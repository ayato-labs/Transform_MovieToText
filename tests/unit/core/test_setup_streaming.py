import unittest
from unittest.mock import MagicMock, patch
from src.utils.setup_helper import SetupHelper

class TestSetupStreaming(unittest.TestCase):
    @patch("ollama.pull")
    def test_pull_model_streaming_logic(self, mock_pull):
        # Mock streaming response from ollama.pull
        mock_pull.return_value = [
            {"status": "downloading", "completed": 500, "total": 1000},
            {"status": "downloading", "completed": 1000, "total": 1000},
            {"status": "success"}
        ]
        
        callback_calls = []
        def progress_callback(status, progress):
            callback_calls.append((status, progress))
            
        success = SetupHelper.pull_model_streaming("test-model", progress_callback)
        
        self.assertTrue(success)
        # 3 parts in mock_pull return value
        self.assertEqual(len(callback_calls), 3)
        
        # Check first progress: 500/1000 = 0.5
        self.assertEqual(callback_calls[0][1], 0.5)
        self.assertIn("Downloading test-model", callback_calls[0][0])
        
        # Check last progress
        self.assertEqual(callback_calls[1][1], 1.0)

if __name__ == "__main__":
    unittest.main()
