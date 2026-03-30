import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HistoryError(Exception):
    """Base exception for History Manager."""

    pass


class HistoryManager:
    """
    Handles persistence of meeting history.
    Uses a standalone FTS5 table for reliable, high-performance search.
    """

    def __init__(self, db_path: str = "data/history.db", timeout: float = 5.0):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._init_db()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise HistoryError(f"Database initialization failed: {e}") from e

    def _get_connection(self) -> sqlite3.Connection:
        """Helper to get a connection with Row factory and Foreign Key support."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Initializes the database schema and migration logic."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # 1. Main table creation
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS meetings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        title TEXT,
                        transcript TEXT,
                        minutes TEXT,
                        minutes_model TEXT,
                        audio_path TEXT,
                        model_info TEXT,
                        project_name TEXT,
                        category TEXT
                    )
                """)

                # 2. Schema Migration
                cursor = conn.execute("PRAGMA table_info(meetings)")
                columns = [row[1] for row in cursor.fetchall()]

                migration_needed = False
                for col in ["project_name", "category", "minutes_model"]:
                    if col not in columns:
                        logger.info(f"Adding missing column to meetings: {col}")
                        conn.execute(f"ALTER TABLE meetings ADD COLUMN {col} TEXT")
                        migration_needed = True

                # 3. FTS5 Virtual Table Management (Standalone for reliability)
                cursor = conn.execute("PRAGMA table_info(meetings_fts)")
                fts_columns = [row[1] for row in cursor.fetchall()]

                # Recreate FTS if columns are missing or table doesn't exist
                if migration_needed or not fts_columns or "project_name" not in fts_columns:
                    logger.info("Recreating standalone FTS5 virtual table.")
                    conn.execute("DROP TABLE IF EXISTS meetings_fts")
                    conn.execute("""
                        CREATE VIRTUAL TABLE meetings_fts USING fts5(
                            title, transcript, minutes, project_name, category, minutes_model,
                            tokenize='unicode61'
                        )
                    """)

                    # Seed FTS index from existing data
                    conn.execute(
                        "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) "
                        "SELECT id, title, transcript, minutes, project_name, category, minutes_model FROM meetings"
                    )

                # 4. Cleanup legacy triggers
                conn.execute("DROP TRIGGER IF EXISTS meetings_ai")
                conn.execute("DROP TRIGGER IF EXISTS meetings_au")
                conn.execute("DROP TRIGGER IF EXISTS meetings_ad")

                # 5. Visual context (Helper table)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS visual_context (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id INTEGER,
                        timestamp REAL,
                        image_path TEXT,
                        description TEXT,
                        ocr_text TEXT,
                        FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                    )
                """)

                # Migration for image_path
                cursor = conn.execute("PRAGMA table_info(visual_context)")
                v_columns = [row[1] for row in cursor.fetchall()]
                if "image_path" not in v_columns:
                    conn.execute("ALTER TABLE visual_context ADD COLUMN image_path TEXT")

                # 6. Multi-model Embeddings (v3.2)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS meeting_embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id INTEGER,
                        model_name TEXT,
                        embedding BLOB,
                        UNIQUE(meeting_id, model_name),
                        FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                    )
                """)

                conn.commit()
                logger.debug("Database initialization successful.")
            except sqlite3.Error as e:
                logger.error(f"Failed to initialize database: {e}", exc_info=True)
                raise HistoryError(f"Database initialization failed: {e}") from e

    def add_meeting(self, title: str, transcript: str, audio_path: str, model_info: str = "", project_name: str = "", category: str = "") -> int:
        """Adds a new meeting. Manually updates FTS."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # 1. Insert into base table
                cursor = conn.execute(
                    "INSERT INTO meetings (title, transcript, audio_path, model_info, project_name, category, minutes_model) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (title, transcript, audio_path, model_info, project_name, category, ""),
                )
                meeting_id = cursor.lastrowid
                logger.info(f"add_meeting: Inserted base record with ID={meeting_id}")

                # 2. Sync to FTS table (Manual sync)
                conn.execute(
                    "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (meeting_id, title, transcript, "", project_name, category, ""),
                )

                conn.commit()
                return meeting_id
            except sqlite3.Error as e:
                logger.error(f"Error adding meeting: {e}")
                raise HistoryError(f"Meeting storage failed: {e}") from e

    def add_visual_context(self, meeting_id: int, timestamp_sec: float, image_path: str, description: str = "", ocr_text: str = ""):
        """Adds a visual context record for a meeting."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                conn.execute(
                    "INSERT INTO visual_context (meeting_id, timestamp, image_path, description, ocr_text) VALUES (?, ?, ?, ?, ?)",
                    (meeting_id, timestamp_sec, image_path, description, ocr_text),
                )
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Error adding visual context: {e}")

    def update_meeting(self, meeting_id: int, **kwargs):
        """Updates meeting fields. Manually updates FTS."""
        if not kwargs:
            return

        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # 1. Update base table
                cols = ", ".join([f"{k} = ?" for k in kwargs])
                vals = list(kwargs.values())
                vals.append(meeting_id)
                conn.execute(f"UPDATE meetings SET {cols} WHERE id = ?", tuple(vals))

                # 2. Re-sync FTS row (Delete then Insert is the safest way to update standalone FTS)
                row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
                if row:
                    conn.execute("DELETE FROM meetings_fts WHERE rowid = ?", (meeting_id,))
                    conn.execute(
                        "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (meeting_id, row["title"], row["transcript"], row["minutes"], row["project_name"], row["category"], row["minutes_model"]),
                    )
                    logger.info("update_meeting: Synchronized FTS5: meeting_id=%d title=%s", meeting_id, row["title"])

                conn.commit()
                logger.info(f"update_meeting: Successfully committed changes for ID={meeting_id}")
            except sqlite3.Error as e:
                logger.error(f"Error updating meeting {meeting_id}: {e}")
                raise HistoryError(f"Update failed: {e}") from e

    def update_minutes(self, meeting_id: int, minutes: str, model_name: str | None = None):
        """Specialized update for minutes and its model info."""
        data = {"minutes": minutes}
        if model_name:
            data["minutes_model"] = model_name
        self.update_meeting(meeting_id, **data)

    def delete_meeting(self, meeting_id: int):
        """Deletes a meeting from history, FTS index, and associated visual context."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # FTS doesn't support FK cascade, must delete manually
                conn.execute("DELETE FROM meetings_fts WHERE rowid = ?", (meeting_id,))
                # Visual context should cascade if PRAGMA foreign_keys=ON, but let's be explicit for safety
                conn.execute("DELETE FROM visual_context WHERE meeting_id = ?", (meeting_id,))
                conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
                conn.commit()
                logger.info(f"delete_meeting: Successfully deleted meeting ID={meeting_id} from all tables.")
            except sqlite3.Error as e:
                logger.error(f"Error deleting meeting {meeting_id}: {e}")
                raise HistoryError(f"Deletion failed: {e}") from e

    def get_meeting(self, meeting_id: int) -> dict[str, Any] | None:
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_visual_context(self, meeting_id: int) -> list[dict[str, Any]]:
        """Retrieves all visual context for a specific meeting."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT * FROM visual_context WHERE meeting_id = ? ORDER BY timestamp ASC", (meeting_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_meetings(self) -> list[dict[str, Any]]:
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT * FROM meetings ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_meetings_filtered(self, project_name: str | None = None, search_query: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves meetings with optional project and search filters.
        More robust than raw search_meetings for complex filtering.
        """
        from contextlib import closing

        from src.core.utils import sanitize_fts_query

        safe_search = sanitize_fts_query(search_query) if search_query else None

        with closing(self._get_connection()) as conn:
            params = []
            where_clauses = []

            if project_name:
                where_clauses.append("project_name = ?")
                params.append(project_name)

            if safe_search:
                # Use FTS5 subquery for performance
                where_clauses.append("id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?)")
                params.append(safe_search)

            sql = "SELECT * FROM meetings"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            try:
                cursor = conn.execute(sql, tuple(params))
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"get_meetings_filtered: Result set size={len(results)} (limit={limit})")
                return results
            except sqlite3.Error as e:
                logger.error(f"Filtered query failed: {e}")
                return []

    def reassign_project(self, old_name: str, new_name: str = "その他"):
        """Reassigns all meetings from one project to another (e.g. on deletion)."""
        if not old_name or old_name == new_name:
            return False

        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # 1. Update main table
                conn.execute("UPDATE meetings SET project_name = ? WHERE project_name = ?", (new_name, old_name))

                # 2. Sync FTS5 table
                # meetings_fts uses external content from meetings in some setups,
                # but if it's a standard FTS5 table, we update it too.
                conn.execute("UPDATE meetings_fts SET project_name = ? WHERE project_name = ?", (new_name, old_name))

                conn.commit()
                logger.info(f"Reassigned project '{old_name}' to '{new_name}'")
                return True
            except sqlite3.Error as e:
                logger.error(f"Failed to reassign project: {old_name} -> {new_name}: {e}")
                return False

    def search_meetings(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Performs optimized search using FTS5."""
        from src.core.utils import sanitize_fts_query

        safe_query = sanitize_fts_query(query)
        if not safe_query:
            return []

        from contextlib import closing

        with closing(self._get_connection()) as conn:
            # Join with base table to get all fields, and use MATCH for FTS5
            sql = """
                SELECT m.* FROM meetings m
                WHERE m.id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """
            try:
                cursor = conn.execute(sql, (safe_query, limit))
                return [dict(row) for row in cursor]
            except sqlite3.Error as e:
                logger.error(f"Search failed: {e}")
                return []

    def search_hybrid(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Performs Hybrid Search:
        1. FTS5 Keyword Search (High precision for titles/specific terms)
        2. Vector Similarity (Fuzzy semantic matching) (Placeholder logic if vector store not fully integrated)

        Merges results and returns high-confidence matches first.
        """
        # 1. Full-Text Search (Keyword/Title focus)
        fts_hits = self.search_meetings(query, limit=limit)

        # 2. Add score metadata for prioritization
        for hit in fts_hits:
            hit["_search_type"] = "keyword"
            hit["_rank_score"] = 0.9  # High initial score for exact matches

        # 3. Vector Search (TBD actual vector library, currently fuzzy title/transcript fallback)
        # For now, we enhance FTS hits with priority if they appear in Title vs Transcript
        scored_results = []
        seen_ids = set()

        for hit in fts_hits:
            if hit["id"] in seen_ids:
                continue

            # Boost score based on where it matched (Simulating weighting)
            if query.lower() in (hit["title"] or "").lower():
                hit["_rank_score"] += 0.5
            if query.lower() in (hit["minutes"] or "").lower():
                hit["_rank_score"] += 0.3

            scored_results.append(hit)
            seen_ids.add(hit["id"])

        # Sort by rank score
        scored_results.sort(key=lambda x: x["_rank_score"], reverse=True)
        return scored_results[:limit]

    def get_projects(self) -> list[str]:
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT DISTINCT project_name FROM meetings WHERE project_name IS NOT NULL AND project_name != ''")
            return [row[0] for row in cursor.fetchall()]

    # --- Embedding Persistence (v3.2) ---

    def save_embedding(self, meeting_id: int, model_name: str, vector: list[float]):
        """Persists an embedding for a specific meeting and model."""
        import json
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            try:
                # Store as JSON string or binary (JSON is safer for interchange, binary more compact)
                # For SQLite industrial strength, we'll use JSON for now to ensure portability
                vector_data = json.dumps(vector)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO meeting_embeddings (meeting_id, model_name, embedding)
                    VALUES (?, ?, ?)
                """,
                    (meeting_id, model_name, vector_data),
                )
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to save embedding for meeting {meeting_id}: {e}")
                raise HistoryError(f"Embedding storage failed: {e}") from e

    def get_embedding(self, meeting_id: int, model_name: str) -> list[float] | None:
        """Retrieves a cached embedding for a specific model."""
        import json
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT embedding FROM meeting_embeddings WHERE meeting_id = ? AND model_name = ?", (meeting_id, model_name))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def delete_embeddings(self, meeting_id: int):
        """Manually deletes all embeddings for a meeting (though ON DELETE CASCADE handles this)."""
        from contextlib import closing

        with closing(self._get_connection()) as conn:
            conn.execute("DELETE FROM meeting_embeddings WHERE meeting_id = ?", (meeting_id,))
            conn.commit()


# Singleton instance
history_mgr = HistoryManager()
