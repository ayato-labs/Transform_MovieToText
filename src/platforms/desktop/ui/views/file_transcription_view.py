import logging
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.constants import EDITION_RESTRICTIONS, WHISPER_MODELS
from src.core.event_bus import (
    EVENT_STATUS_UPDATE,
    EVENT_TRANSCRIPTION_ERROR,
    EVENT_TRANSCRIPTION_FINISHED,
    EVENT_TRANSCRIPTION_PROGRESS,
    event_bus,
)
from src.core.history_mgr import history_mgr
from src.core.intent_router import IntentRouter
from src.core.minutes_service import MinutesService
from src.core.setup_manager import setup_manager
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController
from src.platforms.desktop.controllers.transcription_ctrl import TranscriptionController
from src.platforms.desktop.ui.local_smart_helper import LocalSmartUIHelper
from src.platforms.desktop.ui.ui_utils import safe_update_control, sync_llm_models

logger = logging.getLogger(__name__)


class FileTranscriptionView(ft.Column):
    """
    View for transcribing existing video/audio files with Provider and Model selection.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager, ctrl: TranscriptionController, hw_info: dict):
        super().__init__(expand=True, scroll=ft.ScrollMode.ADAPTIVE, spacing=10)
        self._page = page
        self.config_mgr = config_mgr
        self.ctrl = ctrl
        self.hw_info = hw_info
        self.service = ctrl.service
        self.minutes_service = MinutesService(config_mgr)
        self.local_smart_ctrl = LocalSmartController(config_mgr)
        self.router = IntentRouter(config_mgr)

        self._setup_view_elements()
        self._setup_event_handlers()
        
        # Initialize Shared Helper
        self.smart_helper = LocalSmartUIHelper(
            config_mgr, 
            self.local_smart_ctrl, 
            self.dd_provider, 
            self.dd_llm, 
            self.status_text, 
            dd_whisper=self.dd_whisper, 
            local_smart_btn=self.local_smart_btn
        )

        # IMPORTANT: Start initial load thread AFTER helper is fully assigned to self
        threading.Thread(target=lambda: self.smart_helper.initial_load(self._update_model_options), daemon=True).start()

        self.refresh_dependency_state(initial=True)

    def _setup_view_elements(self):
        # File Pickers
        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._on_file_picked
        self.save_picker = ft.FilePicker()
        self.save_picker.on_result = self._on_save_picked
        if self._page:
            self._page.overlay.extend([self.file_picker, self.save_picker])

        self.dd_whisper = ft.Dropdown(
            label="Whisperモデル",
            width=180,
            options=[self._create_whisper_option(m) for m in WHISPER_MODELS],
            value=self.config_mgr.get_whisper_model(),
            on_change=self._on_whisper_change,
        )

        edition = self.config_mgr.get_edition()
        allowed_providers = EDITION_RESTRICTIONS.get(edition, {}).get("allowed_providers", [])

        self.dd_provider = ft.Dropdown(
            label="AIプロバイダー",
            width=180,
            options=[ft.dropdown.Option(p) for p in allowed_providers],
            value="ollama_local",
            on_change=self._on_provider_change,
            visible=False,
        )

        self.status_text = ft.Text("待機中...", color=ft.Colors.GREY_500)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=ft.Colors.BLUE_400, height=8)

        self.local_smart_btn = ft.IconButton(
            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            selected_icon=ft.Icons.AUTO_AWESOME,
            on_click=self._toggle_local_smart,
            tooltip="Local Smart: Optimize models for my hardware",
            selected=self.config_mgr.get_local_smart_enabled(),
        )

        self.dd_llm = ft.Dropdown(
            label="LLMモデル",
            width=220,
            options=[ft.dropdown.Option("取得中...", disabled=True)],
            value=None,
            on_change=self._on_llm_change,
        )

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

        self.sw_visual = ft.Switch(
            label="映像情報を使用", value=False, tooltip="動画ファイルから10秒ごとに画像を抽出してAIに送信します(分析精度が向上します)"
        )

        self.btn_pick = ft.ElevatedButton(
            "ファイルを選択して開始",
            icon=ft.Icons.UPLOAD_FILE,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=lambda _: self.file_picker.pick_files(allow_multiple=False),
        )

        self.result_text = ft.TextField(
            label="AI 変換結果",
            multiline=True,
            min_lines=20,
            max_lines=None,
            expand=True,
            text_size=14,
            border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.BLACK12,
        )
        self.raw_transcript_text = ft.TextField(
            label="文字起こし全文",
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
                ft.Tab(text="AI 変換結果", icon=ft.Icons.AUTO_AWESOME, content=self.result_text),
                ft.Tab(text="全文テキスト", icon=ft.Icons.LIST_ALT, content=self.raw_transcript_text),
            ],
        )

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("ファイル文字起こし", size=32, weight=ft.FontWeight.BOLD),
                            ft.Text("動画・音声ファイルをAIで解析し、要約や議事録を作成します", size=14, color=ft.Colors.GREY_400),
                        ]
                    ),
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self.update(), tooltip="表示を更新"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=20, color=ft.Colors.GREY_800),
            ft.Row(
                [
                    ft.Text("Smart Local Optimization:", weight=ft.FontWeight.BOLD),
                    self.dd_whisper,
                    self.local_smart_btn,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"RAM: {self.hw_info['ram']}GB", size=10, color=ft.Colors.BLUE_200),
                                ft.Text(f"VRAM: {self.hw_info['vram']}GB", size=10, color=ft.Colors.PURPLE_200),
                            ],
                            spacing=0,
                        ),
                        padding=ft.padding.only(left=10),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row([self.dd_provider, self.dd_llm, self.sw_visual], spacing=10),
            ft.Row([self.dd_project, self.tf_new_project], spacing=10),
            ft.Container(height=10),
            self.btn_pick,
            ft.Container(height=10),
            self.status_text,
            self.progress_bar,
            ft.Container(
                content=self.tabs,
                expand=True,
                height=500,
                padding=15,
                bgcolor=ft.Colors.BLACK26,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=15,
            ),
            ft.Row(
                [
                    ft.ElevatedButton("結果を保存", icon=ft.Icons.SAVE, on_click=lambda _: self.save_picker.save_file(file_name="result.md")),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ]

    def refresh_dependency_state(self, initial=False):
        """Update UI based on background setup status."""
        is_ready = setup_manager.is_fully_ready
        if not is_ready:
            self.btn_pick.disabled = True
            self.btn_pick.text = "自動セットアップ中..."
            self.btn_pick.icon = ft.Icons.DOWNLOAD_FOR_OFFLINE
            self.status_text.value = "⚠️ AI 文字起こしコンポーネントを準備中です..."
        else:
            self.btn_pick.disabled = False
            self.btn_pick.text = "ファイルを選択して開始"
            self.btn_pick.icon = ft.Icons.UPLOAD_FILE
            self.status_text.value = "待機中..."

        if not initial:
            self._safe_update()

    def _setup_event_handlers(self):
        @event_bus.subscribe(EVENT_STATUS_UPDATE)
        def on_status(status):
            self.status_text.value = status
            self._safe_update()

        @event_bus.subscribe(EVENT_TRANSCRIPTION_PROGRESS)
        def on_progress(p):
            self.progress_bar.visible = True
            self.progress_bar.value = p
            self._safe_update()

        @event_bus.subscribe(EVENT_TRANSCRIPTION_FINISHED)
        def on_finished(result):
            self.raw_transcript_text.value = result.get("text", "")
            self.progress_bar.visible = False
            self.btn_pick.disabled = False
            meeting_id = result.get("meeting_id")
            self._run_ai_conversion(result.get("text", ""), meeting_id=meeting_id)
            self._safe_update()

        @event_bus.subscribe(EVENT_TRANSCRIPTION_ERROR)
        def on_error(err):
            self.status_text.value = f"エラー: {err}"
            self.status_text.color = ft.Colors.RED_400
            self.progress_bar.visible = False
            self.btn_pick.disabled = False
            self._safe_update()

    def _create_whisper_option(self, model_name: str):
        return ft.dropdown.Option(key=model_name, text=model_name)

    def _on_whisper_change(self, e):
        self.config_mgr.set_whisper_model(self.dd_whisper.value)

    def _safe_update(self):
        """Safely updates the control if it is attached to a page."""
        safe_update_control(self)

    def _on_provider_change(self, e):
        provider = self.dd_provider.value
        self.config_mgr.set_active_provider(provider)
        self._update_model_options(provider)

    def _handle_empty_models(self, provider: str):
        """Callback when a provider returns no models."""
        logger.warning(f"Provider {provider} returned no models. Hiding from UI.")

        # Remove from dropdown options
        new_options = [opt for opt in self.dd_provider.options if opt.key != provider]
        self.dd_provider.options = new_options

        # If currently selected, fallback to something else
        if self.dd_provider.value == provider:
            if new_options:
                fallback = new_options[0].key
                self.dd_provider.value = fallback
                self.config_mgr.set_active_provider(fallback)
                self._update_model_options(fallback)
            else:
                self.dd_provider.value = None

        self._safe_update()

    def _update_model_options(self, provider: str):
        sync_llm_models(self.page, self.config_mgr, provider, self.dd_llm, on_empty_results=self._handle_empty_models)

    def _on_llm_change(self, e):
        self.config_mgr.set_last_model(self.dd_llm.value)

    def _on_file_picked(self, e):
        if not e.files:
            return
        file_path = e.files[0].path
        self.btn_pick.disabled = True
        self.ctrl.start_file_transcription(file_path, self.dd_whisper.value)

    def _run_ai_conversion(self, text: str, meeting_id: int | None = None):
        if not text or len(text.strip()) < 10:
            return

        self.status_text.value = "🧠 AI 変換処理を開始します..."
        self._safe_update()

        threading.Thread(target=self._ai_worker, args=(text, meeting_id), daemon=True).start()

    def _ai_worker(self, text: str, meeting_id: int | None = None):
        try:
            provider = self.dd_provider.value
            llm_model = self.dd_llm.value

            # Use MinutesService via controller to leverage Map-Reduce
            ai_output = self.ctrl.minutes_service.generate_minutes_sync(
                transcript=text, provider=provider, model=llm_model, meeting_id=meeting_id
            )

            self.result_text.value = ai_output
            self.tabs.selected_index = 0
            self.status_text.value = "処理完了"
            self._safe_update()
        except Exception as e:
            logger.error(f"AI conversion error: {e}")
            self.status_text.value = f"AI変換エラー: {e}"
            self._safe_update()

    def _toggle_local_smart(self, e):
        self.smart_helper.toggle_smart(update_callback=self._update_model_options)

    def _on_project_change(self, e):
        is_new = self.dd_project.value == "__new__"
        self.tf_new_project.visible = is_new
        self.update()

    def _on_save_picked(self, e):
        if not e.path:
            return
        with open(e.path, "w", encoding="utf-8") as f:
            f.write(self.result_text.value)

    def _update_progress(self, val):
        self.progress_bar.value = val
        self._safe_update()
