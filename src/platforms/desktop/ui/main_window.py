import logging

import flet as ft

from src.platforms.common.ui.views.chat_bot_view import ChatBotView
from src.platforms.desktop.ui.theme_manager import ThemeManager
from src.platforms.desktop.ui.views.about_view import AboutView
from src.platforms.desktop.ui.views.file_transcription_view import FileTranscriptionView
from src.platforms.desktop.ui.views.history_view import HistoryView
from src.platforms.desktop.ui.views.live_transcription_view import LiveTranscriptionView
from src.platforms.desktop.ui.views.settings_view import SettingsView

logger = logging.getLogger(__name__)


class MainWindow(ft.Row):
    def __init__(
        self,
        file_trans_view: FileTranscriptionView,
        live_trans_view: LiveTranscriptionView,
        settings_view: SettingsView,
        history_view: HistoryView,
        chat_view: ChatBotView,
        about_view: AboutView,
    ):
        super().__init__(expand=True)
        self.file_trans_view = file_trans_view
        self.live_trans_view = live_trans_view
        self.settings_view = settings_view
        self.history_view = history_view
        self.chat_view = chat_view
        self.about_view = about_view

        # Navigation Rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.SELECTED,
            min_width=80,
            min_extended_width=80,
            group_alignment=-0.9,
            expand=True,
            bgcolor=ft.Colors.TRANSPARENT,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.ATTACH_FILE_OUTLINED,
                    selected_icon=ft.Icons.ATTACH_FILE,
                    label="文字起こし",
                    padding=ft.padding.symmetric(vertical=5),
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.MIC_OUTLINED, selected_icon=ft.Icons.MIC, label="録音", padding=ft.padding.symmetric(vertical=5)
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label="履歴", padding=ft.padding.symmetric(vertical=5)
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CHAT_ROUNDED, selected_icon=ft.Icons.CHAT_ROUNDED, label="AI", padding=ft.padding.symmetric(vertical=5)
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="設定", padding=ft.padding.symmetric(vertical=5)
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INFO_OUTLINED, selected_icon=ft.Icons.INFO, label="情報", padding=ft.padding.symmetric(vertical=5)
                ),
            ],
            on_change=self._on_nav_change,
        )

        # Content Area with subtle container effect
        self.content_container = ft.Container(
            content=self.file_trans_view,
            expand=True,
            padding=ft.padding.all(30),
            alignment=ft.alignment.top_left,
            bgcolor=ThemeManager.SURFACE,
            border_radius=ft.border_radius.only(top_left=24),
            border=ft.border.only(top=ft.BorderSide(1, ThemeManager.BORDER), left=ft.BorderSide(1, ThemeManager.BORDER)),
        )

        # Setup status indicator
        self.setup_icon = ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_ROUNDED, size=20, color=ThemeManager.ACCENT)
        self.setup_status_text = ft.Text("...", size=10, color=ThemeManager.TEXT_SECONDARY)
        self.setup_container = ft.Container(
            content=ft.Row([self.setup_icon, self.setup_status_text], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            padding=ft.padding.only(bottom=20),
            visible=False,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),  # Spacer
                        self.nav_rail,
                        ft.Container(expand=True),  # Filler
                        self.setup_container,
                    ],
                    spacing=0,
                ),
                width=80,
                bgcolor=ThemeManager.BACKGROUND,
            ),
            self.content_container,
        ]

    def update_setup_status(self, status: str, is_critical: bool = True):
        """Update the background setup status display."""
        if is_critical and status != "Ready":
            self.setup_icon.visible = True
            self.setup_status_text.visible = True
            self.setup_status_text.value = status
            self.setup_container.visible = True
        else:
            self.setup_container.visible = False

        self.update()

    def switch_tab(self, index: int):
        """Programmatically switch tabs."""
        self.nav_rail.selected_index = index
        self._on_nav_change(ft.ControlEvent(target="", name="change", data=str(index), control=self.nav_rail, page=self.page))

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        logger.info(f"Navigation changed to index: {idx}")
        try:
            if idx == 0:
                self.content_container.content = self.file_trans_view
            elif idx == 1:
                self.content_container.content = self.live_trans_view
            elif idx == 2:
                self.content_container.content = self.history_view
                self.content_container.update()
                self.history_view.init_view()
            elif idx == 3:
                self.content_container.content = self.chat_view
                self.content_container.update()
            elif idx == 4:
                self.content_container.content = self.settings_view
                self.content_container.update()
                self.settings_view.init_view()
            elif idx == 5:
                self.content_container.content = self.about_view
                self.content_container.update()

            logger.info("Updating main window/page...")
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception as ex:
            logger.error(f"Error in navigation: {ex}", exc_info=True)
