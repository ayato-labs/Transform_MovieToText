import json
import logging
import re

from src.core.db.connection import DatabaseConnection, db_conn
from src.core.utils import sanitize_fts_query

logger = logging.getLogger(__name__)


class MeetingRepository:
    def __init__(self, db: DatabaseConnection = db_conn):
        self.db = db

    def init_db(self):
        """Initializes tables and handles migrations for meetings."""
        with self.db.get_connection() as conn:
            # 1. Main table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    transcript TEXT,
                    transcript_segments TEXT,
                    minutes TEXT,
                    minutes_model TEXT,
                    audio_path TEXT,
                    model_info TEXT,
                    project_name TEXT,
                    category TEXT
                )
            """)

            # 2. Migrations for new columns
            cursor = conn.execute("PRAGMA table_info(meetings)")
            columns = [row["name"] for row in cursor.fetchall()]

            # Explicit list of columns that might be missing in older versions
            target_cols = {"project_name": "TEXT", "category": "TEXT", "minutes_model": "TEXT", "transcript_segments": "TEXT"}

            migration_needed = False
            for col, col_type in target_cols.items():
                if col not in columns:
                    logger.info(f"MeetingRepository: Adding missing column: {col}")
                    conn.execute(f"ALTER TABLE meetings ADD COLUMN {col} {col_type}")
                    migration_needed = True

            # 3. FTS5 Table Management
            cursor = conn.execute("PRAGMA table_info(meetings_fts)")
            fts_columns = [row["name"] for row in cursor.fetchall()]

            if migration_needed or not fts_columns or "project_name" not in fts_columns:
                logger.info("MeetingRepository: Syncing FTS5 virtual table.")
                conn.execute("DROP TABLE IF EXISTS meetings_fts")
                conn.execute("""
                    CREATE VIRTUAL TABLE meetings_fts USING fts5(
                        title, transcript, minutes, project_name, category, minutes_model,
                        tokenize='unicode61'
                    )
                """)
                conn.execute(
                    "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) "
                    "SELECT id, title, transcript, minutes, project_name, category, minutes_model FROM meetings"
                )
            conn.commit()

    def add(
        self,
        title: str,
        transcript: str,
        audio_path: str,
        model_info: str = "",
        project_name: str = "",
        category: str = "",
        transcript_segments: list[dict] | None = None,
    ) -> int:
        segments_json = json.dumps(transcript_segments) if transcript_segments else None

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO meetings (title, transcript, transcript_segments, audio_path, model_info, project_name, category, minutes_model) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, transcript, segments_json, audio_path, model_info, project_name, category, ""),
            )
            meeting_id = cursor.lastrowid

            # Sync FTS
            conn.execute(
                "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (meeting_id, title, transcript, "", project_name, category, ""),
            )
            conn.commit()
            return meeting_id

    def update(self, meeting_id: int, **kwargs):
        if not kwargs:
            return

        # Prepare segments for JSON storage if present
        if "transcript_segments" in kwargs:
            kwargs["transcript_segments"] = json.dumps(kwargs["transcript_segments"])

        with self.db.get_connection() as conn:
            cols = ", ".join([f"{k} = ?" for k in kwargs])
            vals = list(kwargs.values())
            vals.append(meeting_id)
            conn.execute(f"UPDATE meetings SET {cols} WHERE id = ?", tuple(vals))

            # Sync FTS (Delete & Re-insert for simplicity/safety)
            row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
            if row:
                conn.execute("DELETE FROM meetings_fts WHERE rowid = ?", (meeting_id,))
                conn.execute(
                    "INSERT INTO meetings_fts(rowid, title, transcript, minutes, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (meeting_id, row["title"], row["transcript"], row["minutes"], row["project_name"], row["category"], row["minutes_model"]),
                )
            conn.commit()

    def get(self, meeting_id: int) -> dict | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
            if row:
                d = dict(row)
                if d.get("transcript_segments"):
                    try:
                        d["transcript_segments"] = json.loads(d["transcript_segments"])
                    except Exception:
                        d["transcript_segments"] = None
                return d
            return None

    def delete(self, meeting_id: int):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM meetings_fts WHERE rowid = ?", (meeting_id,))
            conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            conn.commit()

    def list_all(self) -> list[dict]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM meetings ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def search_filtered(self, project_names: list[str] = None, categories: list[str] = None, search_query: str = None, limit: int = 50) -> list[dict]:
        with self.db.get_connection() as conn:
            params = []
            where_clauses = []

            if project_names:
                valid_projs = [p for p in project_names if p]
                if valid_projs:
                    placeholders = ", ".join(["?"] * len(valid_projs))
                    where_clauses.append(f"project_name IN ({placeholders})")
                    params.extend(valid_projs)

            if categories:
                valid_cats = [c for c in categories if c]
                if valid_cats:
                    placeholders = ", ".join(["?"] * len(valid_cats))
                    where_clauses.append(f"category IN ({placeholders})")
                    params.extend(valid_cats)

            if search_query:
                # Break up search query into individual tokens for more flexible matching
                # Clean up and add wildcard for partial matches
                tokens = []
                # Use a similar regex as QueryAnalyzer to extract words
                raw_words = re.findall(r"[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-]+", search_query)
                for w in raw_words:
                    if len(w) >= 2:
                        tokens.append(f'"{w}"*')

                if tokens:
                    # Use 'OR' between tokens to increase hit rate, while still prioritising multiple matches
                    flexible_query = " OR ".join(tokens)
                    where_clauses.append("id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?)")
                    params.append(flexible_query)
                else:
                    # Fallback to simple matching if no good tokens found
                    where_clauses.append("id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?)")
                    params.append(sanitize_fts_query(search_query))

            sql = "SELECT * FROM meetings"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_distinct_projects(self) -> list[str]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT project_name FROM meetings WHERE project_name IS NOT NULL AND project_name != ''")
            return [row[0] for row in cursor.fetchall()]

    def get_distinct_categories(self) -> list[str]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT category FROM meetings WHERE category IS NOT NULL AND category != ''")
            return [row[0] for row in cursor.fetchall()]

    def reassign_project(self, old_name: str, new_name: str):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE meetings SET project_name = ? WHERE project_name = ?", (new_name, old_name))
            conn.execute("UPDATE meetings_fts SET project_name = ? WHERE project_name = ?", (new_name, old_name))
            conn.commit()


class VisualContextRepository:
    def __init__(self, db: DatabaseConnection = db_conn):
        self.db = db

    def init_db(self):
        with self.db.get_connection() as conn:
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
            # image_path migration is already covered or can be added if needed
            conn.commit()

    def add(self, meeting_id: int, timestamp: float, image_path: str, description: str = "", ocr_text: str = ""):
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO visual_context (meeting_id, timestamp, image_path, description, ocr_text) VALUES (?, ?, ?, ?, ?)",
                (meeting_id, timestamp, image_path, description, ocr_text),
            )
            conn.commit()

    def get_by_meeting(self, meeting_id: int) -> list[dict]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM visual_context WHERE meeting_id = ? ORDER BY timestamp ASC", (meeting_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_by_meeting(self, meeting_id: int):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM visual_context WHERE meeting_id = ?", (meeting_id,))
            conn.commit()
