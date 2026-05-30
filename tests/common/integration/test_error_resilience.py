import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from src.core.minutes_service import MinutesService
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController

class TestErrorResilience(unittest.TestCase):
    """
    Integration tests focusing on error handling and crash prevention.
    """
    def setUp(self):
        self.mock_config_mgr = MagicMock()
        self.ctrl = LocalSmartController(self.mock_config_mgr)
        self.status_text = ft.Text()
        self.dd_llm = ft.Dropdown()

    @patch("ollama.pull", side_effect=RuntimeError("Connection Timeout"))
    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    @patch("src.core.minutes_service.MinutesService.get_available_models", return_value=[])
    def test_ollama_pull_failure_handling(self, mock_get_models, mock_get_best, mock_pull):
        # Setup: Optimization triggers a pull that will fail
        mock_get_best.return_value = {"tier": "Standard", "whisper": "base", "ollama": "gemma3:4b"}
        
        # Mock page to allow update_error to run
        self.status_text.page = MagicMock()
        
        # Trigger (internal thread will run and fail)
        self.ctrl._pull_and_update("gemma3:4b", self.dd_llm, self.status_text, "Standard")
        
        # Verify: UI should show error message instead of crashing
        self.assertIsNotNone(self.status_text.value)
        self.assertIn("⚠️", self.status_text.value)
        self.assertIn("失敗", self.status_text.value)
        self.assertEqual(self.status_text.color, ft.Colors.RED_400)

    @patch("src.llm.factory.LLMFactory.create_client")
    def test_minutes_service_llm_error_resilience(self, mock_create_client):
        # Setup: LLM client raises exception
        mock_client = MagicMock()
        mock_client.generate_minutes.side_effect = Exception("GPU out of memory")
        mock_create_client.return_value = mock_client
        
        service = MinutesService(self.mock_config_mgr)
        
        # Execution: Should raise RuntimeError but not crash the whole process
        with self.assertRaises(RuntimeError) as cm:
            service.generate_minutes_sync("test transcript", "ollama_local", "gemma3:4b")
        
        self.assertIn("Minutes generation failed", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
