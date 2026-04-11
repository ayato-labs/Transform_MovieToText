import logging

import requests

from ..base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class AyatoCloudClient(BaseLLMClient):
    """
    Client for the managed Ayato Cloud Gateway (GCP-based).
    Provides access to high-quality LLMs without needing individual API keys.
    """

    def __init__(self, token: str, base_url: str = "https://api.ayato-ai.com/v1"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "X-Ayato-Client": "Desktop-App"}

    def get_available_models(self) -> list[str]:
        # In the future, this would fetch from the gateway
        return ["gemini-2.0-flash", "gemini-1.5-pro", "gemma3-27b"]

    def _call_gateway(self, path: str, payload: dict) -> dict:
        try:
            response = requests.post(f"{self.base_url}{path}", json=payload, headers=self.headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ayato Cloud Gateway Error: {e}")
            raise

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        payload = {"model": model_name, "task": "minutes", "transcript": transcript, "visual_contexts": visual_contexts}
        res = self._call_gateway("/transform", payload)
        return res.get("content", "Error: No content returned from gateway.")

    def extract_category(self, transcript: str, model_name: str) -> str:
        payload = {"model": model_name, "task": "category", "transcript": transcript}
        res = self._call_gateway("/transform", payload)
        return res.get("content", "Unknown")

    def generate_title(self, transcript: str, model_name: str) -> str:
        payload = {"model": model_name, "task": "title", "transcript": transcript}
        res = self._call_gateway("/transform", payload)
        return res.get("content", "No Title")

    def chat(self, model_name: str, messages: list[dict]) -> str:
        payload = {"model": model_name, "messages": messages}
        res = self._call_gateway("/chat", payload)
        return res.get("content", "Error: No response from cloud.")
