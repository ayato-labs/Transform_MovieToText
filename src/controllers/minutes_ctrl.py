import logging
import threading

from src.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.core.state import state
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class MinutesController:
    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr
        self.llm_client = None

    def generate_minutes(self, transcript: str, provider: str, model: str):
        if not transcript:
            return
        if not model:
            return

        state.set("is_processing", True)
        state.set("minutes_text", "議事録を生成中...")

        def _worker():
            try:
                # 1. Initialize or get client
                conf = self.config_mgr.get_provider_config(provider)
                client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))

                # 2. v3.0.0: Fetch Visual Context from DB
                meeting_id = state.get("current_meeting_id")
                visual_contexts = []
                if meeting_id:
                    visual_contexts = history_mgr.get_visual_contexts(meeting_id)
                    logger.info(f"Retrieved {len(visual_contexts)} visual contexts for meeting {meeting_id}")

                # 3. Generate multimodal minutes
                res = client.generate_minutes(transcript, model, visual_contexts=visual_contexts)
                state.set("minutes_text", res)

                # Update history if we have a current meeting ID
                meeting_id = state.get("current_meeting_id")
                if meeting_id:
                    history_mgr.update_minutes(meeting_id, res)

                # Save last used model
                self.config_mgr.set_last_model(model)
            except Exception as e:
                logger.error(f"Minutes generation error: {e}", exc_info=True)
                state.set("minutes_text", f"【エラーが発生しました】\n{e}")
            finally:
                state.set("is_processing", False)

        threading.Thread(target=_worker, daemon=True).start()

    def get_available_models(self, provider: str):
        """Helper to fetch models for a provider."""
        try:
            conf = self.config_mgr.get_provider_config(provider)
            client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            return client.get_available_models()
        except Exception as e:
            logger.warning(f"Failed to fetch models for {provider}: {e}")
            return []
