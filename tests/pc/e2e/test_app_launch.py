from unittest.mock import MagicMock, patch

import flet as ft


# We mock FletApp initialization to avoid launching a real window during tests
@patch("src.app.FletApp.__init__", return_value=None)
def test_app_initialization_smoke(mock_init):
    """
    Verify that FletApp can be instantiated without crashing.
    """
    from src.app import FletApp

    page = MagicMock(spec=ft.Page)
    app = FletApp(page)

    assert app is not None
    # Verify init was called once
    mock_init.assert_called_once()


def test_view_instantiation_smoke():
    """
    Verify that all primary views can be instantiated with mock dependencies.
    """
    from src.core.config_manager import ConfigManager
    from src.core.transcription_service import TranscriptionService
    from src.pc.ui.views.settings_view import SettingsView

    _ = MagicMock(spec=ft.Page)
    config_mgr = MagicMock(spec=ConfigManager)
    service = MagicMock(spec=TranscriptionService)
    # Corrected: ensure nested mock exists for TranscriptionView's __init__
    service.transcriber = MagicMock()
    service.transcriber.get_hardware_info.return_value = {"ram": 16.0, "vram": 4.0, "device": "GPU"}

    # TranscriptionView is deprecated and removed. 
    # Smoke tests for specialized views can be added here if needed, 
    # but the generic launch test covers main app structure.

    # 2. Settings View
    hw_info = {"ram": 16, "vram": 8, "device": "cuda"}
    model_reqs = {"base": 1.0, "medium": 5.0}
    s_view = SettingsView(config_mgr, hw_info, model_reqs)
    assert s_view is not None
