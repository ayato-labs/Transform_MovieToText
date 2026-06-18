import unittest
from unittest.mock import MagicMock, patch
from src.llm.providers.gemini_client import GeminiClient
from google.genai import errors

class TestGeminiRetry(unittest.TestCase):
    def setUp(self):
        self.api_key = "fake_key"
        
    @patch("google.genai.Client")
    def test_generate_minutes_retry_on_503(self, mock_genai_client):
        # Setup mock client
        mock_instance = mock_genai_client.return_value
        
        # Simulate 503 error then success
        # Note: We need to mock the response object as well
        mock_response = MagicMock()
        mock_response.text = "Retried successfully"
        
        # We need to simulate the error. google-genai might raise ServerError for 503.
        # Let's assume it raises an Exception with '503' in it for now if we can't easily import the exact error class.
        # But we found ServerError in dir(errors).
        
        err_503 = Exception("503 UNAVAILABLE: high demand")
        
        mock_instance.models.generate_content.side_effect = [err_503, err_503, mock_response]
        
        client = GeminiClient(api_key=self.api_key)
        
        # We need to make sure GeminiClient uses the retry logic.
        # If I haven't implemented it yet, this test should fail (exhausting retries or just failing immediately).
        
        res = client.generate_minutes("test transcript", "gemini-1.5-flash")
        
        self.assertEqual(res, "Retried successfully")
        self.assertEqual(mock_instance.models.generate_content.call_count, 3)

if __name__ == "__main__":
    unittest.main()
