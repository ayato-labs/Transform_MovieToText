import unittest
from unittest.mock import MagicMock
import flet as ft
from src.platforms.desktop.ui.local_smart_helper import LocalSmartUIHelper

class TestLocalSmartUIHelperUnit(unittest.TestCase):
    def setUp(self):
        self.config_mgr = MagicMock()
        self.ctrl = MagicMock()
        
        # UI Mocks
        self.dd_provider = ft.Dropdown(options=[ft.dropdown.Option("ollama_local")])
        self.dd_llm = ft.Dropdown()
        self.status_text = ft.Text()
        self.dd_whisper = ft.Dropdown()
        self.local_smart_btn = ft.IconButton(icon=ft.Icons.AUTO_AWESOME)
        
        # Initial config state
        self.config_mgr.get_local_smart_enabled.return_value = False
        
        self.helper = LocalSmartUIHelper(
            self.config_mgr,
            self.ctrl,
            self.dd_provider,
            self.dd_llm,
            self.status_text,
            dd_whisper=self.dd_whisper,
            local_smart_btn=self.local_smart_btn
        )

    def test_toggle_smart_on_updates_config_and_ui(self):
        # Action: Toggle ON
        self.helper.toggle_smart()
        
        # Assertions
        self.assertTrue(self.helper.local_smart_enabled)
        self.config_mgr.set_local_smart_enabled.assert_called_with(True)
        self.assertTrue(self.local_smart_btn.selected)
        self.ctrl.apply_optimization.assert_called_once()

    def test_toggle_smart_off_restores_manual_mode(self):
        # Setup: Start as enabled
        self.helper.local_smart_enabled = True
        
        # Action: Toggle OFF
        self.helper.toggle_smart()
        
        # Assertions
        self.assertFalse(self.helper.local_smart_enabled)
        self.config_mgr.set_local_smart_enabled.assert_called_with(False)
        self.assertFalse(self.local_smart_btn.selected)
        self.ctrl.restore_manual_mode.assert_called_once()

if __name__ == "__main__":
    unittest.main()
