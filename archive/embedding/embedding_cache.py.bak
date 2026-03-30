import logging

from src.core.embeddings import BaseEmbeddingProvider
from src.core.history_mgr import history_mgr

logger = logging.getLogger(__name__)


class EmbeddingCacheDelegate:
    """
    A delegate that wraps an EmbeddingProvider and provides caching via HistoryManager.
    Ensures that embeddings are only calculated once per model/meeting pair.
    """

    def __init__(self, provider: BaseEmbeddingProvider, model_name: str):
        self.provider = provider
        self.model_name = model_name

    def get_embedding(self, meeting_id: int, text: str) -> list[float]:
        """
        Fetches an embedding, using the cache if available.
        Note: Currently assumes the 'text' for a meeting_id is constant (the transcript).
        """
        # 1. Check cache
        cached = history_mgr.get_embedding(meeting_id, self.model_name)
        if cached:
            logger.info(f"Cache HIT for meeting {meeting_id} with model {self.model_name}")
            return cached

        # 2. Calculate if missing
        logger.info(f"Cache MISS for meeting {meeting_id} with model {self.model_name}. Calculating...")
        vector = self.provider.embed_text(text)

        # 3. Persist
        try:
            history_mgr.save_embedding(meeting_id, self.model_name, vector)
        except Exception as e:
            logger.warning(f"Failed to persist embedding to cache: {e}")

        return vector

    def get_batch_embeddings(self, meeting_id: int, texts: list[str]) -> list[list[float]]:
        """
        Batch version of get_embedding.
        Currently treats the batch as a single cache unit or delegates to single calls.
        For simplicity in v3.2, we'll focus on the primary meeting transcript embedding.
        """
        # In a real RAG system, we might cache individual chunks.
        # For this UI app, we primarily embed the full transcript for categorization/summary context.
        return self.provider.embed_batch(texts)
