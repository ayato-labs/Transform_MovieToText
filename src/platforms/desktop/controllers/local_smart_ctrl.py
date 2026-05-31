import logging
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.minutes_service import MinutesService
from src.core.resource_advisor import ResourceAdvisor

logger = logging.getLogger(__name__)


class LocalSmartController:
    """
    Zero-Setup Controller for 'Local Smart' optimization.
    Follows static hardware-tier patterns and automatically pulls missing models.
    """

    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr
        self.minutes_service = MinutesService(config_mgr)
        logger.info("LocalSmartController: Initialized.")

    def apply_optimization(self, dd_provider: ft.Dropdown, dd_llm: ft.Dropdown, status_text: ft.Text, dd_whisper: ft.Dropdown = None):
        """
        Applies strict hardware-aware optimization and triggers auto-pull if needed.
        Prioritizes existing models if the base name matches.
        """
        rec = ResourceAdvisor.get_best_match()
        target_model = rec["ollama"]

        # 1. Update Whisper (Static target)
        if dd_whisper:
            dd_whisper.value = rec["whisper"]
            dd_whisper.disabled = True
        
        self.config_mgr.set_whisper_model(rec["whisper"])

        # 2. Lock Provider to Local Ollama
        if dd_provider:
            dd_provider.value = "ollama_local"
            dd_provider.disabled = True
        
        self.config_mgr.set_active_provider("ollama_local")

        # 3. Check for Model and Pull if Missing
        all_local_models = self.minutes_service.get_available_models("ollama_local")
        if dd_llm:
            dd_llm.disabled = True  # Always lock in Smart mode

        # Base name matching (e.g. 'phi3.5:latest' matches 'phi3.5:3.8b...')
        base_name = target_model.split(":")[0]
        existing_match = next((m for m in all_local_models if m.split(":")[0] == base_name), None)

        if existing_match:
            # Existing model found, use it preferentially
            logger.info(f"LocalSmart: Found existing match '{existing_match}' for base '{base_name}'. Using it.")
            if dd_llm:
                dd_llm.options = [ft.dropdown.Option(m) for m in all_local_models]
                dd_llm.value = existing_match
            
            status_text.value = f"Local Smart: {rec['tier']} 構成 (既存 {existing_match}) を適用"
            self.config_mgr.set_last_model(existing_match)
        else:
            # Model missing, start background pull
            status_text.value = f"推奨モデル {target_model} を構成中... (初回のみ)"
            status_text.color = ft.Colors.BLUE_400
            threading.Thread(target=self._pull_and_update, args=(target_model, dd_llm, status_text, rec["tier"]), daemon=True).start()

    def _pull_and_update(self, model_name: str, dd_llm: ft.Dropdown, status_text: ft.Text, tier: str):
        """
        Background worker to pull model and refresh UI.
        """
        try:
            logger.info(f"LocalSmart: Pulling missing model '{model_name}'...")
            # Use Ollama CLI or SDK to pull
            logger.info(f"LocalSmart: Pulling model '{model_name}' - this may take some time...")
            import os

            import ollama

            # Ensure OLLAMA_HOST is set for this thread/SDK call
            os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
            ollama.pull(model_name)
            logger.info(f"LocalSmart: Pull of '{model_name}' finished.")

            # Refresh models after pull
            models = self.minutes_service.get_available_models("ollama_local")

            # Update UI controls safely
            def update_ui():
                if dd_llm:
                    dd_llm.options = [ft.dropdown.Option(m) for m in models]
                    dd_llm.value = model_name
                
                status_text.value = f"Local Smart: {tier} 構成の準備が完了しました"
                status_text.color = ft.Colors.GREEN_400
                if status_text.page:
                    status_text.page.update()

            # Since this is a thread, we rely on Flet's thread-safety or manual page.update()
            if status_text.page:
                update_ui()

            self.config_mgr.set_last_model(model_name)
            logger.info(f"LocalSmart: Successfully pulled and applied {model_name}")

        except Exception as e:
            error_msg = f"モデルの取得に失敗しました: {e}"
            logger.error(f"LocalSmart: Pull error: {e}")

            def update_error():
                status_text.value = f"⚠️ {error_msg}"
                status_text.color = ft.Colors.RED_400
                if status_text.page:
                    status_text.page.update()

            if status_text.page:
                update_error()

    def restore_manual_mode(
        self, dd_provider: ft.Dropdown, dd_llm: ft.Dropdown, status_text: ft.Text, dd_whisper: ft.Dropdown = None, update_callback=None
    ):
        """
        Unlocks UI components and restores manual configuration.
        """
        logger.info("LocalSmartController: Restoring manual mode.")
        if dd_provider:
            dd_provider.disabled = False
        if dd_llm:
            dd_llm.disabled = False
        if dd_whisper:
            dd_whisper.disabled = False

        status_text.value = "マニュアル設定モードに戻りました。"
        status_text.color = ft.Colors.GREY_500

        if update_callback and dd_provider:
            update_callback(dd_provider.value)

        if status_text.page:
            status_text.page.update()
        logger.info("LocalSmartController: Manual mode restored.")

        logger.info("LocalSmart: Restored to manual mode.")
