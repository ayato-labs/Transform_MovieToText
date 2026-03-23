import logging
import os
import shutil

from src.core.history_mgr import history_mgr

logger = logging.getLogger(__name__)


class HistoryController:
    def __init__(self):
        pass

    def get_meetings(self):
        """Fetches all meetings."""
        return history_mgr.get_all_meetings()

    def search_meetings(self, query):
        """Performs full-text search."""
        return history_mgr.search_meetings(query)

    def get_projects(self):
        """Fetches unique project names."""
        return history_mgr.get_projects()

    def export_audio(self, meeting_id, target_dir):
        """Copies the audio file of a meeting to a target directory."""
        meeting = history_mgr.get_meeting(meeting_id)
        if not meeting or not meeting.get("audio_path"):
            logger.error(f"No audio file found for meeting {meeting_id}")
            return False, "音声ファイルが見つかりません。"

        src_path = meeting["audio_path"]
        if not os.path.exists(src_path):
            logger.error(f"Audio file does not exist on disk: {src_path}")
            return False, "元の音声ファイルがディスク上に見つかりません。"

        try:
            timestamp = meeting["timestamp"].replace(":", "-").replace(" ", "_")
            filename = f"export_{timestamp}.mp3"
            dest_path = os.path.join(target_dir, filename)

            shutil.copy2(src_path, dest_path)
            logger.info(f"Audio exported to: {dest_path}")
            return True, f"保存しました: {dest_path}"
        except Exception as e:
            logger.error(f"Failed to export audio: {e}")
            return False, f"エクスポート中にエラーが発生しました: {e}"

    def delete_meeting(self, meeting_id):
        # Implementation could be added here if needed,
        # but for now we follow the "Manual Deletion from Explorer" philosophy.
        pass
