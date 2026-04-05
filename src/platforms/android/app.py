import logging
import os
import threading
import flet as ft

from src.core.config_manager import ConfigManager
from src.core.platform_utils import get_log_path, is_android
from src.core.state import state
from src.platforms.android.ui.layouts import MobileLayout

logger = logging.getLogger(__name__)

class AndroidApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_mgr = None
        self.transcriber = None
        
        # UI Elements for Booting
        self.boot_text = ft.Text("Initializing MTT Mobile...", size=14, color=ft.Colors.BLUE_200)
        self.boot_progress = ft.ProgressBar(width=250, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.BLACK12)
        
        # Navigation State
        self.nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=ft.Icons.HISTORY, label="履歴"),
                ft.NavigationDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, selected_icon=ft.Icons.CHAT_BUBBLE, label="AIチャット"),
                ft.NavigationDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="設定"),
            ],
            on_change=self._on_nav_change,
            bgcolor=ft.Colors.SURFACE_VARIANT,
        )
        
        self._show_boot_screen()
        # Initialize in a separate thread to keep UI responsive
        threading.Thread(target=self._init_app_async, daemon=True).start()

    def _show_boot_screen(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.TRANSFORM_ROUNDED, size=80, color=ft.Colors.BLUE_400),
                        ft.Text("Transform Movie to Text", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text("Mobile Edition", size=14, color=ft.Colors.GREY_500),
                        ft.Container(height=40),
                        self.boot_text,
                        self.boot_progress,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )
        )
        self.page.update()

    def _update_boot_status(self, text: str, progress: float):
        logger.info(f"ANDROID BOOT: {text}")
        self.boot_text.value = text
        self.boot_progress.value = progress
        self.page.update()

    def _init_app_async(self):
        try:
            self._setup_page_properties()
            self._update_boot_status("Loading Configuration...", 0.3)
            self.config_mgr = ConfigManager()
            
            self._update_boot_status("Preparing AI Services...", 0.6)
            # Guarded import handled in WhisperTranscriber internally now
            from src.core.whisper_transcriber import WhisperTranscriber
            self.transcriber = WhisperTranscriber()

            self._update_boot_status("Building User Interface...", 0.9)
            # Lazy load views to speed up initial boot
            from src.platforms.common.ui.views.chat_bot_view import ChatBotView
            self.chat_view = ChatBotView(self.page, self.config_mgr)
            
            # Simple placeholders for other views until native implementation
            self.history_view = ft.Column([ft.Text("履歴機能は準備中です。デスクトップ版と同期予定。")], scroll=ft.ScrollMode.ADAPTIVE)
            self.settings_view = ft.Column([ft.Text("設定画面は準備中です。")], scroll=ft.ScrollMode.ADAPTIVE)

            self.views = [self.history_view, self.chat_view, self.settings_view]
            
            # Switch to main UI
            self._update_ui(0)
            logger.info("AndroidApp: Final boot successful.")

        except Exception as ex:
            self._handle_critical_error(ex)

    def _on_nav_change(self, e):
        self._update_ui(e.control.selected_index)

    def _update_ui(self, index: int):
        self.nav_bar.selected_index = index
        title = ["履歴", "AIチャット", "設定"][index]
        
        # Use our MobileLayout helper
        view = MobileLayout(
            content=self.views[index],
            title=title,
            nav_bar=self.nav_bar
        )
        
        self.page.views.clear()
        self.page.views.append(view)
        self.page.update()

    def _setup_page_properties(self):
        self.page.title = "MTT Mobile"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window_soft_input_mode = ft.WindowSoftInputMode.ADJUST_RESIZE

    def _handle_critical_error(self, ex):
        import traceback
        error_stack = traceback.format_exc()
        logger.critical(f"ANDROID FATAL BOOT: {ex}\n{error_stack}")
        
        self.page.clean()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.REPORT_PROBLEM_ROUNDED, color="red", size=60),
                        ft.Text("Initialization Failed", size=24, weight="bold"),
                        ft.Container(
                            content=ft.Text(f"{ex}", color=ft.Colors.RED_200, size=12, selectable=True),
                            padding=20,
                            bgcolor=ft.Colors.BLACK26,
                            border_radius=10,
                        ),
                        ft.Text("This may be due to incompatible libraries on this device.", size=12, color=ft.Colors.GREY_500),
                        ft.Row(
                            [
                                ft.ElevatedButton("Copy Full Log", icon=ft.Icons.COPY, on_click=self._copy_logs),
                                ft.ElevatedButton("Retry", icon=ft.Icons.REFRESH, on_click=lambda _: self._init_app_async()),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                expand=True,
                padding=20,
            )
        )
        self.page.update()

    def _copy_logs(self, e):
        path = get_log_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.page.set_clipboard(f.read())
                self.page.snack_bar = ft.SnackBar(ft.Text("Logs copied to clipboard!"))
                self.page.snack_bar.open = True
                self.page.update()
        except Exception as ex:
            logger.error(f"Failed to copy logs: {ex}")

def main(page: ft.Page):
    AndroidApp(page)
