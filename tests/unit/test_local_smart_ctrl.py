import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import flet as ft

from src.controllers.local_smart_ctrl import LocalSmartController


class TestLocalSmartController(unittest.TestCase):
    """
    Test Suite for LocalSmartController logic and auto-pull.
    """

    def setUp(self):
        self.mock_config = MagicMock()
        self.ctrl = LocalSmartController(self.mock_config)
        self.dd_provider = ft.Dropdown()
        self.dd_llm = ft.Dropdown()
        self.status_text = ft.Text()

    @patch("src.controllers.local_smart_ctrl.MinutesService.get_available_models")
    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    def test_apply_optimization_already_installed(self, mock_rec, mock_models):
        # Case: Model is already installed
        mock_rec.return_value = {"tier": "SmallGPU", "ollama": "phi3.5", "whisper": "small"}
        mock_models.return_value = ["phi3.5", "llama3.2"]

        self.ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text)

        # Verify UI state
        self.assertEqual(self.dd_llm.value, "phi3.5")
        self.assertTrue(self.dd_llm.disabled)
        self.assertIn("SmallGPU", self.status_text.value)

    @patch("src.controllers.local_smart_ctrl.threading.Thread")
    @patch("src.controllers.local_smart_ctrl.MinutesService.get_available_models")
    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    def test_apply_optimization_missing_triggers_pull(self, mock_rec, mock_models, mock_thread):
        # Case: Model is NOT installed
        mock_rec.return_value = {"tier": "SmallGPU", "ollama": "phi3.5", "whisper": "small"}
        mock_models.return_value = ["llama3.2"]  # Missing phi3.5

        self.ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text)

        # Verify status says "Downloading"
        self.assertIn("構成中", self.status_text.value)
        # Verify background thread was started
        mock_thread.assert_called_once()


if __name__ == "__main__":
    unittest.main()
