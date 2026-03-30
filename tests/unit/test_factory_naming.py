import os
import sys
import unittest

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.llm.factory import LLMFactory


class TestLLMFactoryNormalization(unittest.TestCase):
    """
    Test Suite for LLMFactory provider normalization.
    """

    def test_provider_normalization(self):
        # Case: 'google' should be converted to 'gemini' and return GeminiLLMClient
        # Note: This will normally attempt to initialize the client,
        # but normalize happens before instantiation.
        try:
            # We don't need a real API key for normalization check if we catch the instantiation
            LLMFactory.create_client("google", api_key="dummy_key")
        except Exception as e:
            # If it fails with 'Gemini' specific error or similar, normalization worked.
            # If it fails with 'Unsupported LLM provider: google', normalization failed.
            self.assertNotIn("google", str(e))


if __name__ == "__main__":
    unittest.main()
