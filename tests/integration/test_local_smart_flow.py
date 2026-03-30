import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import flet as ft

from src.controllers.local_smart_ctrl import LocalSmartController


class TestLocalSmartIntegration(unittest.TestCase):
    """
    Integration test for LocalSmart optimization flow.
    Verifies interaction between:
    ResourceAdvisor (Spec Check) + Controller (Decision) + Service (Install Status)
    """

    def setUp(self):
        self.mock_config = MagicMock()
        self.ctrl = LocalSmartController(self.mock_config)
        self.dd_provider = ft.Dropdown()
        self.dd_llm = ft.Dropdown()
        self.status_text = ft.Text()

    @patch("src.controllers.local_smart_ctrl.MinutesService.get_available_models")
    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_complete_optimization_decision_flow(self, mock_specs, mock_models):
        # 1. Simulate 32GB RAM, 8GB VRAM (Standard Tier target)
        mock_specs.return_value = (32.0, 8.0)

        # 2. Simulate model NOT installed yet
        mock_models.return_value = ["phi3.5"]  # llama3.1/3.2 (Standard target) is missing

        # 3. Apply Optimization
        with patch("src.controllers.local_smart_ctrl.threading.Thread") as mock_thread:
            # We don't want to actually run the pull thread
            self.ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text)

            # Verify status changed to "Configuring"
            # It should say something like "構成中 (Standard)" or similar
            self.assertIn("構成中", self.status_text.value)
            # Verify auto-pull thread was triggered
            mock_thread.assert_called_once()


if __name__ == "__main__":
    unittest.main()
