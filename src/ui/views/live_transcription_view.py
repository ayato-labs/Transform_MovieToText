import logging

import flet as ft

from src.controllers.transcription_ctrl import TranscriptionController
from src.core.config_manager import ConfigManager
from src.core.constants import DEFAULT_PROVIDERS, WHISPER_MODELS
from src.core.event_bus import EVENT_STATUS_UPDATE, EVENT_TRANSCRIPTION_ERROR, EVENT_TRANSCRIPTION_FINISHED, EVENT_TRANSCRIPTION_SEGMENT, event_bus
from src.core.history_mgr import history_mgr
from src.core.intent_router import IntentRouter
from src.core.state import state
from src.ui.ui_utils import sync_llm_models

logger = logging.getLogger(__name__)


class LiveTranscriptionView(ft.Column):
    """
    View for real-time transcription with Provider and Model selection.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager, ctrl: TranscriptionController, hw_info: dict):
        super().__init__(expand=True, scroll=ft.ScrollMode.ADAPTIVE, spacing=10)
        self._page = page
        self.config_mgr = config_mgr
        self.ctrl = ctrl
        self.hw_info = hw_info
        self.service = ctrl.service
        self.router = IntentRouter(config_mgr)
        self._setup_event_handlers()
        self._build_ui()

    def _setup_event_handlers(self):
        @event_bus.subscribe(EVENT_STATUS_UPDATE)
        def on_status(status):
            self.status_text.value = status
            self._safe_update()

        @event_bus.subscribe(EVENT_TRANSCRIPTION_SEGMENT)
        def on_segment(segment_data):
            # segment_data usually has 'text', 'start', 'end'
            text = segment_data.get("text", "")
            self.raw_transcript_text.value += text + " "
            self._safe_update()

        @event_bus.subscribe(EVENT_TRANSCRIPTION_FINISHED)
        def on_finished(result):
            self._on_transcription_finished(result)

        @event_bus.subscribe(EVENT_TRANSCRIPTION_ERROR)
        def on_error(err):
            self.status_text.value = f"⚠️ エラー: {err}"
            self.status_text.color = ft.Colors.RED_400
            self._stop_ui_state()
            self._safe_update()

    def _safe_update(self):
        if self._page:
            self.update()

    def _build_ui(self):
        # --- Top Selection Area ---
        self.dd_whisper = ft.Dropdown(
            label="Whisperモデル",
            width=180,
            options=[self._create_whisper_option(m) for m in WHISPER_MODELS],
            value=self.config_mgr.get_whisper_model(),
            on_change=self._on_whisper_change,
        )

        provider_options = [ft.dropdown.Option(k) for k in DEFAULT_PROVIDERS]
        self.dd_provider = ft.Dropdown(
            label="AIプロバイダー",
            width=180,
            options=provider_options,
            value=self.config_mgr.get_active_provider(),
            on_change=self._on_provider_change,
        )

        self.sw_visual = ft.Switch(label="画面録画中", value=self.config_mgr.get_visual_capture_enabled(), on_change=self._on_visual_change)

        self.dd_source = ft.Dropdown(
            label="録音ソース",
            width=200,
            options=[
                ft.dropdown.Option("system", "システム音 (録画推奨)"),
                ft.dropdown.Option("microphone", "マイク入力"),
            ],
            value=self.config_mgr.get_audio_source() or "system",
            on_change=self._on_source_change,
        )

        self.status_text = ft.Text("機材準備完了...", color=ft.Colors.GREEN_400)

        # --- Project Selection ---
        existing_projects = history_mgr.get_projects()
        project_options = [
            ft.dropdown.Option("その他", "その他 (デフォルト)"),
            ft.dropdown.Option("__new__", "＋新規プロジェクト作成"),
        ]
        project_options.extend([ft.dropdown.Option(p) for p in existing_projects if p != "その他"])

        self.dd_project = ft.Dropdown(
            label="プロジェクト選択",
            width=200,
            options=project_options,
            value="その他",
            on_change=self._on_project_change,
        )
        self.tf_new_project = ft.TextField(
            label="新規プロジェクト名",
            width=200,
            hint_text="プロジェクト名を入力...",
            visible=False,
        )

        # Action Buttons
        self.btn_live = ft.ElevatedButton("録音開始", icon=ft.Icons.MIC, color=ft.Colors.RED_400, on_click=self._on_toggle_recording)
        self.btn_stop = ft.ElevatedButton("録音停止", icon=ft.Icons.STOP, color=ft.Colors.GREY_400, disabled=True, on_click=self._on_toggle_recording)

        self.dd_llm = ft.Dropdown(
            label="LLMモデル",
            width=220,
            options=[],  # Filled dynamically
            on_change=self._on_llm_change,
        )
        sync_llm_models(self._page, self.config_mgr, self.dd_provider.value, self.dd_llm, self.status_text)

        # Text Areas Container
        self.result_text = ft.TextField(
            label="AI 解析・議事録プレビュー",
            multiline=True,
            min_lines=20,
            max_lines=None,
            expand=True,
            text_size=14,
            border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.BLACK12,
        )
        self.raw_transcript_text = ft.TextField(
            label="生文字起こしログ (リアルタイム更新)",
            multiline=True,
            min_lines=20,
            max_lines=None,
            expand=True,
            text_size=12,
            border_color=ft.Colors.GREY_700,
            bgcolor=ft.Colors.BLACK12,
        )

        self.tabs = ft.Tabs(
            selected_index=0,
            expand=True,
            tabs=[
                ft.Tab(text="ライブ・ログ", icon=ft.Icons.LIST_ALT, content=self.raw_transcript_text),
                ft.Tab(text="AI 変換結果 (停止後に生成)", icon=ft.Icons.AUTO_AWESOME, content=self.result_text),
            ],
        )

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("リアルタイム録音 & 文字起こし", size=32, weight=ft.FontWeight.BOLD),
                            ft.Text("会議や動画の音声をリアルタイムで解析し、終了時に議事録を生成します", size=14, color=ft.Colors.GREY_400),
                        ]
                    ),
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self.update(), tooltip="表示を更新"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=20, color=ft.Colors.GREY_800),
            ft.Row(
                [
                    self.dd_whisper,
                    self.dd_provider,
                    self.dd_llm,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"RAM: {self.hw_info['ram']}GB", size=10, color=ft.Colors.BLUE_200),
                                ft.Text(f"VRAM: {self.hw_info['vram']}GB", size=10, color=ft.Colors.PURPLE_200),
                            ],
                            spacing=0,
                        ),
                        margin=ft.margin.only(left=10),
                    ),
                ],
                spacing=10,
            ),
            ft.Row(
                [
                    self.dd_source,
                    self.sw_visual,
                    ft.VerticalDivider(width=10, color=ft.Colors.TRANSPARENT),
                    self.dd_project,
                    self.tf_new_project,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            ),
            ft.Row(
                [
                    self.btn_live,
                    self.btn_stop,
                ],
                spacing=15,
            ),
            ft.Container(height=5),
            self.status_text,
            ft.Container(
                content=self.tabs,
                expand=True,
                height=500,
                padding=15,
                bgcolor=ft.Colors.BLACK26,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=15,
            ),
        ]

    def _create_whisper_option(self, model_name: str):
        return ft.dropdown.Option(key=model_name, text=model_name)

    # --- Config Sync ---
    def _on_whisper_change(self, e):
        self.config_mgr.set_whisper_model(self.dd_whisper.value)

    def _on_provider_change(self, e):
        self.config_mgr.set_active_provider(self.dd_provider.value)
        sync_llm_models(self._page, self.config_mgr, self.dd_provider.value, self.dd_llm, self.status_text)
        self.update()

    def _on_llm_change(self, e):
        self.config_mgr.set_last_model(self.dd_llm.value)

    def _on_visual_change(self, e):
        self.config_mgr.set_visual_capture_enabled(self.sw_visual.value)

    def _on_source_change(self, e):
        self.config_mgr.set_audio_source(self.dd_source.value)

    def _on_project_change(self, e):
        # Show/Hide new project text field based on selection
        is_new = self.dd_project.value == "__new__"
        self.tf_new_project.visible = is_new
        self.update()

    # --- Action Handlers ---
    def _on_toggle_recording(self, _):
        is_recording = state.get("is_recording", False)

        if not is_recording:
            # START
            self._start_ui_state()

            # Resolve project name
            if self.dd_project.value == "__new__":
                project_name = self.tf_new_project.value.strip() or "新規プロジェクト"
            else:
                project_name = self.dd_project.value or "その他"

            try:
                self.ctrl.start_live_transcription(model_name=self.dd_whisper.value, source=self.dd_source.value, project_name=project_name)
            except Exception as ex:
                logger.error(f"Live transcription failed to start: {ex}", exc_info=True)
                self.status_text.value = f"⚠️ 起動失敗: {ex}"
                self.status_text.color = ft.Colors.RED_400
                self._stop_ui_state()
                self._safe_update()
        else:
            # STOP
            self.ctrl.stop_live_transcription()
            self._safe_update()

    def _on_transcription_finished(self, result):
        if "transformed" in result:
            # Case 2: AI Transformation is COMPLETE
            self.result_text.value = result["transformed"]
            self.tabs.selected_index = 1
            self.status_text.value = result.get("status", "✨ すべての処理が完了しました")
            self.status_text.color = ft.Colors.GREEN_400
            self._stop_ui_state()
            self._safe_update()
        else:
            # Case 1: Raw Transcription is COMPLETE, start AI Transformation
            full_text = result.get("text", "")
            meeting_id = result.get("meeting_id") or state.get("current_meeting_id")

            if full_text and len(full_text.strip()) >= 50:
                self._run_ai_conversion(meeting_id, full_text)
            else:
                # Record too short for AI
                self.result_text.value = f"文字起こしデータが短すぎるため、AI変換はスキップされました。\n\n{full_text}"
                self.status_text.value = "⚠️ 文字起こし完了 (AI変換スキップ)"
                self._stop_ui_state()
                self._safe_update()

    def _run_ai_conversion(self, meeting_id, text):
        """Triggers the background AI transformation process."""
        provider = self.dd_provider.value
        llm_model = self.dd_llm.value

        self.status_text.value = "🧠 AI変換の準備中..."
        self._safe_update()

        # Controller handles the strategy detection and LLM execution in a thread
        self.ctrl.transform_transcript(meeting_id=meeting_id, transcript=text, provider=provider, model=llm_model)

    def _start_ui_state(self):
        self.btn_live.disabled = True
        self.btn_stop.disabled = False
        self.dd_source.disabled = True
        self.dd_provider.disabled = True
        self.dd_whisper.disabled = True
        self.dd_project.disabled = True
        self.tf_new_project.disabled = True
        self.raw_transcript_text.value = ""
        self.tabs.selected_index = 0
        self._safe_update()

    def _stop_ui_state(self):
        self.btn_live.disabled = False
        self.btn_stop.disabled = True
        self.dd_source.disabled = False
        self.dd_provider.disabled = False
        self.dd_whisper.disabled = False
        self.dd_project.disabled = False
        self.tf_new_project.disabled = False

    def init_view(self):
        pass
