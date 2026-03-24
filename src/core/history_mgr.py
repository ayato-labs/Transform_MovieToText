import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Handles persistence of meeting history (transcripts, minutes, and audio paths).
    Uses SQLite for metadata storage.
    """

    def __init__(self, db_path="data/history.db", timeout=5.0):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the database schema and FTS5 virtual table."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            # Main table with new columns
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

            # Migration for existing tables: Check if columns exist and Add if missing
            cursor = conn.execute("PRAGMA table_info(meetings)")
            columns = [row[1] for row in cursor.fetchall()]

            if "project_name" not in columns:
                logger.info("Migrating database: Adding project_name column to meetings table.")
                conn.execute("ALTER TABLE meetings ADD COLUMN project_name TEXT")

            if "category" not in columns:
                logger.info("Migrating database: Adding category column to meetings table.")
                conn.execute("ALTER TABLE meetings ADD COLUMN category TEXT")

            if "minutes_model" not in columns:
                logger.info("Migrating database: Adding minutes_model column to meetings table.")
                conn.execute("ALTER TABLE meetings ADD COLUMN minutes_model TEXT")

            # FTS5 Virtual Table for full-text search
            # Check if FTS5 needs recreation (it doesn't support ALTER TABLE)
            cursor = conn.execute("PRAGMA table_info(meetings_fts)")
            fts_columns = [row[1] for row in cursor.fetchall()]

            if "project_name" not in fts_columns or "category" not in fts_columns or "minutes_model" not in fts_columns:
                logger.info("Migrating database: Recreating meetings_fts table to include missing columns.")
                conn.execute("DROP TABLE IF EXISTS meetings_fts")
                conn.execute("DROP TRIGGER IF EXISTS meetings_ai")
                conn.execute("DROP TRIGGER IF EXISTS meetings_ad")
                conn.execute("DROP TRIGGER IF EXISTS meetings_au")

                conn.execute("""
                    CREATE VIRTUAL TABLE meetings_fts USING fts5(
                        title, transcript, project_name, category, minutes_model, content='meetings', content_rowid='id'
                    )
                """)
                # Re-populate FTS from the now-migrated main table
                conn.execute(
                    "INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model) "
                    "SELECT id, title, transcript, project_name, category, minutes_model FROM meetings"
                )

            # Triggers (Re-created anyway if FTS was recreated, but CREATE IF NOT EXISTS handles the rest)
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS meetings_ai AFTER INSERT ON meetings BEGIN "
                "  INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model) "
                "  VALUES (new.id, new.title, new.transcript, new.project_name, new.category, new.minutes_model); "
                "END;"
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS meetings_ad AFTER DELETE ON meetings BEGIN "
                "  INSERT INTO meetings_fts(meetings_fts, rowid, title, transcript, project_name, category, minutes_model) "
                "  VALUES('delete', old.id, old.title, old.transcript, old.project_name, old.category, old.minutes_model); "
                "END;"
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS meetings_au AFTER UPDATE ON meetings BEGIN "
                "  INSERT INTO meetings_fts(meetings_fts, rowid, title, transcript, project_name, category, minutes_model) "
                "  VALUES('delete', old.id, old.title, old.transcript, old.project_name, old.category, old.minutes_model); "
                "  INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model) "
                "  VALUES (new.id, new.title, new.transcript, new.project_name, new.category, new.minutes_model); "
                "END;"
            )

            # Visual context table for screenshots/images
            conn.execute("""
                CREATE TABLE IF NOT EXISTS visual_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER,
                    timestamp_sec REAL,
                    image_path TEXT,
                    description TEXT,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                )
            """)

            logger.info("History database, FTS5, and Visual Contexts initialized.")
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error during init: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        finally:
            conn.close()

    def add_meeting(self, title, transcript, audio_path, model_info="", project_name="", category=""):
        """Adds a new meeting record with project metadata. Returns the meeting ID."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            cursor = conn.execute(
                "INSERT INTO meetings (title, transcript, audio_path, model_info, project_name, category, minutes_model) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, transcript, audio_path, model_info, project_name, category, ""),
            )
            conn.commit()
            meeting_id = cursor.lastrowid

            # Explicitly sync FTS because external content triggers can be finicky in some environments
            conn.execute(
                "INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?, ?)",
                (meeting_id, title, transcript, project_name, category, ""),
            )
            conn.commit()

            logger.info(f"Meeting record created/added and FTS synced (ID: {meeting_id}, Project: {project_name})")
            return meeting_id
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (add_meeting): {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to add meeting record: {e}")
            raise
        finally:
            conn.close()

    def update_meeting(self, meeting_id, **kwargs):
        """Updates specific fields of a meeting record."""
        if not kwargs:
            return

        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [meeting_id]
            conn.execute(f"UPDATE meetings SET {fields} WHERE id = ?", values)
            conn.commit()
            logger.info(f"Updated meeting record ID: {meeting_id} ({list(kwargs.keys())})")
        except Exception as e:
            logger.error(f"Failed to update meeting {meeting_id}: {e}")
            raise
        finally:
            conn.close()

    def update_minutes(self, meeting_id, minutes, model_name=None):
        """Updates the minutes for a specific meeting (with optional model info)."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            if model_name:
                conn.execute("UPDATE meetings SET minutes = ?, minutes_model = ? WHERE id = ?", (minutes, model_name, meeting_id))
            else:
                conn.execute("UPDATE meetings SET minutes = ? WHERE id = ?", (minutes, meeting_id))
            conn.commit()
            logger.info(f"Updated minutes for meeting ID: {meeting_id} (Model: {model_name})")
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (update_minutes): {e}")
            raise  # Re-raise to let caller know
        except Exception as e:
            logger.error(f"Failed to update minutes: {e}")
            raise
        finally:
            conn.close()

    def get_all_meetings(self):
        """Returns all meetings sorted by timestamp descending."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM meetings ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (get_all_meetings): {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch meetings: {e}")
            return []
        finally:
            conn.close()

    def get_meeting(self, meeting_id):
        """Returns a single meeting record."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (get_meeting {meeting_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch meeting {meeting_id}: {e}")
            return None
        finally:
            conn.close()

    def search_meetings(self, query):
        # ... (existing search_meetings code)
        from src.core.utils import sanitize_fts_query

        safe_query = sanitize_fts_query(query)
        if not safe_query:
            return []

        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM meetings WHERE id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?) ORDER BY timestamp DESC",
                (safe_query,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (search_meetings): {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to search meetings: {e}")
            return []
        finally:
            conn.close()

    def add_visual_context(self, meeting_id, timestamp_sec, image_path, description=""):
        """Adds a visual context record (screenshot) linked to a meeting."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.execute(
                "INSERT INTO visual_contexts (meeting_id, timestamp_sec, image_path, description) VALUES (?, ?, ?, ?)",
                (meeting_id, timestamp_sec, image_path, description),
            )
            conn.commit()
            logger.debug(f"Visual context added for meeting {meeting_id} at {timestamp_sec}s")
        except Exception as e:
            logger.error(f"Failed to add visual context: {e}")
            raise
        finally:
            conn.close()

    def get_visual_contexts(self, meeting_id):
        """Returns all visual contexts for a specific meeting, sorted by timestamp."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM visual_contexts WHERE meeting_id = ? ORDER BY timestamp_sec ASC",
                (meeting_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch visual contexts for meeting {meeting_id}: {e}")
            return []
        finally:
            conn.close()

    def get_projects(self):
        """Returns a list of unique project names."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            cursor = conn.execute(
                "SELECT DISTINCT project_name FROM meetings WHERE project_name IS NOT NULL AND project_name != '' ORDER BY project_name"
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            return []
        finally:
            conn.close()

    def delete_meeting(self, meeting_id):
        """Deletes a meeting and its associated visual contexts."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            conn.commit()
            logger.info(f"Deleted meeting record ID: {meeting_id}")
        except Exception as e:
            logger.error(f"Failed to delete meeting {meeting_id}: {e}")
            raise
        finally:
            conn.close()


# Singleton instance
history_mgr = HistoryManager()
