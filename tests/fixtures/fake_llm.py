import logging

from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class FakeLLMClient(BaseLLMClient):
    """
    A deterministic LLM client for unit tests.
    Inherits from BaseLLMClient and avoids MagicMock for core logic.
    """

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.generate_calls = []
        self.chat_calls = []
        self.title_calls = []
        self._available_models = ["gemma3:2b", "gemma3:4b"]

    def get_available_models(self) -> list[str]:
        return self._available_models

    def chat(self, model_name: str, messages: list[dict]) -> str:
        self.chat_calls.append({"messages": messages, "model": model_name})
        last_msg = messages[-1]["content"] if messages else ""
        for key, resp in self.responses.items():
            if key in last_msg:
                return resp
        return f"Fake chat response for: {last_msg[:20]}..."

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        self.generate_calls.append({"transcript": transcript, "model": model_name})
        for key, resp in self.responses.items():
            if key in transcript:
                return resp
        return "## Fake Minutes\n- Action: Do something."

    def generate_title(self, transcript: str, model_name: str) -> str:
        self.title_calls.append({"transcript": transcript, "model": model_name})
        return "Generated Fake Title"
        
    def extract_category(self, text: str, model_name: str, categories: list[str]) -> str:
        return categories[0] if categories else "Unknown"

    def get_models_info(self) -> list[dict]:
        return [{"name": m, "size_gb": 2.0} for m in self._available_models]

    def delete_model(self, model_name: str) -> bool:
        if model_name in self._available_models:
            self._available_models.remove(model_name)
            return True
        return False
