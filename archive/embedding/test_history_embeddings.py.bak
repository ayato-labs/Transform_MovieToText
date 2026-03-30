from unittest.mock import MagicMock, patch

import pytest

from src.core.history_mgr import HistoryManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_embeddings.db"
    mgr = HistoryManager(db_path=str(db_file))
    yield mgr


def test_embedding_persistence_and_cache(temp_db):
    # 1. Setup meeting
    mid = temp_db.add_meeting(title="Test", transcript="Hello world", audio_path="test.mp3")

    # 2. Mock provider
    mock_provider = MagicMock()
    mock_vector = [0.1, 0.2, 0.3]
    mock_provider.embed_text.return_value = mock_vector

    # We patch history_mgr inside embedding_cache.py to use our temp_db
    with patch("src.core.embedding_cache.history_mgr", temp_db):
        from src.core.embedding_cache import EmbeddingCacheDelegate

        cache = EmbeddingCacheDelegate(mock_provider, "test-model")

        # First call: Cache MISS
        v1 = cache.get_embedding(mid, "Hello world")
        assert v1 == mock_vector
        assert mock_provider.embed_text.call_count == 1

        # Second call: Cache HIT
        v2 = cache.get_embedding(mid, "Hello world")
        assert v2 == mock_vector
        assert mock_provider.embed_text.call_count == 1  # No new calculation

        # Verify DB content directly
        with temp_db._get_connection() as conn:
            row = conn.execute("SELECT * FROM meeting_embeddings WHERE meeting_id = ?", (mid,)).fetchone()
            assert row is not None
            assert row["model_name"] == "test-model"


def test_multi_model_caching(temp_db):
    mid = temp_db.add_meeting(title="Test", transcript="Hello", audio_path="x")

    with patch("src.core.embedding_cache.history_mgr", temp_db):
        from src.core.embedding_cache import EmbeddingCacheDelegate

        # Model A
        mock_a = MagicMock()
        mock_a.embed_text.return_value = [1.0]
        cache_a = EmbeddingCacheDelegate(mock_a, "model-A")

        # Model B
        mock_b = MagicMock()
        mock_b.embed_text.return_value = [2.0]
        cache_b = EmbeddingCacheDelegate(mock_b, "model-B")

        # Calculate for A
        assert cache_a.get_embedding(mid, "Hello") == [1.0]

        # Calculate for B (should not hit A's cache!)
        assert cache_b.get_embedding(mid, "Hello") == [2.0]
        assert mock_b.embed_text.call_count == 1

        # Check A's cache again
        assert cache_a.get_embedding(mid, "Hello") == [1.0]
        assert mock_a.embed_text.call_count == 1
