import logging

import flet as ft

from src.controllers.history_ctrl import HistoryController
from src.core.config_manager import ConfigManager
from src.core.constants import DEFAULT_LLM_MODELS, DEFAULT_PROVIDERS
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber
from src.ui.ui_utils import sync_llm_models

logger = logging.getLogger(__name__)


class HistoryView(ft.Column):
    def __init__(self, controller: HistoryController, config_mgr: ConfigManager, folder_picker: ft.FilePicker, page: ft.Page = None):
        super().__init__(expand=True, scroll="auto")
        self._page = page
        self.controller = controller
        self.config_mgr = config_mgr
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
        if self._page:
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

        if self._page:
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

        # To avoid closure issues in loops, use default arguments in lambdas:
        # lambda _: self.func(meeting)  => lambda _, m=meeting: self.func(m)

        return ft.Card(
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
                                            ft.Container(
                                                content=ft.Text(meeting["project_name"] or "未分類", size=10, color="white"),
                                                bgcolor="blue700",
                                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                                border_radius=10,
                                            )
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
                                ft.TextButton("詳細を表示", icon=ft.Icons.BROWSE_GALLERY, on_click=lambda _, m=meeting: self._show_details(m)),
                                ft.TextButton(
                                    "音声を書き出し",
                                    icon=ft.Icons.DOWNLOAD,
                                    on_click=lambda _, mid=meeting_id: self._start_export(mid),
                                    visible=bool(audio_path),
                                ),
                                ft.TextButton(
                                    "議事録を生成",
                                    icon=ft.Icons.STARS,
                                    on_click=lambda _, m=meeting: self._generate_minutes(m),
                                ),
                                ft.VerticalDivider(width=10, color=ft.Colors.TRANSPARENT),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="この履歴を削除",
                                    on_click=lambda _, mid=meeting_id, t=title: self._confirm_delete(mid, t),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=0,
                ),
                padding=10,
            )
        )

    def _show_details(self, meeting):
        import os

        logger.info(f"Showing details for meeting ID: {meeting['id']}")
        details = self.controller.get_meeting_details(meeting["id"])
        if not details:
            return

        m = details["meeting"]
        v_contexts = details["visual_contexts"]

        transcript_control = ft.TextField(
            value=m["transcript"],
            multiline=True,
            read_only=True,
            min_lines=15,
            max_lines=20,
            text_size=14,
            border=ft.InputBorder.NONE,
        )

        minutes_control = ft.TextField(
            value=m["minutes"] or "（未生成）",
            multiline=True,
            read_only=True,
            min_lines=15,
            max_lines=20,
            text_size=14,
            border=ft.InputBorder.NONE,
        )

        # Visual Context Row
        visual_row = ft.Row(scroll="always", spacing=10)
        for ctx in v_contexts:
            if ctx.get("image_path") and os.path.exists(ctx["image_path"]):
                visual_row.controls.append(
                    ft.Column(
                        [ft.Image(src=ctx["image_path"], width=150, border_radius=5), ft.Text(f"{ctx['timestamp']:.1f}s", size=10)],
                        horizontal_alignment="center",
                    )
                )

        def on_provider_change(e):
            new_provider = e.control.value
            sync_llm_models(self._page, self.config_mgr, new_provider, dd_model)

        dd_provider = ft.Dropdown(
            label="プロバイダー",
            width=150,
            options=[ft.dropdown.Option(k) for k in DEFAULT_PROVIDERS],
            value=self.config_mgr.get_active_provider(),
            on_change=on_provider_change,
            text_size=12,
        )

        initial_provider = dd_provider.value or "gemini"

        dd_model = ft.Dropdown(
            label="モデル",
            width=200,
            options=[],  # Will be filled by initial sync below
            text_size=12,
        )

        # Initial sync for the first load
        sync_llm_models(self._page, self.config_mgr, initial_provider, dd_model)

        initial_provider = dd_provider.value or "gemini"

        # Initial model list (synchronous for the very first load to avoid empty UI)
        try:
            # We use a placeholder and trigger an update immediately
            initial_models = DEFAULT_LLM_MODELS.get(initial_provider, ["loading..."])
        except Exception as ex:
            logger.error(f"Failed to get initial models: {ex}")
            initial_models = ["default"]

        dd_model = ft.Dropdown(
            label="モデル",
            width=200,
            options=[ft.dropdown.Option(m) for m in initial_models],
            value=self.config_mgr.get_last_model() or (initial_models[0] if initial_models else None),
            text_size=12,
        )

        def on_copy_transcript(e):
            self._page.set_clipboard(transcript_control.value)
            self._page.snack_bar = ft.SnackBar(ft.Text("文字起こしをコピーしました"))
            self._page.snack_bar.open = True
            self._page.update()

        def on_copy_minutes(e):
            self._page.set_clipboard(minutes_control.value)
            self._page.snack_bar = ft.SnackBar(ft.Text("議事録をコピーしました"))
            self._page.snack_bar.open = True
            self._page.update()

        def on_regenerate(e):
            e.control.disabled = True
            e.control.text = "生成中..."
            self._page.update()

            try:
                cfg = ConfigManager()
                wt = WhisperTranscriber()
                svc = TranscriptionService(cfg, wt)

                new_minutes = self.controller.regenerate_minutes(m["id"], m["transcript"], svc, provider=dd_provider.value, model=dd_model.value)
                minutes_control.value = new_minutes
                self._page.snack_bar = ft.SnackBar(ft.Text(f"議事録を再生成しました ({dd_model.value})"))
            except Exception as ex:
                self._page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {ex}"), bgcolor=ft.Colors.RED_400)

            e.control.disabled = False
            e.control.text = "AI議事録を再生成"
            self._page.snack_bar.open = True
            self._page.update()

        def close_details(e):
            if self._page.dialog:
                self._page.dialog.open = False
            self._page.update()

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DESCRIPTION),
                    ft.Text(f"{m['title']}", expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(ft.Icons.CLOSE, on_click=close_details),
                ],
                alignment="spaceBetween",
            ),
            content=ft.Container(
                width=800,
                height=600,
                content=ft.Column(
                    [
                        ft.Tabs(
                            selected_index=0,
                            animation_duration=300,
                            tabs=[
                                ft.Tab(
                                    text="文字起こし",
                                    icon=ft.Icons.TEXT_FIELDS_ROUNDED,
                                    content=ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.IconButton(ft.Icons.COPY, on_click=on_copy_transcript, tooltip="コピー"),
                                                ],
                                                alignment="end",
                                            ),
                                            ft.Container(transcript_control, bgcolor=ft.Colors.BLACK12, padding=10, border_radius=5, expand=True),
                                        ],
                                        scroll="auto",
                                        expand=True,
                                    ),
                                ),
                                ft.Tab(
                                    text="AI議事録",
                                    icon=ft.Icons.STARS,
                                    content=ft.Column(
                                        [
                                            ft.Container(
                                                content=ft.Row(
                                                    [
                                                        dd_provider,
                                                        dd_model,
                                                        ft.ElevatedButton("AI議事録を再生成", icon=ft.Icons.REFRESH, on_click=on_regenerate),
                                                        ft.IconButton(ft.Icons.COPY, on_click=on_copy_minutes, tooltip="コピー"),
                                                    ],
                                                    alignment="end",
                                                    spacing=10,
                                                ),
                                                padding=ft.padding.only(bottom=10),
                                            ),
                                            ft.Container(minutes_control, bgcolor=ft.Colors.BLACK12, padding=10, border_radius=5, expand=True),
                                        ],
                                        scroll="auto",
                                        expand=True,
                                    ),
                                ),
                                ft.Tab(
                                    text="画像コンテキスト",
                                    icon=ft.Icons.IMAGE,
                                    content=ft.Column(
                                        [
                                            ft.Text("ビデオから抽出されたフレーム:", size=12, italic=True),
                                            visual_row if visual_row.controls else ft.Text("画像データはありません。", color="grey500"),
                                        ],
                                        scroll="auto",
                                        spacing=10,
                                        expand=True,
                                    ),
                                ),
                            ],
                            expand=True,
                        ),
                        ft.Divider(),
                        ft.Row(
                            [
                                ft.Text(f"📍 プロジェクト: {m['project_name'] or '未分類'} | 📅 日時: {m['timestamp']}", size=12, color="grey400"),
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            ft.Icons.DOWNLOAD,
                                            icon_color="blue400",
                                            tooltip="音声をエクスポート",
                                            on_click=lambda _, mid=m["id"]: self._start_export(mid),
                                        ),
                                        ft.IconButton(
                                            ft.Icons.DELETE,
                                            icon_color="red400",
                                            tooltip="削除",
                                            on_click=lambda _, mid=m["id"], t=m["title"]: self._confirm_delete(mid, t),
                                        ),
                                    ]
                                ),
                            ],
                            alignment="spaceBetween",
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
            ),
        )

        if self._page:
            logger.info("Opening detail dialog via page.open()")
            self._page.open(dlg)
            self._page.update()
        else:
            logger.error("Cannot show details: self._page is None")

    def _generate_minutes(self, meeting):
        logger.info(f"Generating minutes for meeting ID: {meeting['id']} (Legacy trigger)")
        self._show_details(meeting)
        # Find MainWindow and switch tab
        # Based on src/app.py, HistoryView is part of MainWindow
        if hasattr(self.parent, "switch_tab"):
            self.parent.switch_tab(1)  # 1 is AI Minutes tab
        elif hasattr(self._page, "main_window"):
            # Fallback if parent is not main_window directly
            self._page.main_window.switch_tab(1)

    def _start_export(self, meeting_id):
        self.selected_meeting_id = meeting_id
        self.folder_picker.get_directory_path()

    def _on_folder_result(self, e):
        if not e.path or not self.selected_meeting_id:
            return

        success, message = self.controller.export_audio(self.selected_meeting_id, e.path)

        if self._page:
            self._page.snack_bar = ft.SnackBar(ft.Text(message))
            self._page.snack_bar.open = True
            self._page.update()

        self.selected_meeting_id = None

    def _confirm_delete(self, meeting_id, title):
        logger.info(f"Opening delete confirmation for ID: {meeting_id}")

        def close_dlg(e):
            self._page.close(confirm_dlg)

        def do_delete(e):
            self._page.close(confirm_dlg)
            if self.controller.delete_meeting(meeting_id):
                self._refresh_history()
                if self._page:
                    self._page.snack_bar = ft.SnackBar(ft.Text(f"「{title}」を削除しました"))
                    self._page.snack_bar.open = True
            else:
                if self._page:
                    self._page.snack_bar = ft.SnackBar(ft.Text("削除に失敗しました"), bgcolor=ft.Colors.RED_400)
                    self._page.snack_bar.open = True
            if self._page:
                self._page.update()

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("履歴の削除"),
            content=ft.Text(f"「{title}」を削除してもよろしいですか？\nこの操作は取り消せません。"),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dlg),
                ft.TextButton("削除する", icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=do_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if self._page:
            logger.info("Opening delete confirmation via page.open()")
            self._page.open(confirm_dlg)
            self._page.update()
        else:
            logger.error("Cannot show delete dialog: self._page is None")
