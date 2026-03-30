import logging
import os
import shutil

from src.core.history_mgr import history_mgr

logger = logging.getLogger(__name__)


class HistoryController:
    """
    Controller for meeting history.
    """

    def __init__(self):
        pass

    def get_meetings(self):
        return history_mgr.get_all_meetings()

    def search_meetings(self, query):
        return history_mgr.search_meetings(query)

    def get_filtered_meetings(self, project_name=None, search_query=None):
        """Advanced filtering with project name and keywords."""
        return history_mgr.get_meetings_filtered(project_name=project_name, search_query=search_query)

    def reassign_project(self, old_name: str, new_name: str = "その他"):
        """Reassigns all meetings from one project to another (e.g. on deletion)."""
        return history_mgr.reassign_project(old_name, new_name)

    def get_projects(self):
        return history_mgr.get_projects()

    def export_audio(self, meeting_id, target_dir):
        meeting = history_mgr.get_meeting(meeting_id)
        if not meeting or not meeting.get("audio_path"):
            return False, "音声ファイルが見つかりません。"

        src_path = meeting["audio_path"]
        if not os.path.exists(src_path):
            return False, "音声ファイルがディスク上に見つかりません。"

        try:
            timestamp = meeting["timestamp"].replace(":", "-").replace(" ", "_")
            filename = f"export_{timestamp}.mp3"
            dest_path = os.path.join(target_dir, filename)

            shutil.copy2(src_path, dest_path)
            return True, f"保存しました: {dest_path}"
        except Exception as e:
            logger.error(f"Failed to export audio: {e}")
            return False, f"エクスポート失敗: {e}"

    def delete_meeting(self, meeting_id):
        """Deletes a meeting from history."""
        try:
            history_mgr.delete_meeting(meeting_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete meeting {meeting_id}: {e}")
            return False

    def get_meeting_details(self, meeting_id: int):
        """Fetches full meeting data and related visual context."""
        meeting = history_mgr.get_meeting(meeting_id)
        if not meeting:
            return None

        visual_contexts = history_mgr.get_visual_context(meeting_id)
        return {"meeting": meeting, "visual_contexts": visual_contexts}

    def regenerate_minutes(self, meeting_id: int, transcript: str, service, provider: str | None = None, model: str | None = None):
        """Triggers AI minutes re-generation via TranscriptionService."""
        try:
            return service.generate_minutes_for_meeting(meeting_id, transcript, provider=provider, model=model)
        except Exception as e:
            logger.error(f"Failed to regenerate minutes: {e}")
            raise

    def update_meeting(self, meeting_id: int, **kwargs):
        """Updates meeting metadata."""
        try:
            history_mgr.update_meeting(meeting_id, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to update meeting {meeting_id}: {e}")
            return False
