import unittest
from unittest.mock import MagicMock, patch
import flet as ft
from src.core.config_manager import ConfigManager
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController
from src.platforms.desktop.ui.local_smart_helper import LocalSmartUIHelper

class TestLocalSmartIntegration(unittest.TestCase):
    """
    Integration tests for Local Smart flow.
    Mocks are allowed here.
    """
    def setUp(self):
        self.config_mgr = MagicMock(spec=ConfigManager)
        self.ctrl = LocalSmartController(self.config_mgr)
        
        # Real Flet objects for integration verification
        self.dd_provider = ft.Dropdown(options=[ft.dropdown.Option("ollama_local")])
        self.dd_llm = ft.Dropdown()
        self.status_text = ft.Text()
        self.dd_whisper = ft.Dropdown()
        self.local_smart_btn = ft.IconButton(icon=ft.Icons.AUTO_AWESOME)
        
        self.helper = LocalSmartUIHelper(
            self.config_mgr, self.ctrl, self.dd_provider, self.dd_llm, 
            self.status_text, dd_whisper=self.dd_whisper, local_smart_btn=self.local_smart_btn
        )

    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    @patch("src.core.minutes_service.MinutesService.get_available_models")
    @patch("threading.Thread")
    def test_complete_optimization_decision_flow(self, mock_thread, mock_get_models, mock_get_best):
        # 1. Setup Resource Advisor to recommend gemma3:4b
        mock_get_best.return_value = {
            "tier": "Standard",
            "whisper": "medium",
            "ollama": "gemma3:4b"
        }
        
        # 2. Setup MinutesService to say gemma3:4b is NOT installed
        mock_get_models.return_value = ["phi3:latest"] # Irrelevant model
        
        # 3. Trigger optimization through helper (User clicks the magic wand)
        self.helper.apply_smart()
        
        # 4. Verify side effects
        # - Whisper should be locked to medium
        self.assertEqual(self.dd_whisper.value, "medium")
        self.assertTrue(self.dd_whisper.disabled)
        
        # - Provider should be locked to ollama_local
        self.assertEqual(self.dd_provider.value, "ollama_local")
        self.assertTrue(self.dd_provider.disabled)
        
        # - LLM should be locked (waiting for pull)
        self.assertTrue(self.dd_llm.disabled)
        
        # - Status text should indicate pulling
        self.assertIn("gemma3:4b", self.status_text.value)
        self.assertIn("構成中", self.status_text.value)
        
        # - Background thread for pulling should have started
        mock_thread.assert_called_once()

    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    @patch("src.core.minutes_service.MinutesService.get_available_models")
    def test_optimization_with_existing_model(self, mock_get_models, mock_get_best):
        # Setup: gemma3:4b IS already installed (and it's the only gemma3 there to be deterministic)
        mock_get_best.return_value = {"tier": "Pro", "whisper": "large-v3", "ollama": "gemma3:4b"}
        mock_get_models.return_value = ["phi4:latest", "gemma3:4b"]
        
        self.helper.apply_smart()
        
        # Should immediately select gemma3:4b without starting a thread
        self.assertEqual(self.dd_llm.value, "gemma3:4b")
        self.assertIn("適用", self.status_text.value)

if __name__ == "__main__":
    unittest.main()
