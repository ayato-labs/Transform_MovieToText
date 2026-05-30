import logging

import flet as ft

from src.core.config_manager import ConfigManager
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController
from src.platforms.desktop.ui.ui_utils import safe_update_control

logger = logging.getLogger(__name__)

class LocalSmartUIHelper:
    """
    Modular UI helper to handle common Local Smart (automatic setup) logic 
    across different views.
    """
    
    def __init__(self, 
                 config_mgr: ConfigManager, 
                 local_smart_ctrl: LocalSmartController,
                 dd_provider: ft.Dropdown,
                 dd_llm: ft.Dropdown,
                 status_text: ft.Text,
                 dd_whisper: ft.Dropdown = None,
                 local_smart_btn: ft.IconButton = None):
        self.config_mgr = config_mgr
        self.ctrl = local_smart_ctrl
        self.dd_provider = dd_provider
        self.dd_llm = dd_llm
        self.status_text = status_text
        self.dd_whisper = dd_whisper
        self.local_smart_btn = local_smart_btn
        self.local_smart_enabled = config_mgr.get_local_smart_enabled()

    def toggle_smart(self, update_callback=None):
        """Toggles Local Smart mode and applies/restores settings."""
        self.local_smart_enabled = not self.local_smart_enabled
        if self.local_smart_btn:
            self.local_smart_btn.selected = self.local_smart_enabled
        
        # Save to global config
        self.config_mgr.set_local_smart_enabled(self.local_smart_enabled)
        
        if self.local_smart_enabled:
            self.apply_smart()
        else:
            self.ctrl.restore_manual_mode(
                self.dd_provider, 
                self.dd_llm, 
                self.status_text, 
                dd_whisper=self.dd_whisper, 
                update_callback=update_callback
            )
        
        if self.local_smart_btn:
            safe_update_control(self.local_smart_btn)

    def apply_smart(self):
        """Applies the current hardware optimization."""
        self.ctrl.apply_optimization(
            self.dd_provider, 
            self.dd_llm, 
            self.status_text, 
            dd_whisper=self.dd_whisper
        )

    def initial_load(self, update_callback=None):
        """Handles initial state on view load."""
        if self.local_smart_enabled:
            self.apply_smart()
        else:
            provider = self.config_mgr.get_active_provider()
            if update_callback:
                update_callback(provider)
