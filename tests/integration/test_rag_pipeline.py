from unittest.mock import MagicMock, patch
import pytest
import flet as ft
from src.platforms.common.ui.views.chat_bot_view import ChatBotView
from src.core.config_manager import ConfigManager

@pytest.fixture
def mock_page():
    page = MagicMock(spec=ft.Page)
    return page

@pytest.fixture
def mock_config():
    config = MagicMock(spec=ConfigManager)
    config.get_active_provider.return_value = "ollama_local"
    config.get_local_smart_enabled.return_value = False
    config.get_edition.return_value = "pro"
    config.get_provider_config.return_value = {"model": "llama3"}
    # Mock get_llm_client to return a mock client
    mock_client = MagicMock()
    config.get_llm_client.return_value = mock_client
    return config

def test_chat_bot_rag_pipeline_flow(mock_page, mock_config):
    """
    Test the flow from _run_rag_worker to history_mgr.get_meetings_filtered.
    Ensures that intent analysis (mocked) leads to correct database filters.
    """
    # Mock history_mgr BEFORE instantiating the view
    with patch("src.platforms.common.ui.views.chat_bot_view.history_mgr") as mock_hm:
        view = ChatBotView(page=mock_page, config_mgr=mock_config)
        
        mock_hm.get_projects.return_value = ["Project-X"]
        mock_hm.get_categories.return_value = ["Security"]
        mock_hm.get_meetings_filtered.return_value = []
        
        # Mock QueryAnalyzer
        with patch("src.platforms.common.ui.views.chat_bot_view.QueryAnalyzer") as mock_qa_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = {
                "projects": ["Project-X"],
                "categories": ["Security"],
                "keywords": ["vulnerability"]
            }
            mock_qa_class.return_value = mock_analyzer
            
            query = "Project-X の Security について教えて"
            
            # Since _run_rag_worker is usually threaded, we call it directly
            view._run_rag_worker(query)
            
            # Verify DB filter was called with correct metadata
            mock_hm.get_meetings_filtered.assert_called_with(
                project_names=["Project-X"],
                categories=["Security"],
                search_query="vulnerability",
                limit=5
            )

def test_chat_bot_context_preview_integration(mock_page, mock_config):
    """
    Test that _update_context_preview correctly populates UI controls.
    """
    with patch("src.platforms.common.ui.views.chat_bot_view.history_mgr") as mock_hm:
        view = ChatBotView(page=mock_page, config_mgr=mock_config)
        view.input_field.value = "Test query"
        
        mock_hm.get_projects.return_value = []
        mock_hm.get_categories.return_value = []
        mock_hm.get_meetings_filtered.return_value = [
            {"title": "Meeting A", "minutes": "Content A", "timestamp": "2024-01-01"},
            {"title": "Meeting B", "minutes": None, "transcript": "Content B", "timestamp": "2024-01-02"}
        ]
        
        # Trigger preview update
        view._update_context_preview()
        
        # Verify UI state
        assert view.context_preview.visible is True
        # Controls: 1 (Text "Related:") + 2 (Meeting containers) = 3
        assert len(view.context_preview.controls) == 3
        assert view.context_preview.controls[1].content.value == "Meeting A"
        assert view.context_preview.controls[2].content.value == "Meeting B"
