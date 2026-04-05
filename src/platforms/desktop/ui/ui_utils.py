import logging
import threading
import time

import flet as ft

from src.core.constants import DEFAULT_LLM_MODELS
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

# --- Cache Structure ---
# { provider_name: {"models": list[str], "timestamp": float} }
_model_cache = {}
CACHE_TTL = 3600  # 1 hour in seconds


def sync_llm_models(page: ft.Page, config_mgr, provider: str, dd_model: ft.Dropdown, status_text: ft.Text = None, on_empty_results=None):
    """
    Common utility to fetch available LLM models for a provider and update a dropdown.
    Includes 1-hour caching, loading state, error handling, and background threading.
    
    Args:
        page: Flet page instance.
        config_mgr: Configuration manager.
        provider: Provider name (e.g., 'gemini', 'openai').
        dd_model: The dropdown control for models.
        status_text: Optional status text control for feedback.
        on_empty_results: Callback function(provider) if no models are returned.
    """
    logger.info(f"Syncing LLM models for provider: {provider}")

    current_time = time.time()

    # 1. Check Cache
    if provider in _model_cache:
        cache_entry = _model_cache[provider]
        if current_time - cache_entry["timestamp"] < CACHE_TTL:
            logger.info(f"Using cached model list for {provider} (TTL: {CACHE_TTL}s)")
            if not cache_entry["models"] and on_empty_results:
                on_empty_results(provider)
            else:
                _update_dropdown_ui(dd_model, cache_entry["models"], config_mgr, provider, status_text)
            
            if page:
                try:
                    page.update()
                except Exception:
                    pass
            return

    # 2. If not cached or expired, show loading state and fetch
    dd_model.options = [ft.dropdown.Option("loading", "モデルを取得中...")]
    dd_model.value = "loading"
    dd_model.disabled = True

    original_status = None
    if status_text:
        original_status = status_text.value
        status_text.value = f"📡 {provider} の利用可能モデルを取得中..."

    if page:
        try:
            page.update()
        except Exception:
            pass

    def fetch_task():
        try:
            # Setup client and fetch
            conf = config_mgr.get_provider_config(provider)
            client = LLMFactory.create_client(provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            models = client.get_available_models()

            # Update Cache
            _model_cache[provider] = {"models": models, "timestamp": time.time()}

            if not models:
                logger.warning(f"No models returned for {provider}.")
                if on_empty_results:
                    on_empty_results(provider)
                else:
                    # Fallback if no callback provided
                    fallback = DEFAULT_LLM_MODELS.get(provider, ["default"])
                    _update_dropdown_ui(dd_model, fallback, config_mgr, provider, status_text, original_status)
            else:
                # Update UI with actual models
                _update_dropdown_ui(dd_model, models, config_mgr, provider, status_text, original_status)

        except Exception as e:
            logger.error(f"Error fetching models for {provider}: {e}")
            fallback = DEFAULT_LLM_MODELS.get(provider, ["error-fallback"])
            _update_dropdown_ui(dd_model, fallback, config_mgr, provider, status_text, f"⚠️ {provider} モデル取得失敗: {str(e)[:40]}")

        if page:
            try:
                page.update()
            except Exception:
                pass

    # Run in background
    threading.Thread(target=fetch_task, daemon=True).start()


def _update_dropdown_ui(dd_model: ft.Dropdown, models: list[str], config_mgr, provider: str, status_text: ft.Text = None, status_val: str = None):
    """Internal helper to update the dropdown component."""
    dd_model.options = [ft.dropdown.Option(m) for m in models]

    # Try to restore last used model if it exists in the new list
    last_model = config_mgr.get_last_model(provider)
    if last_model in models:
        dd_model.value = last_model
    else:
        dd_model.value = models[0] if models else None

    dd_model.disabled = False

    if status_text and status_val:
        status_text.value = status_val
    elif status_text:
        # If no status_val provided, we might assume success/idle
        pass
