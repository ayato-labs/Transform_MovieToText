import logging

from src.core.config_manager import ConfigManager
from src.core.event_bus import EVENT_STATUS_UPDATE, event_bus
from src.core.history_mgr import HistoryManager
from src.core.history_mgr import history_mgr as _history_mgr
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class MinutesService:
    """
    Handles business logic for generating meeting minutes and summaries.
    Decoupled from UI state.
    """
    CHUNK_SIZE = 4000  # Characters
    CHUNK_OVERLAP = 200

    def __init__(self, config_mgr: ConfigManager, history_mgr: HistoryManager | None = None):
        self.config_mgr = config_mgr
        self.history_mgr = history_mgr or _history_mgr

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        """Splits long text into overlapping chunks."""
        if not text:
            return [""]
            
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
            if start >= len(text):
                break
        return chunks

    def generate_minutes_sync(self, transcript: str, provider: str, model: str, meeting_id: int | None = None) -> str:
        """
        Synchronously generates minutes and updates history if meeting_id is provided.
        Uses Map-Reduce for long transcripts.
        """
        if not transcript or not model:
            raise ValueError("Transcript and model name are required.")

        # 1. Initialize client
        conf = self.config_mgr.get_provider_config(provider)
        client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))

        # 2. Fetch Visual Context if available
        visual_contexts = []
        if meeting_id:
            try:
                visual_contexts = self.history_mgr.get_visual_context(meeting_id)
                logger.info(f"Retrieved {len(visual_contexts)} visual contexts for meeting {meeting_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch visual contexts: {e}")

        # 3. Decision: Direct vs Map-Reduce
        try:
            if len(transcript) < self.CHUNK_SIZE:
                logger.info(f"Using direct generation for transcript length {len(transcript)}")
                res = client.generate_minutes(transcript, model, visual_contexts=visual_contexts)
            else:
                logger.info(f"Using Map-Reduce for transcript length {len(transcript)}")
                res = self._generate_map_reduce(transcript, client, model, visual_contexts)
            
            # 3.5 Generate/Update Title based on the summary
            if meeting_id and res:
                try:
                    event_bus.publish(EVENT_STATUS_UPDATE, "🧠 タイトルを構成中...")
                    ai_title = client.generate_title(res, model)
                    if ai_title:
                        from datetime import datetime
                        timestamp_ui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        final_title = f"{ai_title} ({timestamp_ui})"
                        self.history_mgr.update_meeting(meeting_id, title=final_title)
                        logger.info(f"MinutesService: Updated title for meeting {meeting_id} -> {final_title}")
                except Exception as e:
                    logger.warning(f"MinutesService: Title generation failed: {e}")
                    
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            err_msg = str(e)
            if "503" in err_msg or "high demand" in err_msg.lower():
                msg = (
                    "現在AIモデルが非常に混雑しています（503 UNAVAILABLE）。\n"
                    "一時的な混雑のため、数分待ってから再試行してください。\n"
                    "お急ぎの場合は、設定画面からローカルモデル（Local Smart）への切り替えも検討してください。"
                )
                raise RuntimeError(msg) from e
            raise RuntimeError(f"Minutes generation failed: {e}") from e

        # 4. Update history and config
        if meeting_id:
            try:
                self.history_mgr.update_minutes(meeting_id, res, model_name=model)
            except Exception as e:
                logger.error(f"Failed to update history with minutes: {e}")

        self.config_mgr.set_last_model(model)
        return res

    def _generate_map_reduce(self, transcript: str, client, model: str, visual_contexts: list) -> str:
        """Implements the Map-Reduce pattern for long transcripts."""
        chunks = self._chunk_text(transcript)
        logger.info(f"Map Phase: Processing {len(chunks)} chunks...")
        
        # Map Phase: Summarize each chunk
        summaries = []
        map_prompt_template = (
            "会議のこのセクションにおける主要な議論ポイント、決定事項、および課題を箇条書きで抽出してください。"
            "簡潔にまとめてください。\n\n--- セクション内容 ---\n{chunk_text}"
        )
        
        for i, chunk in enumerate(chunks):
            status = f"🧠 AI解析中 (Map): {i+1}/{len(chunks)} セクションを処理中..."
            logger.debug(status)
            event_bus.publish(EVENT_STATUS_UPDATE, status)
            
            prompt = map_prompt_template.format(chunk_text=chunk)
            # Use chat() for finer control over prompts during intermediate steps
            summary = client.chat(model_name=model, messages=[{"role": "user", "content": prompt}])
            summaries.append(f"セクション {i+1} の要約:\n{summary}")

        # Reduce Phase: Combine summaries into final minutes
        status = "🧠 AI解析中 (Reduce): 中間要約を統合して最終議事録を作成中..."
        logger.info(status)
        event_bus.publish(EVENT_STATUS_UPDATE, status)
        combined_summaries = "\n\n".join(summaries)

        prompt = (
            "以下は会議の各セクションの要約です。これらを統合し、全体として一貫性のある公式な議事録を作成し てください。"
            "項目は「会議の概要」「決定事項」「ネクストアクション」を含めて、適切なMarkdown形式(# や -)を使 用してください。"
            "画像によるコンテキストがある場合は、それも考慮に入れてください。\n\n"
            f"--- セクション要約群 ---\n{combined_summaries}"
        )
        
        # In the final reduce step, we use the combined summaries as the "transcript"
        return client.generate_minutes(combined_summaries, model, visual_contexts=visual_contexts)

    def get_available_models(self, provider: str) -> list[str]:
        """Fetches available models for a given provider."""
        try:
            conf = self.config_mgr.get_provider_config(provider)
            client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            return client.get_available_models()
        except Exception as e:
            logger.error(f"Failed to fetch models for {provider}: {e}")
            return []

    def get_models_info(self, provider: str) -> list[dict]:
        """Fetches detailed model information."""
        try:
            conf = self.config_mgr.get_provider_config(provider)
            logger.info(f"MinutesService: Fetching models for {provider}. Config key: {bool(conf.get('api_key'))}")
            client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            models = client.get_models_info()
            logger.info(f"MinutesService: Found {len(models)} models for {provider}.")
            return models
        except Exception as e:
            logger.error(f"Failed to fetch models info for {provider}: {e}")
            return []

    def delete_model(self, provider: str, model_name: str) -> bool:
        """Deletes a model from the provider."""
        try:
            conf = self.config_mgr.get_provider_config(provider)
            client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            return client.delete_model(model_name)
        except Exception as e:
            logger.error(f"Failed to delete model {model_name} from {provider}: {e}")
            return False
