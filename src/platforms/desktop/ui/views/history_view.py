import logging

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.constants import DEFAULT_LLM_MODELS, DEFAULT_PROVIDERS
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber
from src.platforms.desktop.controllers.history_ctrl import HistoryController
from src.platforms.common.ui.ui_utils import Debouncer
from src.platforms.desktop.ui.ui_utils import sync_llm_models

logger = logging.getLogger(__name__)


class HistoryView(ft.Column):
    def __init__(self, controller: HistoryController, config_mgr: ConfigManager, folder_picker: ft.FilePicker, page: ft.Page = None):
        super().__init__(expand=True, scroll="auto")
        self._page = page
        self.controller = controller
        self.config_mgr = config_mgr
        self.folder_picker = folder_picker
        self.selected_meeting_id = None
        self.audio_player = None
        
        # Search debouncer to avoid flooding DB during typing
        self.search_debouncer = Debouncer(delay=0.3)

        self.folder_picker.on_result = self._on_folder_result

        self.history_list = ft.ListView(expand=True, spacing=10, padding=10)

        self.search_field = ft.TextField(
            label="キーワード検索 (FTS5)",
            hint_text="プロジェクト名、内容、キーワードで検索...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_submit=lambda _: self._refresh_history(),
            on_change=self._on_search_change,
        )

        self.project_dropdown = ft.Dropdown(label="プロジェクトで絞り込み", width=250, on_change=lambda _: self._on_project_filter_change())
        self.clear_filter_btn = ft.IconButton(
            icon=ft.Icons.FILTER_LIST_OFF,
            tooltip="絞り込みを解除",
            on_click=lambda _: self._clear_filters(),
            visible=False,  # Initially hidden
        )

        # ROI Dashboard Banner
        self.roi_banner = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("節約された合計時間", size=12, color=ft.Colors.BLUE_200),
                            ft.Text("0.0時間", size=22, weight="bold", key="time_saved"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                    ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                    ft.Column(
                        [
                            ft.Text("削減コスト (SaaS換算)", size=12, color=ft.Colors.GREEN_200),
                            ft.Text("¥0", size=22, weight="bold", key="cost_saved"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
            padding=20,
            bgcolor=ft.Colors.BLACK26,
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            margin=ft.margin.only(bottom=10),
        )

        self.controls = [
            ft.Text("会議履歴 ＆ ROIダッシュボード", size=24, weight="bold"),
            ft.Text("過去の資産を活用し、どれだけの時間とコストが削減されたかを確認できます。"),
            self.roi_banner,
            ft.Row([self.search_field, ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._refresh_history())]),
            ft.Row([self.project_dropdown, self.clear_filter_btn]),
            ft.Divider(),
            self.history_list,
        ]

    def init_view(self):
        self._update_projects_list()
        self._refresh_history()

    def _update_projects_list(self):
        projects = self.controller.get_projects()
        current_val = self.project_dropdown.value

        # Don't add 'All Projects' anymore. We use a clear button instead.
        self.project_dropdown.options = [ft.dropdown.Option(p) for p in projects]

        # Keep selection if it still exists
        if current_val in projects:
            self.project_dropdown.value = current_val
        else:
            self.project_dropdown.value = None

        if self._page:
            self.update()

    def _refresh_history(self):
        self.history_list.controls.clear()

        # Update ROI Metrics
        metrics = self.controller.get_roi_metrics()
        # The Flet elements within the container are columns, we need to access the text controls
        # Finding them by key is easier if we store references or use the control's key/index.
        # Inside the Row under Column 0 and 1.
        self.roi_banner.content.controls[0].controls[1].value = f"{metrics['time_saved_hours']}時間"
        self.roi_banner.content.controls[2].controls[1].value = f"¥{metrics['cost_avoided_jpy']:,}"

        # Get both filters
        search_query = self.search_field.value.strip() if self.search_field.value else None
        project_filter = self.project_dropdown.value

        # Toggle clear filter button visibility
        self.clear_filter_btn.visible = bool(project_filter)

        logger.info(f"Refreshing history with project='{project_filter}' and query='{search_query}'")

        # Use single gateway for filtered data
        meetings = self.controller.get_filtered_meetings(project_name=project_filter, search_query=search_query)

        if not meetings:
            self.history_list.controls.append(ft.Text("履歴がありません。", italic=True, color="grey500"))
        else:
            for m in meetings:
                self.history_list.controls.append(self._build_meeting_card(m))

        if self._page:
            self.update()
            self._page.update()

    def _on_search_change(self, e):
        self.search_debouncer.run(self._refresh_history)

    def _on_project_filter_change(self):
        self._refresh_history()

    def _clear_filters(self):
        self.project_dropdown.value = None
        self.clear_filter_btn.visible = False
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

        # Setup audio player
        if self.audio_player in self._page.overlay:
            self._page.overlay.remove(self.audio_player)

        audio_path = m.get("audio_path")
        if audio_path and os.path.exists(audio_path):
            self.audio_player = ft.Audio(src=audio_path, autoplay=False, volume=1.0)
            self._page.overlay.append(self.audio_player)
        else:
            self.audio_player = None

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

        # Metadata Edit Controls
        tf_title = ft.TextField(label="タイトル", value=m["title"], expand=True)
        tf_project = ft.TextField(label="プロジェクト", value=m["project_name"] or "その他", width=200)

        def on_save_metadata(e):
            new_title = tf_title.value.strip()
            new_project = tf_project.value.strip()
            if self.controller.update_meeting(m["id"], title=new_title, project_name=new_project):
                self._page.snack_bar = ft.SnackBar(ft.Text("保存しました"))
                self._page.snack_bar.open = True
                self._update_projects_list()
                self._refresh_history()
                self._page.update()
            else:
                self._page.snack_bar = ft.SnackBar(ft.Text("保存に失敗しました"), bgcolor=ft.Colors.RED_400)
                self._page.snack_bar.open = True
                self._page.update()

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
            if self.audio_player:
                self.audio_player.pause()
            if self._page.dialog:
                self._page.dialog.open = False
            self._page.update()

        # Build Interactive Transcript if available
        interactive_content = None
        segments = m.get("transcript_segments")
        if segments and self.audio_player:
            interactive_content = self._build_interactive_transcript(segments, v_contexts)

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.EDIT_DOCUMENT),
                    tf_title,
                    ft.IconButton(ft.Icons.SAVE, on_click=on_save_metadata, tooltip="メタデータを保存", icon_color="blue400"),
                    ft.IconButton(ft.Icons.CLOSE, on_click=close_details),
                ],
                alignment="spaceBetween",
                spacing=10,
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
                                ft.Tab(
                                    text="インタラクティブ再生",
                                    icon=ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
                                    content=interactive_content
                                    if interactive_content
                                    else ft.Text("このデータにはタイムライン情報がありません。", color="grey500"),
                                ),
                            ],
                            expand=True,
                        ),
                        ft.Divider(),
                        ft.Row(
                            [
                                ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN, size=16), tf_project], vertical_alignment="center", spacing=5),
                                ft.Text(f"📅 日時: {m['timestamp']}", size=12, color="grey400"),
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

    def _build_interactive_transcript(self, segments, visual_contexts):
        """Constructs a clickable transcript linked to audio player and visual context."""
        transcript_container = ft.Column(expand=True, scroll="auto", spacing=5)

        # Player Controls at the top
        play_btn = ft.IconButton(ft.Icons.PLAY_ARROW, on_click=lambda _: self.audio_player.play() if self.audio_player else None)
        pause_btn = ft.IconButton(ft.Icons.PAUSE, on_click=lambda _: self.audio_player.pause() if self.audio_player else None)

        transcript_container.controls.append(
            ft.Row([play_btn, pause_btn, ft.Text("テキストをクリックするとその時点から再生します", size=12, italic=True)], alignment="center")
        )

        for seg in segments:
            start_ms = int(seg["start"] * 1000)
            text = seg["text"]

            def on_seg_click(e, ms=start_ms):
                if self.audio_player:
                    self.audio_player.seek(ms)
                    self.audio_player.play()
                    self._page.update()

            transcript_container.controls.append(
                ft.Container(
                    content=ft.Text(f"[{seg['start']:.1f}s] {text}", size=14),
                    on_click=on_seg_click,
                    padding=5,
                    border_radius=5,
                    ink=True,
                )
            )

        return ft.Container(content=transcript_container, padding=10, expand=True)

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
