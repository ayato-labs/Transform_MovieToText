import unittest
from unittest.mock import MagicMock, patch
from src.llm.providers.ollama_client import OllamaLocalClient

class TestSecurityHardening(unittest.TestCase):
    @patch("src.llm.providers.ollama_client.Client")
    def test_ollama_client_enforces_loopback(self, mock_ollama_client):
        # Case 1: Attempt to use non-loopback address
        client = OllamaLocalClient(base_url="http://192.168.1.10:11434")
        # Should be forced to 127.0.0.1
        self.assertEqual(client.host, "http://127.0.0.1:11434")
        
        # Case 2: Attempt to use 0.0.0.0 (potentially unsafe)
        client = OllamaLocalClient(base_url="http://0.0.0.0:11434")
        # Should be forced to 127.0.0.1
        self.assertEqual(client.host, "http://127.0.0.1:11434")
        
        # Case 3: Valid loopback
        client = OllamaLocalClient(base_url="http://localhost:11434")
        self.assertEqual(client.host, "http://localhost:11434")

if __name__ == "__main__":
    unittest.main()
