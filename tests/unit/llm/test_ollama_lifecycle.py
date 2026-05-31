import unittest
from unittest.mock import MagicMock, patch

from src.llm.providers.ollama_client import OllamaLocalClient


class TestOllamaLifecycle(unittest.TestCase):
    @patch("src.llm.providers.ollama_client.Client")
    def setUp(self, mock_ollama_client):
        self.mock_client_instance = MagicMock()
        mock_ollama_client.return_value = self.mock_client_instance
        self.client = OllamaLocalClient(base_url="http://localhost:11434")

    def test_get_models_info(self):
        # Mocking list() response
        mock_model = MagicMock()
        mock_model.model = "gemma3:4b"
        mock_model.size = 2.7 * (1024**3)
        
        # Newer SDK style
        mock_response = MagicMock()
        mock_response.models = [mock_model]
        self.mock_client_instance.list.return_value = mock_response
        
        # Mocking _verify_local_model to return True
        with patch.object(self.client, "_verify_local_model", return_value=True):
            info = self.client.get_models_info()
            
            self.assertEqual(len(info), 1)
            self.assertEqual(info[0]["name"], "gemma3:4b")
            self.assertEqual(info[0]["size_gb"], 2.7)

    def test_delete_model(self):
        self.client.delete_model("gemma3:2b")
        self.mock_client_instance.delete.assert_called_with("gemma3:2b")

if __name__ == "__main__":
    unittest.main()
