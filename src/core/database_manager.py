import logging
import sqlite3
from typing import Any

from src.core.constants import DEFAULT_DB_PATH, EDITION_RESTRICTIONS, AppEdition

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections for different editions (SQLite for Free/Pro, MySQL for Enterprise)."""

    def __init__(self, edition: AppEdition, config: dict):
        self.edition = edition
        self.config = config
        self.db_type = EDITION_RESTRICTIONS.get(edition, {}).get("db_type", "sqlite")
        self.connection = None
        logger.info(f"DatabaseManager initialized for {edition.name} (Type: {self.db_type})")

    def get_connection(self) -> Any:
        """Returns a database connection based on the current edition."""
        if self.db_type == "mysql":
            return self._get_mysql_connection()
        return self._get_sqlite_connection()

    def _get_sqlite_connection(self):
        """Standard SQLite connection."""
        try:
            conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise

    def _get_mysql_connection(self):
        """MySQL connection for Enterprise edition.
        Requires 'mysql-connector-python' or similar.
        """
        # mysql_config = self.config.get("mysql", {})
        try:
            # Placeholder for actual MySQL connection logic
            # import mysql.connector
            # return mysql.connector.connect(**mysql_config)
            logger.warning("MySQL connection requested but Enterprise logic is not yet fully implemented.")
            # For now, fall back to SQLite or raise
            return self._get_sqlite_connection()
        except ImportError:
            logger.error("MySQL connector not installed. Run 'uv pip install mysql-connector-python'")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
