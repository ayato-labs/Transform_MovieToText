import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class GoogleEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = "text-embedding-004"

    def embed_text(self, text: str) -> list[float]:
        response = self.client.models.embed_content(model=self.model, contents=text)
        return response.embeddings[0].values

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(model=self.model, contents=texts)
        return [e.values for e in response.embeddings]


class FastEmbedProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        # This will download the model on first init
        self.model = TextEmbedding(model_name=model_name)
        logger.info(f"FastEmbed initialized with model: {model_name}")

    def embed_text(self, text: str) -> list[float]:
        # FastEmbed returns an iterator of numpy arrays
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = list(self.model.embed(texts))
        return [e.tolist() for e in embeddings]


class EmbeddingFactory:
    @staticmethod
    def create_provider(provider_type: str, use_cache: bool = False, **kwargs) -> Any:
        # Create base provider
        if provider_type == "google":
            provider = GoogleEmbeddingProvider(api_key=kwargs.get("api_key"))
            model_name = provider.model
        elif provider_type == "local":
            model_name = kwargs.get("model_name", "BAAI/bge-small-en-v1.5")
            provider = FastEmbedProvider(model_name=model_name)
        else:
            raise ValueError(f"Unknown embedding provider: {provider_type}")

        # Wrap with cache delegate if requested
        if use_cache:
            from src.core.embedding_cache import EmbeddingCacheDelegate

            return EmbeddingCacheDelegate(provider, model_name)

        return provider
