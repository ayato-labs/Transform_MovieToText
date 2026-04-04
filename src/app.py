import logging
import os
import sys
import warnings

# Suppress HuggingFace and Requests warnings before other imports
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

logger = logging.getLogger(__name__)

try:
    from requests.exceptions import RequestsDependencyWarning

    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    logger.debug("RequestsDependencyWarning not available, skipping filter.")

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.state import state
from src.core.platform_utils import is_android

# src.core.whisper_transcriber is now lazy-loaded
# src.ui and controllers are loaded only when environment is ready

logger = logging.getLogger(__name__)


class FletApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self._init_app_safe()

    def _init_app_safe(self):
        try:
            self._setup_page_properties()
            logger.info("FletApp: Starting initialization...")
            self.config_mgr = ConfigManager()
            logger.info("FletApp: ConfigManager ready.")

            # Lazy load heavy components
            logger.info("FletApp: Lazy loading components...")
            from src.core.whisper_transcriber import WhisperTranscriber
            from src.pc.controllers.history_ctrl import HistoryController
            from src.pc.controllers.minutes_ctrl import MinutesController
            from src.pc.controllers.transcription_ctrl import TranscriptionController
            from src.pc.ui.main_window import MainWindow
            from src.pc.ui.views.chat_bot_view import ChatBotView
            from src.pc.ui.views.file_transcription_view import FileTranscriptionView
            from src.pc.ui.views.history_view import HistoryView
            from src.pc.ui.views.live_transcription_view import LiveTranscriptionView
            from src.pc.ui.views.settings_view import SettingsView

            logger.info("FletApp: All core components imported.")
            self.transcriber = WhisperTranscriber()
            logger.info("FletApp: WhisperTranscriber initialized.")

            # Hardware detection
            try:
                logger.info("FletApp: Detecting hardware...")
                self.hw_info = self.transcriber.get_hardware_info()
            except Exception as e:
                logger.warning(f"Hardware detection failed, using fallback: {e}")
                self.hw_info = {"ram": 0.0, "vram": 0.0, "device": "unknown"}

            logger.info(f"FletApp: Hardware detected: {self.hw_info}")

            # Initialize Controllers
            logger.info("FletApp: Initializing controllers...")
            self.trans_ctrl = TranscriptionController(self.config_mgr, self.transcriber)
            self.minutes_ctrl = MinutesController(self.config_mgr)
            self.history_ctrl = HistoryController()

            # Page Overlay controls
            self.file_picker = ft.FilePicker(on_result=self._on_file_result)
            self.save_picker = ft.FilePicker(on_result=self._on_save_result)
            self.folder_picker = ft.FilePicker()
            self.page.overlay.extend([self.file_picker, self.save_picker, self.folder_picker])

            # Initialize Views
            logger.info("FletApp: Initializing views...")
            self.file_trans_view = FileTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.live_trans_view = LiveTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.chat_view = ChatBotView(self.page, self.config_mgr)
            self.settings_view = SettingsView(self.config_mgr, self.hw_info, self.transcriber.MODEL_REQUIREMENTS, history_ctrl=self.history_ctrl)
            self.history_view = HistoryView(self.history_ctrl, self.config_mgr, self.folder_picker, self.page)

            # Build Main UI
            logger.info("FletApp: Building UI layout...")
            self.main_window = MainWindow(self.file_trans_view, self.live_trans_view, self.settings_view, self.history_view, self.chat_view)
            self.page.add(self.main_window)

            self._setup_initial_values()
            logger.info("FletApp: Initialization successful.")

        except Exception as ex:
            self._handle_critical_error(ex)

    def _setup_page_properties(self):
        self.page.title = "Movie to Text v2.0"
        self.page.theme_mode = "dark"
        self.page.padding = 0
        if not is_android():
            self.page.window_width = 1100
            self.page.window_height = 850
            self.page.window_icon = "assets/icon.png"

    def _handle_critical_error(self, ex):
        import traceback
        error_stack = traceback.format_exc()
        logger.critical(f"FATAL BOOT ERROR: {ex}\n{error_stack}")
        
        # Clear page and show error
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=50),
                    ft.Text("Fatal Initialization Error", size=24, color="red", weight="bold"),
                    ft.Divider(),
                    ft.Text(f"{ex}", selectable=True, color="white"),
                    ft.ExpansionTile(
                        title=ft.Text("Show Stack Trace (for Dev)", size=12),
                        controls=[ft.Text(error_stack, size=10, selectable=True, color="grey")]
                    ),
                    ft.ElevatedButton("Retry (Clear State)", on_click=lambda _: self._init_app_safe())
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True, alignment=ft.alignment.center, padding=20
            )
        )
        self.page.update()

    def _setup_initial_values(self):
        # Whisper model options
        model_options = []
        for model_name in self.transcriber.MODEL_REQUIREMENTS:
            model_options.append(ft.dropdown.Option(key=model_name, text=model_name))

        # Individual view initialization is handled during construction or nav
        # self.transcription_view.init_view(model_options)
        # Other views initialized on selection

    def _on_file_result(self, e):
        if e.files:
            path = e.files[0].path
            state.set("selected_file_path", path)
            logger.info(f"File selected: {path}")

    def _on_save_result(self, e):
        if e.path:
            # Check file extension to decide content
            is_md = e.path.endswith(".md")
            content = state.get("minutes_text") if is_md else state.get("transcript_text")
            try:
                with open(e.path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._show_snack(f"ファイルを保存しました: {os.path.basename(e.path)}")
            except Exception as ex:
                self._show_snack(f"保存失敗: {ex}")


def main(page: ft.Page):
    from src.core.setup_wizard import is_env_ready
    from src.core.setup_wizard import main as setup_main

    missing = is_env_ready()
    if missing:
        logger.warning(f"Missing dependencies: {missing}. Launching Setup Wizard.")
        setup_main(page)
    else:
        FletApp(page)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ft.app(target=main)
