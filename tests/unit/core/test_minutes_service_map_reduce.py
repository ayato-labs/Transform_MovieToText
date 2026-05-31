import unittest
from unittest.mock import MagicMock, patch

from src.core.minutes_service import MinutesService


class TestMinutesServiceMapReduce(unittest.TestCase):
    def setUp(self):
        self.mock_config_mgr = MagicMock()
        self.service = MinutesService(self.mock_config_mgr)
        
    def test_chunk_text(self):
        text = "Hello world. " * 100 # Approx 1300 chars
        chunks = self.service._chunk_text(text, chunk_size=500, overlap=50)
        self.assertTrue(len(chunks) > 1)
        self.assertIn("Hello world", chunks[0])
        
    @patch("src.llm.factory.LLMFactory.create_client")
    def test_generate_minutes_long_text_triggers_map_reduce(self, mock_create_client):
        # Setup mocks
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        self.mock_config_mgr.get_provider_config.return_value = {"api_key": "test"}
        
        # Long transcript (over 3000 chars)
        long_transcript = "Meeting part. " * 500 
        
        # We need to mock chat/generate calls
        # 1. Map calls (multiple) via chat()
        mock_client.chat.side_effect = [
            "Summary 1", "Summary 2"
        ]
        # 2. Reduce call (one) via generate_minutes()
        mock_client.generate_minutes.return_value = "Final Minutes"
        
        # CHUNK_SIZE is 4000. Let's make it 5000 chars to ensure at least 2 chunks.
        long_transcript = "Meeting part. " * 500 
        
        res = self.service.generate_minutes_sync(long_transcript, "ollama_local", "gemma3:4b")
        
        self.assertEqual(res, "Final Minutes")
        # Check that chat was called (Map phase)
        self.assertTrue(mock_client.chat.call_count >= 1)
        # Check that generate_minutes was called (Reduce phase)
        self.assertTrue(mock_client.generate_minutes.called)

if __name__ == "__main__":
    unittest.main()
