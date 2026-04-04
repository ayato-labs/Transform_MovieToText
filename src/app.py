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
from src.core.platform_utils import get_log_path, is_android
from src.core.state import state

# src.core.whisper_transcriber is now lazy-loaded
# src.ui and controllers are loaded only when environment is ready


class FletApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.boot_text = ft.Text("Initializing system...", size=14, color=ft.Colors.BLUE_200)
        self.boot_progress = ft.ProgressBar(width=400, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.BLACK12)
        self._show_boot_screen()
        self._init_app_safe()

    def _show_boot_screen(self):
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=50, color=ft.Colors.BLUE_400),
                        ft.Text("Transform Movie to Text", size=20, weight=ft.FontWeight.BOLD),
                        self.boot_text,
                        self.boot_progress,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )
        )
        self.page.update()

    def _update_boot_status(self, text: str, progress: float):
        logger.info(f"BOOT: {text}")
        self.boot_text.value = text
        self.boot_progress.value = progress / 5.0
        self.page.update()

    def _init_app_safe(self):
        try:
            self._setup_page_properties()
            logger.info("FletApp: Starting initialization...")
            self.config_mgr = ConfigManager()
            logger.info("FletApp: ConfigManager ready.")

            # Lazy load heavy components
            self._update_boot_status("Loading AI standard modules...", 1)
            from src.core.whisper_transcriber import WhisperTranscriber
            
            self._update_boot_status("Loading history and controllers...", 2)
            from src.pc.controllers.history_ctrl import HistoryController
            from src.pc.controllers.minutes_ctrl import MinutesController
            from src.pc.controllers.transcription_ctrl import TranscriptionController
            
            self._update_boot_status("Loading UI components...", 3)
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
            self._update_boot_status("Preparing workspace views...", 4)
            self.file_trans_view = FileTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.live_trans_view = LiveTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.chat_view = ChatBotView(self.page, self.config_mgr)
            self.settings_view = SettingsView(self.config_mgr, self.hw_info, self.transcriber.MODEL_REQUIREMENTS, history_ctrl=self.history_ctrl)
            self.history_view = HistoryView(self.history_ctrl, self.config_mgr, self.folder_picker, self.page)

            # Build Main UI
            self._update_boot_status("Building UI layout...", 5)
            from src.pc.ui.main_window import MainWindow
            self.main_window = MainWindow(self.file_trans_view, self.live_trans_view, self.settings_view, self.history_view, self.chat_view)
            self.page.controls.clear()
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

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=50),
                        ft.Text("Fatal Initialization Error", size=24, color="red", weight="bold"),
                        ft.Divider(),
                        ft.Text(f"{ex}", selectable=True, color="white"),
                        ft.ExpansionTile(
                            title=ft.Text("Show Stack Trace (for Dev)", size=12),
                            controls=[ft.Text(error_stack, size=10, selectable=True, color="grey")],
                        ),
                        ft.ElevatedButton("Retry (Clear State)", on_click=lambda _: self._init_app_safe()),
                        ft.TextButton("Copy Debug Logs to Clipboard", icon=ft.Icons.COPY_ALL, on_click=self._on_copy_error_logs),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
                padding=20,
            )
        )
        self.page.update()

    def _on_copy_error_logs(self, e):
        try:
            from src.core.platform_utils import get_log_path
            path = get_log_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.page.set_clipboard(content)
                self.page.snack_bar = ft.SnackBar(ft.Text("Logs copied to clipboard!"))
                self.page.snack_bar.open = True
                self.page.update()
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Log file not found."))
                self.page.snack_bar.open = True
                self.page.update()
        except Exception as ex:
            logger.error(f"Failed to copy error logs: {ex}")

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


def init_logging():
    log_file = get_log_path()
    # Basic config for stdout
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    # Add FileHandler for persistent logs on Android
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    # Global exception handler
    import sys
    import traceback
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        
    sys.excepthook = handle_exception


if __name__ == "__main__":
    init_logging()
    ft.app(target=main)
