import logging
import threading
import time

import flet as ft

from src.core.constants import DEFAULT_LLM_MODELS

logger = logging.getLogger(__name__)

# --- Cache Structure ---
# { provider_name: {"models": list[str], "timestamp": float} }
_model_cache = {}
CACHE_TTL = 3600  # 1 hour in seconds


def clear_model_cache(provider: str = None):
    """Clears the model cache, forcing a fresh fetch on next request."""
    if provider and provider in _model_cache:
        del _model_cache[provider]
        logger.info(f"Cleared model cache for {provider}")
    elif not provider:
        _model_cache.clear()
        logger.info("Cleared all model caches")


def safe_update(page: ft.Page):
    """
    Safely updates the Flet page, logging failures instead of crashing
    or silently swallowing important errors.
    """
    if not page:
        return
    try:
        page.update()
    except Exception as e:
        # Often happens during shutdown or if the page was closed prematurely.
        # We log at DEBUG to avoid flooding the user logs in production,
        # but keep it visible for developer diagnostics.
        logger.debug(f"UI update skipped (Page state likely invalid): {e}")


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

            safe_update(page)
            return

    # 2. If not cached or expired, show loading state and fetch
    dd_model.options = [ft.dropdown.Option("loading", "モデルを取得中...")]
    dd_model.value = "loading"
    dd_model.disabled = True

    original_status = None
    if status_text:
        original_status = status_text.value
        status_text.value = f"📡 {provider} の利用可能モデルを取得中..."

    safe_update(page)

    def fetch_task():
        try:
            # Fetch filtered models through ConfigManager (which enforces edition rules)
            models = config_mgr.get_llm_models(provider)

            # Update Cache (only if models were returned)
            if models:
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

        safe_update(page)

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
        logger.debug(f"UI Update: {provider} model list refreshed with {len(models)} items.")


def safe_update_control(control: ft.Control):
    """Safely updates a single control."""
    if not control or not control.page:
        return
    try:
        control.update()
    except Exception as e:
        logger.debug(f"Control update skipped: {e}")


class Debouncer:
    """
    Utility to delay execution of a function until after a specified silence period.
    Commonly used for 'Search-as-you-type' to avoid flooding the DB/API with requests.
    """

    def __init__(self, delay=0.4):
        self.delay = delay
        self._timer = None

    def run(self, action, *args, **kwargs):
        """Triggers the action after the delay, cancelling any pending ones."""
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.delay, action, args=args, kwargs=kwargs)
        self._timer.start()

    def cancel(self):
        """Cancels any pending action."""
        if self._timer is not None:
            self._timer.cancel()
