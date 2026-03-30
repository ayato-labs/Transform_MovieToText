import logging
import threading

from src.core.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.core.state import state
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptionController:
    """
    Controller for transcription UI.
    Delegates business logic to TranscriptionService.
    Handles Flet's state updates.
    """

    def __init__(self, config_mgr: ConfigManager, transcriber: WhisperTranscriber):
        self.config_mgr = config_mgr
        self.service = TranscriptionService(config_mgr, transcriber)

    def get_project_list(self):
        return history_mgr.get_projects()

    def start_file_transcription(self, file_path: str, model_name: str, language: str | None = None):
        if not file_path:
            return

        state.set("is_processing", True)
        state.set("status_text", "文字起こし準備中...")
        state.set("progress_visible", True)
        state.set("transcription_progress", 0.0)

        def _worker():
            try:

                def progress_callback(progress):
                    state.set("transcription_progress", progress)

                result = self.service.transcribe_file_sync(file_path, model_name, language=language, progress_callback=progress_callback)

                # Memory Relay: Unload Whisper before potentially starting LLM or just to free up resources
                logger.info("TranscriptionController: Task complete. Unloading Whisper for memory efficiency...")
                self.service.transcriber.unload_model()

                state.set("transcript_text", result)
                state.set("status_text", "文字起こし完了 (履歴に自動保存しました)")
            except Exception as e:
                logger.error(f"File transcription failed: {e}", exc_info=True)
                state.set("status_text", f"エラー: {e}")
            finally:
                state.set("is_processing", False)
                state.set("progress_visible", False)

        threading.Thread(target=_worker, daemon=True).start()

    def toggle_live_recording(self, model_name: str, source: str):
        if state.get("is_recording"):
            self.stop_live_recording()
        else:
            self.start_live_recording(model_name, source)

    def start_live_recording(self, model_name: str, source: str):
        language = state.get("transcription_language")
        state.set("is_recording", True)
        source_label = "システム音" if source == "system" else "マイク"
        state.set("status_text", f"{source_label}をリアルタイム録音・文字起こし中...")
        state.set("transcript_text", "")

        project_name = state.get("project_name", "その他")
        category = state.get("category", "")

        try:

            def _on_text_added(text):
                current = state.get("transcript_text", "")
                state.set("transcript_text", current + text + " ")

            meeting_id = self.service.start_live_recording(
                model_name=model_name, source=source, language=language, project_name=project_name, category=category, on_text_added=_on_text_added
            )
            state.set("current_meeting_id", meeting_id)
        except Exception as e:
            logger.error(f"Live recording start error: {e}")
            state.set("status_text", f"エラー: {e}")
            state.set("is_recording", False)

    def stop_live_recording(self):
        state.set("status_text", "録音を終了し、最後のチャンクを処理中...")
        state.set("is_recording", False)

        def _finalize_callback(full_text, category):
            state.set("transcript_text", full_text)
            if category:
                state.set("category", category)
                state.set("status_text", f"ライブ文字起こし完了（分類: {category}）")
            else:
                state.set("status_text", "ライブ文字起こし終了（短時間のため保存されませんでした）")

        self.service.stop_live_recording(finalize_callback=_finalize_callback)
