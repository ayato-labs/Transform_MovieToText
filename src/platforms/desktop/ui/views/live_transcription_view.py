import logging
import threading

import flet as ft

from src.common.ui.view_models.live_transcription_vm import LiveTranscriptionViewModel
from src.core.config_manager import ConfigManager
from src.core.constants import DEFAULT_PROVIDERS, WHISPER_MODELS
from src.core.history_mgr import history_mgr
from src.core.setup_manager import setup_manager
from src.core.state import state
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController
from src.platforms.desktop.controllers.transcription_ctrl import TranscriptionController
from src.platforms.desktop.ui.local_smart_helper import LocalSmartUIHelper
from src.platforms.desktop.ui.ui_utils import safe_update_control, sync_llm_models

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
        self.local_smart_ctrl = LocalSmartController(config_mgr)

        # Initialize ViewModel
        self.vm = LiveTranscriptionViewModel(config_mgr, ctrl)
        self._setup_vm_callbacks()

        # IMPORTANT: UI must be built before helper initialization so references exist
        self._build_ui()
        
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

        # Initial data load (Start AFTER helper is ready)
        threading.Thread(target=lambda: self.smart_helper.initial_load(self._update_model_options), daemon=True).start()

        self.refresh_dependency_state(initial=True)

    def refresh_dependency_state(self, initial=False):
        """Update UI based on background setup status."""
        is_ready = setup_manager.is_fully_ready
        is_recording = state.get("is_recording", False)

        if not is_ready:
            self.btn_live.disabled = True
            self.btn_live.text = "セットアップ中..."
            self.btn_live.icon = ft.Icons.DOWNLOAD_FOR_OFFLINE
            self.status_text.value = "⚠️ AI 文字起こしコンポーネントを準備中です..."
        elif not is_recording:
            self.btn_live.disabled = False
            self.btn_live.text = "録音開始"
            self.btn_live.icon = ft.Icons.MIC
            self.status_text.value = "機材準備完了..."

        if not initial:
            self._safe_update()

    def _setup_vm_callbacks(self):
        self.vm.on_status_changed = self._on_vm_status_changed
        self.vm.on_segment_added = self._on_vm_segment_added
        self.vm.on_transcription_finished = self._on_vm_transcription_finished
        self.vm.on_error = self._on_vm_error

    def _on_vm_status_changed(self, status: str):
        self.status_text.value = status
        self._safe_update()

    def _on_vm_segment_added(self, text: str):
        self.raw_transcript_text.value += text + " "
        self._safe_update()

    def _on_vm_transcription_finished(self, result: dict):
        if "transformed" in result:
            self.result_text.value = result["transformed"]
            self.tabs.selected_index = 1
            self.status_text.value = result.get("status", "✨ すべての処理が完了しました")
            self.status_text.color = ft.Colors.GREEN_400
            self._stop_ui_state()
            self._safe_update()
        else:
            full_text = result.get("text", "")
            meeting_id = result.get("meeting_id") or state.get("current_meeting_id")
            if full_text and len(full_text.strip()) >= 50:
                self.vm.trigger_ai_transformation(meeting_id, full_text, self.dd_provider.value, self.dd_llm.value)
            else:
                self.result_text.value = f"文字起こしデータが短すぎるため、AI変換はスキップされました。\n\n{full_text}"
                self.status_text.value = "⚠️ 文字起こし完了 (AI変換スキップ)"
                self._stop_ui_state()
                self._safe_update()

    def _on_vm_error(self, err: str):
        self.status_text.value = f"⚠️ エラー: {err}"
        self.status_text.color = ft.Colors.RED_400
        self._stop_ui_state()
        self._safe_update()

    def _safe_update(self):
        """Safely updates the control if it is attached to a page."""
        safe_update_control(self)

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
            value="ollama_local",
            on_change=self._on_provider_change,
            visible=False,
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

        # Local Smart Toggle
        self.local_smart_btn = ft.IconButton(
            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            selected_icon=ft.Icons.AUTO_AWESOME,
            on_click=self._toggle_local_smart,
            tooltip="Local Smart: Optimize models for my hardware",
            selected=self.config_mgr.get_local_smart_enabled(),
        )

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
                        margin=ft.margin.only(left=10),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    self.dd_provider,
                    self.dd_llm,
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

    def _toggle_local_smart(self, e):
        self.smart_helper.toggle_smart(update_callback=self._update_model_options)

    def _update_model_options(self, provider: str):
        sync_llm_models(self._page, self.config_mgr, provider, self.dd_llm, self.status_text, on_empty_results=self._handle_empty_models)

    def _create_whisper_option(self, model_name: str):
        return ft.dropdown.Option(key=model_name, text=model_name)

    # --- Config Sync ---
    def _on_whisper_change(self, e):
        self.config_mgr.set_whisper_model(self.dd_whisper.value)

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
        logger.info(f"LiveTranscriptionView: Toggle recording button clicked (Current: {'Recording' if is_recording else 'Idle'})")

        if not is_recording:
            # START
            self._start_ui_state()

            # Resolve project name
            if self.dd_project.value == "__new__":
                project_name = self.tf_new_project.value.strip() or "新規プロジェクト"
            else:
                project_name = self.dd_project.value or "その他"

            logger.info(f"LiveTranscriptionView: Starting recording for project: {project_name}")
            self.vm.start_recording(
                whisper_model=self.dd_whisper.value,
                source=self.dd_source.value,
                project_name=project_name,
                provider=self.dd_provider.value,
                llm_model=self.dd_llm.value,
            )
        else:
            # STOP
            logger.info("LiveTranscriptionView: Stopping recording.")
            self.vm.stop_recording()
            self._safe_update()

    def _on_transcription_finished(self, result):
        logger.info("LiveTranscriptionView: Transcription finished.")
        if "transformed" in result:
            # Case 2: AI Transformation is COMPLETE
            logger.info("LiveTranscriptionView: AI transformation complete.")
            self.result_text.value = result["transformed"]
            self.tabs.selected_index = 1
            self.status_text.value = result.get("status", "✨ すべての処理が完了しました")
            self.status_text.color = ft.Colors.GREEN_400
            self._stop_ui_state()
            self._safe_update()
        else:
            # Case 1: Raw Transcription is COMPLETE, start AI Transformation
            logger.info("LiveTranscriptionView: Raw transcription complete, starting AI transformation.")
            full_text = result.get("text", "")
            meeting_id = result.get("meeting_id") or state.get("current_meeting_id")

            if full_text and len(full_text.strip()) >= 50:
                self._run_ai_conversion(meeting_id, full_text)
            else:
                # Record too short for AI
                logger.info("LiveTranscriptionView: Transcription too short for AI conversion.")
                self.result_text.value = f"文字起こしデータが短すぎるため、AI変換はスキップされました。\n\n{full_text}"
                self.status_text.value = "⚠️ 文字起こし完了 (AI変換スキップ)"
                self._stop_ui_state()
                self._safe_update()

    def _run_ai_conversion(self, meeting_id, text):
        """Triggers the background AI transformation process."""
        provider = self.dd_provider.value
        llm_model = self.dd_llm.value

        self.status_text.value = "🧠 AI変換の準備中..."
        logger.info(f"LiveTranscriptionView: Running AI conversion (Provider: {provider}, Model: {llm_model})")
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
        self.local_smart_btn.disabled = True
        self.raw_transcript_text.value = ""
        self.tabs.selected_index = 0
        self._safe_update()

    def _on_provider_change(self, e):
        provider = self.dd_provider.value
        self.config_mgr.set_active_provider(provider)
        self._update_model_options(provider)

    def _on_llm_change(self, e):
        self.config_mgr.set_last_model(self.dd_llm.value)

    def _handle_empty_models(self, provider: str):
        """Callback when a provider returns no models."""
        logger.warning(f"LiveTranscriptionView: Provider {provider} returned no models. Hiding.")

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

    def _stop_ui_state(self):
        self.btn_live.disabled = False
        self.btn_stop.disabled = True
        self.dd_source.disabled = False
        self.dd_provider.disabled = False
        self.dd_whisper.disabled = False
        self.dd_project.disabled = False
        self.tf_new_project.disabled = False
        self.local_smart_btn.disabled = False

    def init_view(self):
        pass
