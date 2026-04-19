import unittest
from src.core.minutes_service import MinutesService
from tests.fixtures.fake_llm import FakeLLMClient

class MockConfigManager:
    def get_provider_config(self, provider):
        return {"api_key": "fake", "base_url": "http://fake"}
    def set_last_model(self, model):
        pass
    def get_last_model(self, provider):
        return "gemma3:4b"

class TestMinutesServiceUnit(unittest.TestCase):
    """
    Unit tests for MinutesService.
    Uses FakeLLMClient (NO MagicMock) for LLM logic.
    """
    def setUp(self):
        self.config_mgr = MockConfigManager()
        self.service = MinutesService(self.config_mgr)
        # Responses for Map phase and Reduce phase
        # Note: In _generate_map_reduce, combined_summaries is passed to generate_minutes.
        self.fake_client = FakeLLMClient(responses={
            "セクション内容": "Summary for Part",
            "セクション 1": "## Final Integrated Minutes"
        })

    def test_chunk_text_boundary_cases(self):
        # Empty string
        self.assertEqual(self.service._chunk_text(""), [""])
        
        # Exact chunk size
        text_exact = "A" * self.service.CHUNK_SIZE
        chunks = self.service._chunk_text(text_exact)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), self.service.CHUNK_SIZE)
        
        # Slightly over chunk size
        text_over = "A" * (self.service.CHUNK_SIZE + 100)
        chunks = self.service._chunk_text(text_over)
        self.assertEqual(len(chunks), 2)

    def test_generate_map_reduce_logic_flow(self):
        import src.llm.factory
        original_create = src.llm.factory.LLMFactory.create_client
        src.llm.factory.LLMFactory.create_client = lambda *args, **kwargs: self.fake_client
        
        try:
            # Create a transcript long enough for Map-Reduce (> 4000 chars)
            long_transcript = "Meeting part 1. " * 500 # ~8000 chars
            
            # Execute with a dummy meeting_id to trigger title update
            result = self.service.generate_minutes_sync(long_transcript, "ollama_local", "gemma3:4b", meeting_id=123)
            
            # Verify result matches our fake integration response (Reduce Phase)
            self.assertEqual(result, "## Final Integrated Minutes")
            
            # Verify Map Phase calls (should have processed 2 chunks)
            self.assertTrue(len(self.fake_client.chat_calls) >= 2)
            
            # Verify Reduce Phase call
            self.assertEqual(len(self.fake_client.generate_calls), 1)
            
            # Verify Title Generation Phase call
            self.assertEqual(len(self.fake_client.title_calls), 1)
            self.assertEqual(self.fake_client.title_calls[0]["transcript"], "## Final Integrated Minutes")
            
        finally:
            src.llm.factory.LLMFactory.create_client = original_create

if __name__ == "__main__":
    unittest.main()
