import logging

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.setup_manager import setup_manager
from src.core.state import state
from src.platforms.common.ui.views.chat_bot_view import ChatBotView

# Desktop specific imports (moved from src.pc)
from src.platforms.desktop.controllers.history_ctrl import HistoryController
from src.platforms.desktop.controllers.minutes_ctrl import MinutesController
from src.platforms.desktop.controllers.transcription_ctrl import TranscriptionController
from src.platforms.desktop.ui.main_window import MainWindow
from src.platforms.desktop.ui.theme_manager import ThemeManager
from src.platforms.desktop.ui.views.about_view import AboutView
from src.platforms.desktop.ui.views.file_transcription_view import FileTranscriptionView
from src.platforms.desktop.ui.views.history_view import HistoryView
from src.platforms.desktop.ui.views.live_transcription_view import LiveTranscriptionView
from src.platforms.desktop.ui.views.settings_view import SettingsView

logger = logging.getLogger(__name__)


class DesktopApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.boot_text = ft.Text("Initializing system...", size=14, color=ft.Colors.BLUE_200)
        self.boot_progress = ft.ProgressBar(width=400, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.BLACK12)
        self._show_boot_screen()
        self._init_app_safe()

    def _show_boot_screen(self):
        ThemeManager.apply_theme(self.page)
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=64, color=ThemeManager.ACCENT),
                        ft.Text("Transform Movie to Text", size=24, weight=ft.FontWeight.BOLD, color=ThemeManager.TEXT_PRIMARY),
                        self.boot_text,
                        ft.Container(self.boot_progress, width=400, border_radius=10),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                expand=True,
                alignment=ft.alignment.center,
                bgcolor=ThemeManager.BACKGROUND,
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
            logger.info("DesktopApp: Starting initialization...")

            # Start background setup immediately if needed
            setup_manager.check_env()
            if not setup_manager.is_fully_ready:
                logger.warning("DesktopApp: Environment incomplete. Starting AI orchestration.")
                setup_manager.start_background_setup(on_status_change=self._on_setup_status_change, on_complete=self._on_setup_complete)

            self.config_mgr = ConfigManager()

            self._update_boot_status("Discovering AI environment...", 1)
            from src.core.whisper_transcriber import WhisperTranscriber

            self.transcriber = WhisperTranscriber()

            self._update_boot_status("Analyzing hardware & AI engine...", 2)
            try:
                self.hw_info = self.transcriber.get_hardware_info()
            except Exception as e:
                logger.warning(f"DesktopApp: Hardware info detection failed: {e}. Using safe defaults.")
                self.hw_info = {"ram": 0.0, "vram": 0.0, "device": "unknown"}

            self._update_boot_status("Initializing controllers...", 3)
            self.trans_ctrl = TranscriptionController(self.config_mgr, self.transcriber)
            self.minutes_ctrl = MinutesController(self.config_mgr)
            self.history_ctrl = HistoryController()

            self._update_boot_status("Preparing workspace views...", 4)
            self.file_picker = ft.FilePicker(on_result=self._on_file_result)
            self.save_picker = ft.FilePicker(on_result=self._on_save_result)
            self.folder_picker = ft.FilePicker()
            self.page.overlay.extend([self.file_picker, self.save_picker, self.folder_picker])

            self.file_trans_view = FileTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.live_trans_view = LiveTranscriptionView(self.page, self.config_mgr, self.trans_ctrl, self.hw_info)
            self.chat_view = ChatBotView(self.page, self.config_mgr)
            self.about_view = AboutView()
            self.settings_view = SettingsView(
                self.config_mgr, self.hw_info, self.transcriber.MODEL_REQUIREMENTS, history_ctrl=self.history_ctrl, minutes_ctrl=self.minutes_ctrl
            )
            self.history_view = HistoryView(self.history_ctrl, self.config_mgr, self.folder_picker, self.page)

            self._update_boot_status("Building UI layout...", 5)
            self.main_window = MainWindow(
                self.file_trans_view,
                self.live_trans_view,
                self.settings_view,
                self.history_view,
                self.chat_view,
                self.about_view,
            )
            self.page.controls.clear()
            self.page.add(self.main_window)

            self._setup_initial_values()
            logger.info("DesktopApp: Initialization successful.")

        except Exception as ex:
            self._handle_critical_error(ex)

    def _on_setup_status_change(self, status: str):
        """Update UI with background setup status."""
        logger.info(f"SETUP_STATUS: {status}")
        # If in boot screen, use boot status
        if hasattr(self, "boot_text") and self.boot_text.page:
            self.boot_text.value = f"Finalizing environment: {status}"
            self.page.update()

        # If MainWindow is already active, notify it
        if hasattr(self, "main_window") and self.main_window.page:
            self.main_window.update_setup_status(status)

    def _on_setup_complete(self):
        """Handle setup completion."""
        logger.info("SETUP_COMPLETE: Environment is now ready.")
        if hasattr(self, "main_window") and self.main_window.page:
            self.main_window.update_setup_status("Ready", is_critical=False)
            # Notify views to re-check their dependencies
            self.file_trans_view.refresh_dependency_state()
            self.live_trans_view.refresh_dependency_state()

    def _setup_page_properties(self):
        self.page.title = "Movie to Text v2.5 (Windows Specialized)"
        self.page.padding = 0
        self.page.window_width = 1100
        self.page.window_height = 850
        self.page.window_min_width = 800
        self.page.window_min_height = 600
        # self.page.window_title_bar_hidden = True # Cleaner look but requires custom window controls
        self.page.window_icon = "assets/icon.png"

    def _handle_critical_error(self, ex):
        import traceback

        error_stack = traceback.format_exc()
        logger.critical(f"FATAL BOOT ERROR: {ex}\n{error_stack}")
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=50),
                        ft.Text("Fatal Initialization Error (Desktop)", size=24, color="red", weight="bold"),
                        ft.Text(f"{ex}", selectable=True),
                        ft.ElevatedButton("Retry (Clear State)", on_click=lambda _: self._init_app_safe()),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )
        )
        self.page.update()

    def _setup_initial_values(self):
        # Initial values for settings/dropdowns
        pass

    def _on_file_result(self, e):
        if e.files:
            path = e.files[0].path
            state.set("selected_file_path", path)
            logger.info(f"File selected: {path}")

    def _on_save_result(self, e):
        if e.path:
            is_md = e.path.endswith(".md")
            content = state.get("minutes_text") if is_md else state.get("transcript_text")
            try:
                with open(e.path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as ex:
                logger.error(f"Save failed: {ex}")


def main(page: ft.Page):
    DesktopApp(page)
