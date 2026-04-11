import unittest
from unittest.mock import patch

from src.llm.providers.ollama_client import OllamaCloudClient, OllamaLocalClient


class TestOllamaClients(unittest.TestCase):
    def setUp(self):
        self.local_config = {"base_url": "http://localhost:11434", "model": "local_model"}
        self.cloud_config = {"base_url": "https://ollama.com", "api_key": "test_key", "model": "cloud_model"}

    # IMPORTANT: We MUST mock BEFORE the Client is instantiated in __init__
    @patch("src.llm.providers.ollama_client.Client")
    def test_ollama_local_client(self, mock_client_class):
        mock_instance = mock_client_class.return_value
        mock_instance.chat.return_value = {"message": {"content": "local response"}}

        client = OllamaLocalClient(**self.local_config)
        self.assertEqual(client.host, "http://localhost:11434")

        response = client.generate_minutes("transcript", model_name="local_model")
        self.assertEqual(response, "local response")

        mock_client_class.assert_called_with(host="http://localhost:11434")

    @patch("src.llm.providers.ollama_client.Client")
    def test_ollama_cloud_client(self, mock_client_class):
        mock_instance = mock_client_class.return_value
        mock_instance.chat.return_value = {"message": {"content": "cloud response"}}

        client = OllamaCloudClient(**self.cloud_config)
        self.assertEqual(client.host, "https://ollama.com")

        response = client.generate_minutes("transcript", model_name="cloud_model")
        self.assertEqual(response, "cloud response")

        expected_headers = {"Authorization": "Bearer test_key"}
        mock_client_class.assert_called_with(host="https://ollama.com", headers=expected_headers)


if __name__ == "__main__":
    unittest.main()