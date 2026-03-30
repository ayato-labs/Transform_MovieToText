import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import flet as ft

from src.ui.views.chat_bot_view import ChatBotView, ChatMessage


class TestChatBotViewIntegration(unittest.TestCase):
    """
    Integration tests for ChatBotView UI and its interaction with controllers.
    """

    def setUp(self):
        self.page = MagicMock(spec=ft.Page)
        self.config_mgr = MagicMock()
        self.config_mgr.get_active_provider.return_value = "ollama_local"
        self.config_mgr.get_local_smart_enabled.return_value = False

        # Initialize View with mocks
        with patch("src.ui.views.chat_bot_view.threading.Thread"):
            self.view = ChatBotView(self.page, self.config_mgr)

    def test_ui_initialization(self):
        # Basic controls check
        self.assertEqual(self.view.dd_provider.value, "ollama_local")
        self.assertGreater(len(self.view.controls), 0)
        self.assertEqual(len(self.view.chat_history.controls), 0)

    def test_sending_message_ui_update(self):
        # Case: User sends a message
        self.view.input_field.value = "Hello AI"

        with patch("src.ui.views.chat_bot_view.threading.Thread"):
            self.view._on_send_click(None)

        # Check if message is in history
        self.assertEqual(len(self.view.chat_history.controls), 1)
        self.assertIsInstance(self.view.chat_history.controls[0], ChatMessage)
        # Check input cleared
        self.assertEqual(self.view.input_field.value, "")
        # Check status
        self.assertEqual(self.view.status_text.value, "AIが思考中...")

    @patch("src.ui.views.chat_bot_view.history_mgr.search_hybrid")
    def test_rag_worker_retrieval_and_llm_call(self, mock_search):
        # Case: RAG worker running with mock results
        mock_search.return_value = [{"title": "Test Meeting", "transcript": "Testing RAG", "minutes": None}]

        mock_client = MagicMock()
        mock_client.chat.return_value = "This is a RAG answer."
        self.config_mgr.get_llm_client.return_value = mock_client
        self.config_mgr.get_provider_config.return_value = {"api_key": "dummy", "base_url": None}

        # Run worker synchronously for testing
        self.view._run_rag_worker("What was discussed?")

        # Verify LLM was called with the context
        self.assertTrue(mock_client.chat.called)
        # Verify AI response was added to history
        self.assertEqual(len(self.view.chat_history.controls), 1)
        # Verify AI助理 name check is not strictly needed but good for visual
        ai_msg = self.view.chat_history.controls[0]
        self.assertIn("This is a RAG answer.", str(ai_msg.controls[0].controls[1].content.value))

    def test_toggle_local_smart_activates_controller(self):
        # Case: Toggling Local Smart ON
        with patch.object(self.view.local_smart_ctrl, "apply_optimization") as mock_apply:
            self.view._toggle_local_smart(None)
            self.assertTrue(self.view.local_smart_enabled)
            mock_apply.assert_called_once()


if __name__ == "__main__":
    unittest.main()
