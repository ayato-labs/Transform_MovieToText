import logging
import threading

from src.core.config_manager import ConfigManager
from src.core.event_bus import (
    EVENT_STATUS_UPDATE,
    EVENT_TRANSCRIPTION_ERROR,
    EVENT_TRANSCRIPTION_FINISHED,
    EVENT_TRANSCRIPTION_PROGRESS,
    EVENT_TRANSCRIPTION_SEGMENT,
    event_bus,
)
from src.core.history_mgr import history_mgr
from src.core.intent_router import IntentRouter, TransformationStrategy
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
        self.router = IntentRouter(config_mgr)
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Connects background events to the UI state."""

        @event_bus.subscribe(EVENT_STATUS_UPDATE)
        def on_status_update(status_text):
            state.set("status_text", status_text)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_PROGRESS)
        def on_progress(progress):
            state.set("transcription_progress", progress)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_SEGMENT)
        def on_segment(segment_data):
            # For live updates
            if state.get("is_recording"):
                current = state.get("transcript_text", "")
                state.set("transcript_text", current + segment_data["text"] + " ")

        @event_bus.subscribe(EVENT_TRANSCRIPTION_FINISHED)
        def on_finished(result):
            state.set("is_processing", False)
            state.set("progress_visible", False)
            state.set("status_text", "処理完了 (履歴に保存しました)")

        @event_bus.subscribe(EVENT_TRANSCRIPTION_ERROR)
        def on_error(error_msg):
            state.set("is_processing", False)
            state.set("progress_visible", False)
            state.set("status_text", f"エラー: {error_msg}")

    def get_project_list(self):
        return history_mgr.get_projects()

    def start_file_transcription(self, file_path: str, model_name: str, language: str | None = None):
        if not file_path:
            return

        state.set("is_processing", True)
        state.set("progress_visible", True)
        state.set("transcription_progress", 0.0)

        def _worker():
            try:
                self.service.transcribe_file_sync(file_path, model_name, language=language)

                # Memory Relay: Unload Whisper before potentially starting LLM
                logger.info("TranscriptionController: Task complete. Unloading Whisper...")
                self.service.transcriber.unload()
            except Exception as e:
                logger.error(f"File transcription failed: {e}", exc_info=True)
                event_bus.publish(EVENT_TRANSCRIPTION_ERROR, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def toggle_live_recording(self, model_name: str, source: str):
        if state.get("is_recording"):
            self.stop_live_transcription()
        else:
            self.start_live_transcription(model_name, source)

    def start_live_transcription(self, model_name: str, source: str, project_name: str | None = None):
        language = state.get("transcription_language")
        state.set("is_recording", True)
        state.set("transcript_text", "")

        # Use passed project_name or fallback to state/default
        p_name = project_name or state.get("project_name", "その他")
        category = state.get("category", "")

        try:
            meeting_id = self.service.start_live_recording(
                model_name=model_name, source=source, language=language, project_name=p_name, category=category
            )
            state.set("current_meeting_id", meeting_id)
        except Exception as e:
            logger.error(f"Live transcription start error: {e}")
            event_bus.publish(EVENT_TRANSCRIPTION_ERROR, str(e))
            state.set("is_recording", False)

    def stop_live_transcription(self):
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

    def transform_transcript(self, meeting_id, transcript, provider, model):
        """Routes to the best AI strategy and performs transformation in background."""
        if not transcript or len(transcript.strip()) < 50:
            return

        def _transform_worker():
            try:
                event_bus.publish(EVENT_STATUS_UPDATE, "🧠 AI解析中: 内容に合わせた最適な形式を選択しています...")

                # 1. Determine Intent
                route_result = self.router.route(transcript, provider, model)
                strategy = route_result.get("strategy", TransformationStrategy.CLEAN)
                reason = route_result.get("reason", "")

                event_bus.publish(EVENT_STATUS_UPDATE, f"🧠 AI思考中: {strategy.name}として変換を実行中... ({reason})")

                # 2. Execute Transformation
                # For now, generate_minutes fits most strategies, but we can specialize later
                result = self.service.generate_minutes_for_meeting(meeting_id=meeting_id, transcript=transcript, provider=provider, model=model)

                # 3. Update UI
                event_bus.publish(EVENT_STATUS_UPDATE, f"✨ 完了: {strategy.name}形式で整理しました。")
                event_bus.publish(EVENT_TRANSCRIPTION_FINISHED, {"meeting_id": meeting_id, "text": transcript, "transformed": result})

            except Exception as e:
                logger.error(f"Transformation failed: {e}", exc_info=True)
                event_bus.publish(EVENT_TRANSCRIPTION_ERROR, f"AI変換失敗: {e}")

        threading.Thread(target=_transform_worker, daemon=True).start()
