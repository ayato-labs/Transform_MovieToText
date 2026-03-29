import logging
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch

from src.core.embedding_cache import EmbeddingCacheDelegate
from src.core.history_mgr import HistoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify():
    db_path = "verify_embeddings.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    mgr = HistoryManager(db_path=db_path)

    # 1. Setup meeting
    mid = mgr.add_meeting(title="Test", transcript="Hello", audio_path="x")
    logger.info(f"Created meeting {mid}")

    # 2. Mock provider
    mock_provider = MagicMock()
    mock_provider.embed_text.return_value = [1.0, 2.0]

    # Cache Delegate
    cache = EmbeddingCacheDelegate(mock_provider, "test-model")

    # 3. Patch history_mgr in cache logic
    with patch("src.core.embedding_cache.history_mgr", mgr):
        v1 = cache.get_embedding(mid, "Hello")
        logger.info(f"V1: {v1}")

        v2 = cache.get_embedding(mid, "Hello")
        logger.info(f"V2: {v2}")

        if v1 == v2 and mock_provider.embed_text.call_count == 1:
            logger.info("VERIFICATION SUCCESS: Cache works!")
        else:
            logger.error("VERIFICATION FAILURE!")
            sys.exit(1)


if __name__ == "__main__":
    verify()
