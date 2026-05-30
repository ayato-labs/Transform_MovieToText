import time
from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from src.core.config_manager import ConfigManager
from src.platforms.desktop.ui.views.history_view import HistoryView


@pytest.fixture
def mock_deps():
    ctrl = MagicMock()
    config = MagicMock(spec=ConfigManager)
    picker = MagicMock(spec=ft.FilePicker)
    page = MagicMock(spec=ft.Page)
    return ctrl, config, picker, page


def test_history_search_as_you_type_flow(mock_deps):
    """
    System test: Simulate typing in HistoryView and check if refresh is triggered after debounce.
    """
    ctrl, config, picker, page = mock_deps

    # Instance the view
    view = HistoryView(controller=ctrl, config_mgr=config, folder_picker=picker, page=page)

    # Mock the refresh method to track calls
    with patch.object(view, "_refresh_history") as mock_refresh:
        # Simulate typing 'Ayato'
        view.search_field.value = "Ayato"
        # Manually trigger the event handler
        view._on_search_change(None)

        # Should not be called immediately (debounce is 0.3s)
        assert mock_refresh.call_count == 0

        # Wait for debounce
        time.sleep(0.4)

        # Should be called once now
        assert mock_refresh.call_count == 1


def test_chat_preview_as_you_type_flow(mock_deps):
    """
    System test: Simulate typing in ChatBotView and check if context preview appears.
    """
    _, config, _, page = mock_deps
    from src.platforms.common.ui.views.chat_bot_view import ChatBotView

    config.get_active_provider.return_value = "ollama_local"
    config.get_provider_config.return_value = {"model": "llama3"}
    config.get_edition.return_value = "pro"

    with patch("src.platforms.common.ui.views.chat_bot_view.history_mgr") as mock_hm, \
         patch("src.platforms.common.ui.views.chat_bot_view.QueryAnalyzer") as mock_qa:
        # Setup dependencies
        mock_hm.get_meetings_filtered.return_value = [{"title": "Meeting X"}]
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {"projects": [], "categories": [], "keywords": ["Meet"]}
        mock_qa.return_value = mock_analyzer

        view = ChatBotView(page=page, config_mgr=config)

        # Simulate typing (minimum 3 chars required in our implementation)
        view.input_field.value = "Meet"
        view._on_input_change(None)

        # Wait for debounce (0.5s in ChatBotView)
        time.sleep(0.7)

        # Check if preview became visible and contains the result
        assert view.context_preview.visible is True
        assert any("Meeting X" in str(c.content.value) for c in view.context_preview.controls if hasattr(c, "content"))
