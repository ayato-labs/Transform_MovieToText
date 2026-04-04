import logging

from src.core.db.connection import DatabaseConnection
from src.core.db.repositories import MeetingRepository, VisualContextRepository

logger = logging.getLogger(__name__)


class HistoryError(Exception):
    """Base exception for History Manager."""

    pass


class HistoryManager:
    """
    Service layer for meeting history.
    Delegates database operations to repositories.
    """

    def __init__(self, db_path: str | None = None):
        logger.info(f"HistoryManager: Initializing (DB Path: {db_path or 'default'})")
        if db_path:
            self._conn = DatabaseConnection(db_path)
        else:
            from src.core.db.connection import db_conn

            self._conn = db_conn

        self.meetings = MeetingRepository(self._conn)
        self.visuals = VisualContextRepository(self._conn)
        try:
            self._init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise HistoryError(f"Database initialization failed: {e}") from e

    @property
    def db_path(self) -> str:
        return str(self._conn.db_path)

    def _get_connection(self):
        return self._conn.get_connection()

    def _init_db(self):
        """Triggers repository-level initialization and migrations."""
        self.meetings.init_db()
        self.visuals.init_db()
        logger.debug("HistoryManager: Database layers initialized.")

    def add_meeting(
        self,
        title: str,
        transcript: str,
        audio_path: str,
        model_info: str = "",
        project_name: str = "",
        category: str = "",
        transcript_segments: list[dict] | None = None,
    ) -> int:
        """Adds a new meeting with optional segment data."""
        try:
            return self.meetings.add(
                title=title,
                transcript=transcript,
                audio_path=audio_path,
                model_info=model_info,
                project_name=project_name,
                category=category,
                transcript_segments=transcript_segments,
            )
        except Exception as e:
            logger.error(f"Error adding meeting: {e}")
            raise HistoryError(f"Meeting storage failed: {e}") from e

    def add_visual_context(self, meeting_id: int, timestamp_sec: float, image_path: str, description: str = "", ocr_text: str = ""):
        """Adds a visual context record for a meeting."""
        try:
            self.visuals.add(meeting_id, timestamp_sec, image_path, description, ocr_text)
        except Exception as e:
            logger.warning(f"Error adding visual context: {e}")

    def update_meeting(self, meeting_id: int, **kwargs):
        """Updates meeting fields via repository."""
        try:
            self.meetings.update(meeting_id, **kwargs)
        except Exception as e:
            logger.error(f"Error updating meeting {meeting_id}: {e}")
            raise HistoryError(f"Update failed: {e}") from e

    def update_minutes(self, meeting_id: int, minutes: str, model_name: str | None = None):
        """Specialized update for minutes and its model info."""
        data = {"minutes": minutes}
        if model_name:
            data["minutes_model"] = model_name
        self.update_meeting(meeting_id, **data)

    def delete_meeting(self, meeting_id: int):
        """Deletes a meeting and its associated visual context."""
        try:
            # PRAGMA foreign_keys = ON handles visual_context cascade if configured,
            # but repository can be explicit if needed.
            self.meetings.delete(meeting_id)
            logger.info(f"delete_meeting: Deleted record ID={meeting_id}")
        except Exception as e:
            logger.error(f"Error deleting meeting {meeting_id}: {e}")
            raise HistoryError(f"Deletion failed: {e}") from e

    def get_meeting(self, meeting_id: int) -> dict | None:
        return self.meetings.get(meeting_id)

    def get_visual_context(self, meeting_id: int) -> list[dict]:
        return self.visuals.get_by_meeting(meeting_id)

    def get_all_meetings(self) -> list[dict]:
        return self.meetings.list_all()

    def get_meetings_filtered(
        self, project_names: list[str] = None, categories: list[str] = None, search_query: str = None, limit: int = 50
    ) -> list[dict]:
        return self.meetings.search_filtered(project_names, categories, search_query, limit)

    def reassign_project(self, old_name: str, new_name: str = "その他"):
        """Reassigns all meetings from one project to another."""
        if not old_name or old_name == new_name:
            return False
        try:
            self.meetings.reassign_project(old_name, new_name)
            return True
        except Exception as e:
            logger.error(f"Failed to reassign project: {e}")
            return False

    def get_projects(self) -> list[str]:
        return self.meetings.get_distinct_projects()

    def get_categories(self) -> list[str]:
        return self.meetings.get_distinct_categories()

    def search_meetings(self, query: str, limit: int = 50) -> list[dict]:
        """Backward compatibility alias for search_filtered."""
        return self.meetings.search_filtered(search_query=query, limit=limit)

    def delete_project(self, project_name: str):
        """Backward compatibility for project deletion (reassigns to default)."""
        return self.reassign_project(project_name, "その他")

    def search_hybrid(self, query: str, limit: int = 5) -> list[dict]:
        """
        Maintains the existing hybrid search logic, delegating basic search to repository.
        """
        # For now, reuse repository search as base
        results = self.meetings.search_filtered(search_query=query, limit=limit)

        for hit in results:
            hit["_search_type"] = "keyword"
            hit["_rank_score"] = 0.9

            # Simple boosting
            if query.lower() in (hit["title"] or "").lower():
                hit["_rank_score"] += 0.5
            if query.lower() in (hit["minutes"] or "").lower():
                hit["_rank_score"] += 0.3

        results.sort(key=lambda x: x.get("_rank_score", 0), reverse=True)
        return results[:limit]


# Singleton instance
history_mgr = HistoryManager()
