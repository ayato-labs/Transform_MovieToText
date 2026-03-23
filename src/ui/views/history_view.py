import logging

import flet as ft

from src.controllers.history_ctrl import HistoryController
from src.core.state import state

logger = logging.getLogger(__name__)


class HistoryView(ft.Column):
    def __init__(self, controller: HistoryController, folder_picker: ft.FilePicker):
        super().__init__(expand=True, scroll="auto")
        self.controller = controller
        self.folder_picker = folder_picker
        self.selected_meeting_id = None

        self.folder_picker.on_result = self._on_folder_result

        self.history_list = ft.ListView(expand=True, spacing=10, padding=10)

        self.search_field = ft.TextField(
            label="キーワード検索 (FTS5)",
            hint_text="プロジェクト名、内容、キーワードで検索...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_submit=lambda _: self._refresh_history(),
        )

        self.project_dropdown = ft.Dropdown(label="プロジェクトで絞り込み", width=250, on_change=lambda _: self._on_project_filter_change())

        self.controls = [
            ft.Text("会議履歴", size=24, weight="bold"),
            ft.Text("過去の録音と議事録を確認・書き出せます。"),
            ft.Row([self.search_field, ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._refresh_history())]),
            ft.Row([self.project_dropdown]),
            ft.Divider(),
            self.history_list,
        ]

    def init_view(self):
        self._update_projects_list()
        self._refresh_history()

    def _update_projects_list(self):
        projects = self.controller.get_projects()
        self.project_dropdown.options = [ft.dropdown.Option(key="", text="全プロジェクト")]
        for p in projects:
            self.project_dropdown.options.append(ft.dropdown.Option(key=p, text=p))
        if self.page:
            self.update()

    def _refresh_history(self, search_query=None):
        self.history_list.controls.clear()

        query = search_query or self.search_field.value

        if query:
            logger.info(f"Filtering history with query: {query}")
            meetings = self.controller.search_meetings(query)
        else:
            meetings = self.controller.get_meetings()

        if not meetings:
            self.history_list.controls.append(ft.Text("履歴がありません。", italic=True, color="grey500"))
        else:
            for m in meetings:
                self.history_list.controls.append(self._build_meeting_card(m))

        if self.page:
            self.update()

    def _on_project_filter_change(self):
        selected = self.project_dropdown.value
        if selected:
            # Full-text search can also handle exact project names
            self._refresh_history(search_query=selected)
        else:
            self._refresh_history()

    def _build_meeting_card(self, meeting):
        meeting_id = meeting["id"]
        timestamp = meeting["timestamp"]
        title = meeting["title"]
        has_minutes = bool(meeting["minutes"])
        audio_path = meeting["audio_path"]

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.RECORD_VOICE_OVER if not has_minutes else ft.Icons.DESCRIPTION),
                            title=ft.Text(f"{title}"),
                            subtitle=ft.Column(
                                [
                                    ft.Text(f"日時: {timestamp}", size=12),
                                    ft.Row(
                                        [
                                            ft.Badge(content=ft.Text(meeting["project_name"] or "未分類", size=10), bgcolor="blue700")
                                            if meeting.get("project_name")
                                            else ft.Container(),
                                            ft.Text(f" {meeting['category'] or ''}", size=10, italic=True),
                                        ],
                                        spacing=5,
                                    ),
                                ]
                            ),
                        ),
                        ft.Row(
                            [
                                ft.TextButton("詳細を表示", icon=ft.Icons.BROWSE_GALLERY, on_click=lambda _: self._show_details(meeting)),
                                ft.TextButton(
                                    "音声を書き出し",
                                    icon=ft.Icons.DOWNLOAD,
                                    on_click=lambda _: self._start_export(meeting_id),
                                    visible=bool(audio_path),
                                ),
                            ],
                            alignment="end",
                        ),
                    ],
                    spacing=0,
                ),
                padding=10,
            )
        )
        return card

    def _show_details(self, meeting):
        # Update app state to show this meeting's content in the transcription/minutes tabs
        state.set("transcript_text", meeting["transcript"])
        state.set("minutes_text", meeting["minutes"] or "（未生成）")

        # Simple snackbar
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"「{meeting['title']}」の内容を各タブにロードしました"))
            self.page.snack_bar.open = True
            self.page.update()

    def _start_export(self, meeting_id):
        self.selected_meeting_id = meeting_id
        self.folder_picker.get_directory_path()

    def _on_folder_result(self, e: ft.FilePickerResultEvent):
        if not e.path or not self.selected_meeting_id:
            return

        success, message = self.controller.export_audio(self.selected_meeting_id, e.path)

        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(message))
            self.page.snack_bar.open = True
            self.page.update()

        self.selected_meeting_id = None
