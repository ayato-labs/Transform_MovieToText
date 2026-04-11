import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
from src.core.history_mgr import HistoryManager
from src.platforms.common.ui.views.chat_bot_view import ChatBotView


class TestSystemCompleteWorkflow(unittest.TestCase):
    """
    System/E2E Test for the full user flow story:
    1. Transcription result is saved.
    2. RAG Chat retrieves that result and answers accurately.
    """

    def setUp(self):
        self.db_path = "tests/system_test_v2.db"
        self.mgr = HistoryManager(self.db_path)
        self.config_mgr = MagicMock()
        self.config_mgr.get_active_provider.return_value = "ollama_local"
        self.page = MagicMock()
        # Must return list for segments to be JSON serializable
        self.mock_transcriber = MagicMock()
        self.mock_transcriber.transcribe.return_value = {"text": "Transcription result", "segments": []}

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch("src.llm.providers.ollama_client.OllamaLocalClient.chat")
    @patch("src.llm.providers.ollama_client.OllamaCloudClient.chat")
    def test_full_user_story_flow(self, mock_chat_cloud, mock_chat):
        # 1. Data Generation (Story: A user just finished a meeting about "Pizza")
        self.mgr.add_meeting(title="Pizza Strategy", transcript="The best pizza has pineapple.", audio_path="mock.mp3")
        self.mgr.update_minutes(1, minutes="Summary: Pineapple is recommended for pizza.")

        # 2. Chat Query (Story: User asks about the secret to pizza)
        # CRITICAL: We patch the global history_mgr in the view module
        with patch("src.platforms.common.ui.views.chat_bot_view.history_mgr", self.mgr), patch("src.platforms.common.ui.views.chat_bot_view.threading.Thread"):
            view = ChatBotView(self.page, self.config_mgr)

        query = "What is the secret for pizza?"
        view.input_field.value = query

        # 3. Mock AI Response (Simulating LLM knowing the context)
        mock_chat.return_value = "The secret is pineapple, according to the Pizza Strategy meeting."

        # 'create_autospec' is the Gold Standard for anti-MagicMock policies.
        # It ensures that calling client_mock.chat() with wrong arguments raises TypeError.
        from unittest.mock import create_autospec

        from src.llm.base_client import BaseLLMClient

        client_mock = create_autospec(BaseLLMClient, instance=True)
        client_mock.chat = mock_chat

        self.config_mgr.get_llm_client.return_value = client_mock
        self.config_mgr.get_provider_config.return_value = {"api_key": "dummy"}

        # 4. Verification
        view._run_rag_worker(query)

        # Verify the mock was called with 'messages' (not 'message'!)
        args, kwargs = mock_chat.call_args
        self.assertIn("messages", kwargs)
        self.assertIsInstance(kwargs["messages"], list)
        self.assertEqual(kwargs["messages"][-1]["content"], query)
        # But here we focus on the answer content
        self.assertGreater(len(view.chat_history.controls), 0)
        ai_msg = view.chat_history.controls[-1]
        response_text = ai_msg.controls[0].controls[1].content.value
        self.assertIn("pineapple", response_text)
        self.assertIn("Pizza Strategy", response_text)


if __name__ == "__main__":
    unittest.main()