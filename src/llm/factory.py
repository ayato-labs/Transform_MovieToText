import logging

from src.llm.providers.gemini_client import GeminiClient
from src.llm.providers.ollama_client import OllamaLocalClient

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory class to create LLM clients."""

    @staticmethod
    def create_client(provider_name, api_key=None, base_url=None, temperature=0.7):
        """Creates and returns the appropriate LLM client."""
        logger.info(f"LLMFactory: Creating client for {provider_name} (Temp: {temperature})")

        if provider_name == "ollama_local":
            return OllamaLocalClient(base_url=base_url, temperature=temperature)
        if provider_name == "gemini_api":
            return GeminiClient(api_key=api_key, temperature=temperature)
            
        logger.error(f"Unsupported LLM provider: {provider_name}")
        raise ValueError(f"Unknown LLM provider: {provider_name}")

def get_llm_client(provider_name, api_key, base_url=None, temperature=0.7):
    """Legacy function support for factory creation."""
    return LLMFactory.create_client(provider_name, api_key, base_url, temperature)
