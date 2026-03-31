import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Manages SQLite database connections with recommended settings.
    """

    def __init__(self, db_path: str = "data/history.db", timeout: float = 5.0):
        self._is_memory = str(db_path) == ":memory:"
        if self._is_memory:
            # Use URI for sharing across connections in same process.
            self.db_path = "file:memdb?mode=memory&cache=shared"
            # Keep one connection open to ensure :memory: db stays alive
            # MUST use check_same_thread=False for sharing across transcription threads
            self._keep_alive = sqlite3.connect(self.db_path, timeout=timeout, uri=True, check_same_thread=False)
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._keep_alive = None

        self.timeout = timeout

    @contextmanager
    def get_connection(self):
        """
        Returns a database connection.
        For in-memory databases, returns the persistent connection to avoid losing the schema.
        """
        if self._is_memory:
            conn = self._keep_alive
        else:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)

        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            if not self._is_memory:
                conn.close()

    def __del__(self):
        if hasattr(self, "_keep_alive") and self._keep_alive:
            self._keep_alive.close()


# Singleton instance for default path
db_conn = DatabaseConnection()
