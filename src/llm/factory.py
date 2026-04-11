import logging

from src.llm.providers.cloud_gateway_client import AyatoCloudClient
from src.llm.providers.gemini_client import GeminiLLMClient
from src.llm.providers.ollama_client import OllamaCloudClient, OllamaLocalClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory class to create LLM clients."""

    @staticmethod
    def create_client(provider_name, api_key=None, base_url=None):
        """Creates and returns the appropriate LLM client."""
        # Normalize provider names (UI friendlier names)
        if provider_name == "google":
            provider_name = "gemini"

        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "****"
        logger.info(f"LLMFactory: Creating client for {provider_name} (API Key: {masked_key}, Base URL: {base_url})")

        if provider_name == "gemini":
            return GeminiLLMClient(api_key=api_key)
        if provider_name == "ayato_cloud":
            return AyatoCloudClient(token=api_key, base_url=base_url)
        if provider_name == "ollama_local":
            return OllamaLocalClient(base_url=base_url)
        if provider_name == "ollama_cloud":
            return OllamaCloudClient(api_key=api_key, base_url=base_url)
        logger.error(f"Unsupported LLM provider: {provider_name}")
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def get_llm_client(provider_name, api_key, base_url=None):
    """Legacy function support for factory creation."""
    return LLMFactory.create_client(provider_name, api_key, base_url)
