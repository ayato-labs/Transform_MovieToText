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
        logger.info(f"DatabaseConnection: Initializing with path: {db_path}")
        self._is_memory = str(db_path) == ":memory:"
        if self._is_memory:
            # SECURITY/STABILITY: Use unique URI name for each memory DB to prevent 
            # cross-test leakage while allowing multi-threaded access within one instance.
            import uuid
            unique_id = uuid.uuid4().hex
            self.db_path = f"file:memdb_{unique_id}?mode=memory&cache=shared"
            # Keep one connection open to ensure :memory: db stays alive
            self._keep_alive = sqlite3.connect(self.db_path, timeout=timeout, uri=True, check_same_thread=False)
            logger.info(f"DatabaseConnection: In-memory database initialized ({unique_id}).")
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._keep_alive = None
            logger.info(f"DatabaseConnection: Initializing persistent DB at {self.db_path}")

        self.timeout = timeout

    @contextmanager
    def get_connection(self):
        """
        Returns a database connection.
        For in-memory databases, returns the persistent connection to avoid losing the schema.
        """
        conn = self._keep_alive if self._is_memory else sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)

        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except Exception as e:
            logger.error(f"DatabaseConnection: Error during database operation: {e}")
            raise
        finally:
            if not self._is_memory:
                conn.close()
                logger.debug("DatabaseConnection: Connection closed.")

    def __del__(self):
        if hasattr(self, "_keep_alive") and self._keep_alive:
            self._keep_alive.close()
            logger.info("DatabaseConnection: In-memory connection closed.")


# Singleton instance for default path
db_conn = DatabaseConnection()
