from unittest.mock import MagicMock, patch

import pytest

from src.llm.providers.gemini_client import GeminiLLMClient


@pytest.fixture
def mock_client():
    with patch("src.llm.providers.gemini_client.genai.Client") as mock:
        yield mock


def test_get_available_models(mock_client):
    # Setup mock response for models.list()
    mock_model_1 = MagicMock()
    mock_model_1.name = "models/gemini-1.5-pro"
    mock_model_1.supported_actions = ["generate_content"]

    mock_model_2 = MagicMock()
    mock_model_2.name = "models/gemini-embedding-exp"
    mock_model_2.supported_actions = ["embedContent"]

    mock_model_3 = MagicMock()
    mock_model_3.name = "models/gemini-1.5-flash"
    mock_model_3.supported_actions = ["generate_content"]

    # Mocking the client instance's models.list return value
    mock_client.return_value.models.list.return_value = [mock_model_1, mock_model_2, mock_model_3]

    client = GeminiLLMClient(api_key="test_key")
    models = client.get_available_models()

    # Should filter out embedding and sort (descending gemini-1.5-pro, gemini-1.5-flash)
    assert len(models) == 2
    assert "gemini-1.5-pro" in models
    assert "gemini-1.5-flash" in models
    assert "gemini-embedding-exp" not in models


def test_generate_minutes(mock_client):
    mock_response = MagicMock()
    mock_response.text = "Generated Minutes Content"
    mock_client.return_value.models.generate_content.return_value = mock_response

    client = GeminiLLMClient(api_key="test_key")
    result = client.generate_minutes("Test Transcript", "gemini-1.5-flash")

    assert result == "Generated Minutes Content"
    mock_client.return_value.models.generate_content.assert_called_once()