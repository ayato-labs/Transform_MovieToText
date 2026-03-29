import time
from unittest.mock import MagicMock, patch

import flet as ft
import pytest

# Import target
from src.ui.ui_utils import _model_cache, sync_llm_models


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the global cache before each test."""
    _model_cache.clear()


def test_sync_llm_models_initial_fetch():
    """Verify that the first call fetches models via LLMFactory."""
    page = MagicMock(spec=ft.Page)
    config_mgr = MagicMock()
    config_mgr.get_provider_config.return_value = {"api_key": "test"}
    config_mgr.get_last_model.return_value = None

    dd_model = ft.Dropdown(options=[])
    provider = "gemini"

    mock_client = MagicMock()
    mock_client.get_available_models.return_value = ["model1", "model2"]

    with patch("src.llm.factory.LLMFactory.create_client", return_value=mock_client) as mock_create, patch("threading.Thread") as mock_thread:
        sync_llm_models(page, config_mgr, provider, dd_model)

        # Should have started a thread
        mock_thread.assert_called_once()

        # Manually trigger the target function to simulate thread execution
        target_fn = mock_thread.call_args[1]["target"]
        target_fn()

        # Verify results
        assert len(dd_model.options) == 2
        assert dd_model.options[0].key == "model1"
        assert dd_model.value == "model1"
        assert dd_model.disabled is False

        # Verify cache was populated
        assert provider in _model_cache
        assert _model_cache[provider]["models"] == ["model1", "model2"]


def test_sync_llm_models_caching():
    """Verify that subsequent calls within 1 hour use the cache."""
    page = MagicMock(spec=ft.Page)
    config_mgr = MagicMock()
    dd_model = ft.Dropdown(options=[])
    provider = "ollama_local"

    # Pre-populate cache
    _model_cache[provider] = {"models": ["cached_model"], "timestamp": time.time()}

    with patch("src.llm.factory.LLMFactory.create_client") as mock_create:
        sync_llm_models(page, config_mgr, provider, dd_model)

        # Should NOT have called factory or started a thread (it returns early for cache hits)
        mock_create.assert_not_called()
        assert dd_model.value == "cached_model"
        assert dd_model.disabled is False


def test_sync_llm_models_cache_expiry():
    """Verify that cache expires after 1 hour (3600s)."""
    page = MagicMock(spec=ft.Page)
    config_mgr = MagicMock()
    config_mgr.get_provider_config.return_value = {}
    dd_model = ft.Dropdown(options=[])
    provider = "gemini"

    # Pre-populate EXPIRED cache (2 hours ago)
    _model_cache[provider] = {"models": ["old_model"], "timestamp": time.time() - 7200}

    mock_client = MagicMock()
    mock_client.get_available_models.return_value = ["new_model"]

    with patch("src.llm.factory.LLMFactory.create_client", return_value=mock_client), patch("threading.Thread") as mock_thread:
        sync_llm_models(page, config_mgr, provider, dd_model)

        # Should start a thread because cache is expired
        mock_thread.assert_called_once()
        target_fn = mock_thread.call_args[1]["target"]
        target_fn()

        assert dd_model.value == "new_model"


def test_sync_llm_models_fallback_on_error():
    """Verify that defaults are used if API fails."""
    page = MagicMock(spec=ft.Page)
    config_mgr = MagicMock()
    config_mgr.get_provider_config.return_value = {}
    dd_model = ft.Dropdown(options=[])
    provider = "gemini"

    with patch("src.llm.factory.LLMFactory.create_client", side_effect=Exception("API Down")), patch("threading.Thread") as mock_thread:
        sync_llm_models(page, config_mgr, provider, dd_model)
        target_fn = mock_thread.call_args[1]["target"]
        target_fn()

        # Should use fallback from constants (DEFAULT_LLM_MODELS)
        assert len(dd_model.options) > 0
        assert dd_model.disabled is False
        assert "gemini" in str(dd_model.options[0].key).lower()
