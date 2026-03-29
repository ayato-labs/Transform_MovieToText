import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Pre-mock fastembed to avoid import-time re.error on Windows
sys.modules["fastembed"] = MagicMock()

from src.core.embeddings import FastEmbedProvider


@pytest.fixture
def mock_fastembed():
    with patch("fastembed.TextEmbedding") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


def test_fastembed_embed_text(mock_fastembed):
    # Setup mock return value (iterator of numpy arrays)
    # FastEmbed's .embed() usually returns something like [np.array([0.1, 0.2])]
    mock_fastembed.embed.return_value = iter([np.array([0.1, 0.2, 0.3])])

    provider = FastEmbedProvider(model_name="test-model")
    embedding = provider.embed_text("hello world")

    assert isinstance(embedding, list)
    assert embedding == [0.1, 0.2, 0.3]
    mock_fastembed.embed.assert_called_once_with(["hello world"])


def test_fastembed_embed_batch(mock_fastembed):
    # Setup mock for batch
    mock_fastembed.embed.return_value = iter([np.array([1.0, 0.0]), np.array([0.0, 1.0])])

    provider = FastEmbedProvider()
    texts = ["A", "B"]
    embeddings = provider.embed_batch(texts)

    assert len(embeddings) == 2
    assert embeddings[0] == [1.0, 0.0]
    assert embeddings[1] == [0.0, 1.0]
    mock_fastembed.embed.assert_called_once_with(texts)
