import logging
import threading

from src.core.config_manager import ConfigManager
from src.core.minutes_service import MinutesService
from src.core.state import state

logger = logging.getLogger(__name__)


class MinutesController:
    """
    Controller for minutes UI.
    Delegates business logic to MinutesService.
    Handles UI state updates.
    """

    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr
        self.service = MinutesService(config_mgr)

    def generate_minutes(self, transcript: str, provider: str, model: str):
        if not transcript or not model:
            return

        state.set("is_processing", True)
        state.set("minutes_text", "議事録を生成中...")

        def _worker():
            try:
                meeting_id = state.get("current_meeting_id")
                res = self.service.generate_minutes_sync(transcript=transcript, provider=provider, model=model, meeting_id=meeting_id)
                state.set("minutes_text", res)

                if meeting_id:
                    state.set("status_text", f"議事録生成完了 (モデル: {model})")
            except Exception as e:
                logger.error(f"Minutes generation failed: {e}", exc_info=True)
                state.set("minutes_text", f"【エラー】\n{e}")
            finally:
                state.set("is_processing", False)

        threading.Thread(target=_worker, daemon=True).start()

    def get_available_models(self, provider: str):
        return self.service.get_available_models(provider)
