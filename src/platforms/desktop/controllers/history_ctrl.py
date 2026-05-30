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

    def get_roi_metrics(self):
        """Fetches calculated ROI results from HistoryManager."""
        return history_mgr.get_roi_metrics()

    def get_meetings(self):
        return history_mgr.get_all_meetings()

    def search_meetings(self, query):
        return history_mgr.search_meetings(query)

    def get_filtered_meetings(self, project_name=None, search_query=None):
        """Advanced filtering with project name and keywords."""
        project_names = [project_name] if project_name else None
        return history_mgr.get_meetings_filtered(project_names=project_names, search_query=search_query)

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

    def export_meeting_as_md(self, meeting_id: int, target_dir: str):
        """Exports meeting text and metadata as a Markdown file with YAML frontmatter."""
        details = self.get_meeting_details(meeting_id)
        if not details:
            return False, "データが見つかりません。"
        
        m = details["meeting"]
        title = m.get("title", "Untitled")
        project = m.get("project_name", "その他")
        category = m.get("category", "")
        timestamp = m.get("timestamp", "")
        minutes = m.get("minutes", "")
        transcript = m.get("transcript", "")

        # Format as Markdown with YAML Frontmatter
        md_lines = [
            "---",
            f'title: "{title}"',
            f'project: "{project}"',
            f'category: "{category}"',
            f'date: "{timestamp}"',
            "source: \"Transform_MovieToText Export\"",
            "---",
            "",
            f"# {title}",
            "",
            "## 議事録 / 要約",
            minutes if minutes else "(未生成)",
            "",
            "---",
            "",
            "## 文字起こし全文",
            "<details>",
            "<summary>クリックして展開</summary>",
            "",
            transcript,
            "",
            "</details>"
        ]
        
        content = "\n".join(md_lines)
        
        try:
            from src.core.utils import sanitize_filename
            safe_title = sanitize_filename(title)
            safe_date = timestamp.split(" ")[0].replace("-", "")
            filename = f"Knowledge_{safe_date}_{safe_title}.md"
            dest_path = os.path.join(target_dir, filename)
            
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True, f"ナレッジを書き出しました: {filename}"
        except Exception as e:
            logger.error(f"Failed to export knowledge md: {e}")
            return False, f"書き出し失敗: {e}"

    def sync_knowledge(self, target_dir):
        """Triggers knowledge directory sync via HistoryManager."""
        return history_mgr.sync_knowledge(target_dir)
