from collections.abc import Callable

from src.core.config_manager import ConfigManager
from src.core.event_bus import (
    EVENT_STATUS_UPDATE,
    EVENT_TRANSCRIPTION_ERROR,
    EVENT_TRANSCRIPTION_FINISHED,
    EVENT_TRANSCRIPTION_SEGMENT,
    event_bus,
)
from src.core.state import state


class LiveTranscriptionViewModel:
    """
    Platform-agnostic ViewModel for the Live Transcription screen.
    Handles state management and business logic interaction, notifying the View via callbacks.
    """

    def __init__(self, config_mgr: ConfigManager, transcription_ctrl):
        self.config_mgr = config_mgr
        self.ctrl = transcription_ctrl
        self.on_status_changed: Callable[[str], None] | None = None
        self.on_segment_added: Callable[[str], None] | None = None
        self.on_transcription_finished: Callable[[dict], None] | None = None
        self.on_error: Callable[[str], None] | None = None

        self._setup_subscriptions()

    def _setup_subscriptions(self):
        @event_bus.subscribe(EVENT_STATUS_UPDATE)
        def on_status(status):
            if self.on_status_changed:
                self.on_status_changed(status)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_SEGMENT)
        def on_segment(segment_data):
            text = segment_data.get("text", "")
            if self.on_segment_added:
                self.on_segment_added(text)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_FINISHED)
        def on_finished(result):
            if self.on_transcription_finished:
                self.on_transcription_finished(result)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_ERROR)
        def on_error(err):
            if self.on_error:
                self.on_error(str(err))

    def start_recording(self, whisper_model: str, source: str, project_name: str, provider: str, llm_model: str):
        """Triggers recording start logic."""
        if state.get("is_recording", False):
            return

        # Update config before starting
        self.config_mgr.set_whisper_model(whisper_model)
        self.config_mgr.set_audio_source(source)
        self.config_mgr.set_active_provider(provider)
        self.config_mgr.set_last_model(llm_model)

        try:
            self.ctrl.start_live_transcription(model_name=whisper_model, source=source, project_name=project_name)
        except Exception as e:
            if self.on_error:
                self.on_error(f"起動失敗: {e}")

    def stop_recording(self):
        """Triggers recording stop logic."""
        if not state.get("is_recording", False):
            return
        self.ctrl.stop_live_transcription()

    def trigger_ai_transformation(self, meeting_id: int, transcript: str, provider: str, model: str):
        """Triggers AI minutes generation."""
        if not transcript or len(transcript.strip()) < 50:
            return

        if self.on_status_changed:
            self.on_status_changed("🧠 AI変換の準備中...")

        self.ctrl.transform_transcript(
            meeting_id=meeting_id,
            transcript=transcript,
            provider=provider,
            model=model,
        )
