import unittest
from unittest.mock import MagicMock, patch

from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController


class TestLocalSmartSafety(unittest.TestCase):
    def setUp(self):
        self.mock_config_mgr = MagicMock()
        self.ctrl = LocalSmartController(self.mock_config_mgr)

    @patch("src.core.resource_advisor.ResourceAdvisor.get_best_match")
    def test_apply_optimization_handles_none_components(self, mock_get_best):
        # Mock recommendation
        mock_get_best.return_value = {
            "tier": "Standard",
            "whisper": "base",
            "ollama": "gemma3:4b"
        }
        
        # We'll pass None for dropdowns to simulate hidden UI
        status_text = MagicMock()
        
        # This should NOT raise AttributeError: 'NoneType' object has no attribute 'value'
        try:
            self.ctrl.apply_optimization(
                dd_provider=None, 
                dd_llm=None, 
                status_text=status_text, 
                dd_whisper=None
            )
        except AttributeError as e:
            self.fail(f"apply_optimization raised AttributeError even with None checks: {e}")

    def test_restore_manual_mode_handles_none_components(self):
        status_text = MagicMock()
        # This should NOT raise AttributeError
        try:
            self.ctrl.restore_manual_mode(
                dd_provider=None, 
                dd_llm=None, 
                status_text=status_text, 
                dd_whisper=None
            )
        except AttributeError as e:
            self.fail(f"restore_manual_mode raised AttributeError even with None checks: {e}")

if __name__ == "__main__":
    unittest.main()
