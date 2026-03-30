import logging
import os
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

# src.core.whisper_transcriber is now lazy-loaded
# src.ui and controllers are loaded only when environment is ready

logger = logging.getLogger(__name__)


class FletApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Movie to Text v2.0"
        self.page.theme_mode = "dark"
        self.page.window_width = 1100
        self.page.window_height = 850
        self.page.padding = 0
        self.page.window_icon = "assets/icon.png"

        logger.info("FletApp: Starting initialization...")
        self.config_mgr = ConfigManager()
        logger.info("FletApp: ConfigManager ready.")

        # Lazy load heavy components
        logger.info("FletApp: Lazy loading components (this may trigger library loads)...")
        from src.controllers.history_ctrl import HistoryController
        from src.controllers.minutes_ctrl import MinutesController
        from src.controllers.transcription_ctrl import TranscriptionController
        from src.core.whisper_transcriber import WhisperTranscriber
        from src.ui.main_window import MainWindow
        from src.ui.views.chat_bot_view import ChatBotView
        from src.ui.views.file_transcription_view import FileTranscriptionView
        from src.ui.views.history_view import HistoryView
        from src.ui.views.live_transcription_view import LiveTranscriptionView
        from src.ui.views.settings_view import SettingsView

        logger.info("FletApp: All core components imported.")
        self.transcriber = WhisperTranscriber()
        logger.info("FletApp: WhisperTranscriber initialized.")

        # Detect hardware (often heavy)
        logger.info("FletApp: Detecting hardware...")
        self.hw_info = self.transcriber.get_hardware_info()
        logger.info(f"FletApp: Hardware detected: {self.hw_info}")

        # Initialize Controllers
        logger.info("FletApp: Initializing controllers...")
        self.trans_ctrl = TranscriptionController(self.config_mgr, self.transcriber)
        self.minutes_ctrl = MinutesController(self.config_mgr)
        self.history_ctrl = HistoryController()
        logger.info("FletApp: Controllers ready.")

        # Setup File Pickers
        self.file_picker = ft.FilePicker(on_result=self._on_file_result)
        self.save_picker = ft.FilePicker(on_result=self._on_save_result)
        self.folder_picker = ft.FilePicker()  # HistoryView will use this
        self.page.overlay.extend([self.file_picker, self.save_picker, self.folder_picker])

        # Initialize Views
        logger.info("FletApp: Initializing views...")
        self.file_trans_view = FileTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
        self.live_trans_view = LiveTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
        self.chat_view = ChatBotView(self.page, self.config_mgr)
        self.settings_view = SettingsView(self.config_mgr, self.hw_info, self.transcriber.MODEL_REQUIREMENTS, history_ctrl=self.history_ctrl)
        self.history_view = HistoryView(self.history_ctrl, self.config_mgr, self.folder_picker, self.page)
        logger.info("FletApp: Views ready.")

        # Build Main UI
        logger.info("FletApp: Building UI layout...")
        self.main_window = MainWindow(self.file_trans_view, self.live_trans_view, self.settings_view, self.history_view, self.chat_view)
        self.page.add(self.main_window)

        # Initial View Setup
        self._setup_initial_values()
        logger.info("FletApp: Initialization process completed successfully.")

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
