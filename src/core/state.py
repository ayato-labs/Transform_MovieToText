import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class AppState:
    """
    Global state management for the application.
    Implements a simple observer pattern for state changes.
    """

    def __init__(self):
        self._state: dict[str, Any] = {
            "is_processing": False,
            "status_text": "準備完了",
            "transcript_text": "",
            "minutes_text": "",
            "error_message": "",
            "gpu_warning": "",
            "progress_visible": False,
            "is_recording": False,
            "current_meeting_id": None,
            "selected_file_path": None,
            "current_mp3_path": None,
            "project_name": "",
            "category": "",
            "audio_source": "system",
            "whisper_model": "base",
            "llm_provider": "ollama_local",
            "llm_model": None,
            "force_gpu": False,
            "transcription_language": None,
        }
        self._listeners: dict[str, list[Callable[[Any], None]]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any, notify: bool = True):
        if self._state.get(key) != value:
            self._state[key] = value
            if notify:
                self._notify(key, value)

    def subscribe(self, key: str, callback: Callable[[Any], None]):
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

    def _notify(self, key: str, value: Any):
        if key in self._listeners:
            for callback in self._listeners[key]:
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Error in state listener for {key}: {e}")


# Global singleton instance
state = AppState()
