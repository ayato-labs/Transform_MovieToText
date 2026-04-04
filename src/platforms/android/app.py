import logging
import os
import flet as ft

from src.core.config_manager import ConfigManager
from src.core.platform_utils import get_log_path, is_android
from src.core.state import state

logger = logging.getLogger(__name__)

class AndroidApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.boot_text = ft.Text("Android System Booting...", size=14, color=ft.Colors.GREEN_200)
        self.boot_progress = ft.ProgressBar(width=300, color=ft.Colors.GREEN_400, bgcolor=ft.Colors.BLACK12)
        self._show_boot_screen()
        self._init_app_safe()

    def _show_boot_screen(self):
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.PHONE_ANDROID, size=50, color=ft.Colors.GREEN_400),
                        ft.Text("Transform Movie to Text Mobile", size=18, weight=ft.FontWeight.BOLD),
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
        logger.info(f"ANDROID BOOT: {text}")
        self.boot_text.value = text
        self.boot_progress.value = progress / 3.0
        self.page.update()

    def _init_app_safe(self):
        try:
            self._setup_page_properties()
            self.config_mgr = ConfigManager()
            
            self._update_boot_status("Loading Core Services...", 1)
            # Avoid torch/whisper local if possible, or use guarded import
            from src.core.whisper_transcriber import WhisperTranscriber
            self.transcriber = WhisperTranscriber()

            self._update_boot_status("Initializing Mobile UI...", 2)
            # Currently sharing desktop views for compatibility, but ready for Mobile-specific views
            from src.platforms.desktop.ui.views.chat_bot_view import ChatBotView
            self.chat_view = ChatBotView(self.page, self.config_mgr)

            self._update_boot_status("Finalizing...", 3)
            # Simpler UI for Android for now
            self.page.controls.clear()
            self.page.add(
                ft.AppBar(title=ft.Text("MTT Mobile"), bgcolor=ft.Colors.SURFACE_VARIANT),
                ft.Container(content=self.chat_view, padding=10, expand=True)
            )
            self.page.update()
            
            logger.info("AndroidApp: Boot successful.")

        except Exception as ex:
            self._handle_critical_error(ex)

    def _setup_page_properties(self):
        self.page.title = "MTT Mobile"
        self.page.theme_mode = "dark"
        self.page.padding = 0

    def _handle_critical_error(self, ex):
        import traceback
        error_stack = traceback.format_exc()
        logger.critical(f"ANDROID FATAL BOOT: {ex}\n{error_stack}")
        self.page.controls.clear()
        self.page.add(
            ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=50),
                    ft.Text("App Initialization Failed", size=20, weight="bold"),
                    ft.Text(f"{ex}", selectable=True, size=12),
                    ft.ElevatedButton("Copy Logs", on_click=self._copy_logs),
                    ft.ElevatedButton("Retry", on_click=lambda _: self._init_app_safe()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        self.page.update()

    def _copy_logs(self, e):
        path = get_log_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.page.set_clipboard(f.read())
            self.page.snack_bar = ft.SnackBar(ft.Text("Logs copied!"))
            self.page.snack_bar.open = True
            self.page.update()

def main(page: ft.Page):
    AndroidApp(page)
