import time
import unittest
from unittest.mock import MagicMock, patch

import flet as ft

# System-level test simulating full user flow
from src.core.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.platforms.desktop.controllers.transcription_ctrl import TranscriptionController
from src.platforms.desktop.ui.views.live_transcription_view import LiveTranscriptionView


class TestFullUserFlow(unittest.TestCase):
    """
    System test for the full user flow: 
    Start App -> Toggle Smart -> Record -> AI Transform.
    """
    @patch("src.llm.factory.LLMFactory.create_client")
    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs", return_value=(16.0, 8.0))
    @patch("ollama.pull")
    def test_live_transcription_to_minutes_flow(self, mock_pull, mock_specs, mock_create_client):
        # 1. Setup mocks
        mock_client = MagicMock()
        mock_client.get_available_models.return_value = ["gemma3:4b"]
        mock_client.generate_minutes.return_value = "## Structured Minutes Output"
        mock_create_client.return_value = mock_client
        
        # Patch history_mgr methods that might not exist or need mocking
        with patch.object(history_mgr, 'get_projects', return_value=["Project A"]), \
             patch.object(history_mgr, 'update_minutes', return_value=True), \
             patch.object(history_mgr, 'get_visual_context', return_value=[], create=True):
            
            page = MagicMock(spec=ft.Page)
            page.overlay = []
            config_mgr = ConfigManager()
            transcriber = MagicMock()
            ctrl = TranscriptionController(config_mgr, transcriber, history_mgr=history_mgr)
            
            # 2. Instantiate View (Simulates user opening the Recording tab)
            view = LiveTranscriptionView(page, config_mgr, ctrl, hw_info={"ram": 16.0, "vram": 8.0, "device": "GPU"})
            
            # Give a small moment for initial_load thread to run
            time.sleep(0.5)

            # 3. Simulate User enabling Local Smart
            view.smart_helper.toggle_smart()
            self.assertEqual(view.dd_llm.value, "gemma3:4b")
            self.assertEqual(view.dd_whisper.value, "medium")
            
            # 4. Simulate Recording Process
            result_payload = {
                "text": "Hello, this is a test meeting about Project X. We decided to move forward.",
                "meeting_id": 123
            }
            
            # Manually trigger the callback
            view._on_transcription_finished(result_payload)
            
            # Give time for the background AI transformation thread to finish
            time.sleep(1.0)
            
            # 5. Verify AI Transformation was triggered and result displayed
            self.assertEqual(view.result_text.value, "## Structured Minutes Output")
            self.assertEqual(view.tabs.selected_index, 1) # Should have switched to AI tab
            self.assertIn("完了", view.status_text.value)

    @patch("src.core.history_mgr.history_mgr.get_projects", return_value=["Project A"])
    @patch("src.llm.factory.LLMFactory.create_client")
    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs", return_value=(16.0, 8.0))
    def test_file_transcription_view_initialization(self, mock_specs, mock_create_client, mock_projects):
        # This test specifically target the AttributeError regression in constructor
        from src.platforms.desktop.ui.views.file_transcription_view import FileTranscriptionView
        
        mock_client = MagicMock()
        mock_client.get_available_models.return_value = ["gemma3:4b"]
        mock_create_client.return_value = mock_client
        
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        config_mgr = ConfigManager()
        transcriber = MagicMock()
        ctrl = TranscriptionController(config_mgr, transcriber)
        
        # Instantiate. Should not raise AttributeError: 'FileTranscriptionView' object has no attribute 'smart_helper'
        view = FileTranscriptionView(page, config_mgr, ctrl, hw_info={"ram": 16.0, "vram": 8.0, "device": "GPU"})
        
        # Verify helper is initialized
        self.assertIsNotNone(view.smart_helper)
        self.assertEqual(view.smart_helper.config_mgr, config_mgr)

if __name__ == "__main__":
    unittest.main()
