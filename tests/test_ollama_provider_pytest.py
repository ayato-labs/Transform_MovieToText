from unittest.mock import MagicMock, patch

import pytest

from src.llm.providers.ollama_client import OllamaLocalClient


@pytest.fixture
def mock_ollama_client():
    with patch("src.llm.providers.ollama_client.Client") as mock:
        yield mock


def test_ollama_generate_minutes(mock_ollama_client):
    # Setup mock
    mock_instance = mock_ollama_client.return_value
    mock_instance.chat.return_value = {"message": {"content": "Test summary"}}

    client = OllamaLocalClient(base_url="http://localhost:11434")
    res = client.generate_minutes("Test transcript", model_name="llama3")

    assert res == "Test summary"
    mock_instance.chat.assert_called_once()


def test_ollama_get_available_models(mock_ollama_client):
    # Setup mock for 'list' to be a Mock object with 'models' attribute
    mock_instance = mock_ollama_client.return_value

    # Create an object-like response
    mock_model = MagicMock()
    mock_model.model = "llama3:latest"

    mock_response = MagicMock()
    mock_response.models = [mock_model]
    mock_instance.list.return_value = mock_response

    client = OllamaLocalClient(base_url="http://localhost:11434")
    models = client.get_available_models()

    assert "llama3:latest" in models
    assert len(models) == 1


def test_ollama_error_handling(mock_ollama_client):
    # Setup mock to raise error
    mock_instance = mock_ollama_client.return_value
    mock_instance.chat.side_effect = Exception("Ollama connection failed")

    client = OllamaLocalClient(base_url="http://localhost:11434")

    with pytest.raises(RuntimeError) as excinfo:
        client.generate_minutes("transcript", "llama3")

    assert "Failed to generate minutes" in str(excinfo.value)