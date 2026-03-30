import logging
import os
import threading

import flet as ft

from src.controllers.local_smart_ctrl import LocalSmartController
from src.core.config_manager import ConfigManager
from src.core.intent_router import IntentRouter
from src.core.minutes_service import MinutesService
from src.core.state import state
from src.core.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


class TranscriptionView(ft.Column):
    """
    Main View for Transcription and Transformation.
    Restored and modernized with Tabs, Progress, and Live Recording support.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager, service: TranscriptionService):
        super().__init__(expand=True, scroll=ft.ScrollMode.ADAPTIVE, spacing=10)
        self._page = page
        self.config_mgr = config_mgr
        self.service = service
        self.minutes_service = MinutesService(config_mgr)
        self.local_smart_ctrl = LocalSmartController(config_mgr)
        self.router = IntentRouter(config_mgr)
        self.hw_info = service.transcriber.get_hardware_info()
        self.local_smart_enabled = self.config_mgr.get_local_smart_enabled()

        # File Pickers
        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._on_file_picked
        self.save_picker = ft.FilePicker()
        self.save_picker.on_result = self._on_save_picked
        if self._page:
            self._page.overlay.extend([self.file_picker, self.save_picker])

        # Status & Progress
        self.status_text = ft.Text("待機中...", color=ft.Colors.GREY_500)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=ft.Colors.BLUE_400, height=8)

        # Action Buttons
        self.btn_pick = ft.ElevatedButton(
            "ファイルを選択",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=lambda _: self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["mp4", "mkv", "mp3", "wav", "m4a"]),
        )
        self.btn_live = ft.ElevatedButton("録音開始 (Live)", icon=ft.Icons.MIC, color=ft.Colors.RED_400, on_click=self._on_live_recording_toggle)
        self.btn_stop = ft.ElevatedButton(
            "録音停止", icon=ft.Icons.STOP, color=ft.Colors.GREY_400, disabled=True, on_click=self._on_live_recording_toggle
        )

        # Text Areas Container
        self.result_text = ft.TextField(
            label="AI 変換結果 (要約・アクションアイテム等)",
            multiline=True,
            min_lines=20,
            max_lines=None,
            read_only=False,
            expand=True,
            text_size=14,
            border_color=ft.Colors.BLUE_700,
            hint_text="ここにAIによる変換結果が表示されます...",
            bgcolor=ft.Colors.BLACK12,
        )
        self.raw_transcript_text = ft.TextField(
            label="文字起こし全文",
            multiline=True,
            min_lines=20,
            max_lines=None,
            read_only=True,
            expand=True,
            text_size=12,
            border_color=ft.Colors.GREY_700,
            hint_text="ここに生文字起こしのテキストが表示されます...",
            bgcolor=ft.Colors.BLACK12,
        )

        # Tabs for result navigation
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(text="AI 変換結果", icon=ft.Icons.AUTO_AWESOME, content=self.result_text),
                ft.Tab(text="文字起こし全文", icon=ft.Icons.LIST_ALT, content=self.raw_transcript_text),
            ],
        )

        # Model Selection Row with Local Smart Button
        self.dd_whisper = ft.Dropdown(
            label="Whisperモデル",
            width=180,
            options=[ft.dropdown.Option(m) for m in ["tiny", "base", "small", "medium", "large-v3"]],
            value=self.config_mgr.get_last_model(),
        )
        self.dd_provider = ft.Dropdown(
            label="AIプロバイダー",
            width=180,
            options=[ft.dropdown.Option(p) for p in ["ollama_local", "ollama_cloud", "google"]],
            value=self.config_mgr.get_active_provider(),
            on_change=self._on_provider_change,
        )
        self.dd_llm = ft.Dropdown(
            label="LLMモデル",
            width=200,
            options=[ft.dropdown.Option("取得中...", disabled=True)],
            value=None,
        )
        self.local_smart_btn = ft.IconButton(
            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            selected_icon=ft.Icons.AUTO_AWESOME,
            selected=self.local_smart_enabled,
            tooltip="Local Smart: ハードウェアに最適な設定を自動適用",
            on_click=self._toggle_local_smart,
        )

        # Initial background load
        threading.Thread(target=self._initial_load, daemon=True).start()

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("リアルタイム録音 & 文字起こし", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text("会議や動画の音声をリアルタイムで解析し、終了時に議事録を生成します", size=13, color=ft.Colors.GREY_400),
                        ]
                    ),
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._refresh_ui(), tooltip="表示を更新"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=20, color=ft.Colors.GREY_800),
            ft.Row(
                [
                    self.dd_whisper,
                    self.dd_provider,
                    self.dd_llm,
                    self.local_smart_btn,
                ],
                spacing=10,
            ),
            ft.Row([self.btn_pick, self.btn_live, self.btn_stop], spacing=15),
            ft.Container(height=10),
            self.status_text,
            self.progress_bar,
            ft.Container(height=10),
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
                    ft.ElevatedButton(
                        "結果を保存 (.md)",
                        icon=ft.Icons.SAVE_ALT,
                        bgcolor=ft.Colors.BLUE_800,
                        color=ft.Colors.WHITE,
                        on_click=lambda _: self.save_picker.save_file(file_name="transcription_result.md"),
                    ),
                    ft.Text("※ AI変換結果がMarkdown形式で保存されます", size=12, color=ft.Colors.GREY_500),
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=10,
            ),
        ]

    # --- Event Handlers ---

    def _on_file_picked(self, e):
        if not e.files:
            return
        file_path = e.files[0].path
        model = self.config_mgr.get_last_model()
        threading.Thread(target=self._run_transcription_flow, args=(file_path, model), daemon=True).start()

    def _on_live_recording_toggle(self, _):
        is_recording = state.get("is_recording", False)
        model = self.config_mgr.get_last_model()

        if not is_recording:
            # Transition to START
            self._set_recording_ui_state(True)
            self.status_text.value = "録音準備中..."
            state.set("is_recording", True)  # Set flag IMMEDIATELY to enable Stop button logic
            self.update()

            def on_chunk(text):
                # Update text in real-time
                self.raw_transcript_text.value += text + " "
                self._safe_update()

            def _start_worker():
                try:
                    # Offload to background thread so UI doesn't freeze
                    result = self.service.start_live_recording(model_name=model, source="system", on_text_added=on_chunk)

                    # result == -1 means stop was requested during model loading
                    if result == -1:
                        logger.info("Recording was cancelled during model load. Resetting UI.")
                        state.set("is_recording", False)
                        self._set_recording_ui_state(False)
                        self.status_text.value = "録音をキャンセルしました（停止ボタンが押されました）"
                        self._safe_update()
                        return

                    self.status_text.value = "🎙 システム音をリアルタイム録音・文字起こし中..."
                    self._safe_update()
                except Exception as ex:
                    logger.error(f"Live recording start failed: {ex}")
                    self.status_text.value = f"⚠️ 録音開始エラー: {ex}"
                    state.set("is_recording", False)
                    self._set_recording_ui_state(False)
                    self._safe_update()

            threading.Thread(target=_start_worker, daemon=True).start()
        else:
            # Transition to STOP
            self.status_text.value = "停止指示を受け付けました。最終処理中... (3秒程度)"
            self.btn_stop.disabled = True  # Prevent double clicks
            self.update()

            # Request stop from service (which now flushes buff immediately)
            self.service.stop_live_recording(finalize_callback=self._on_live_finalized)

    def _on_live_finalized(self, full_text, category):
        state.set("is_recording", False)
        self._set_recording_ui_state(False)
        self.raw_transcript_text.value = full_text
        self.status_text.value = f"ライブ文字起こし完了 (自動分類: {category if category else '未分類'})"

        # Memory Relay: Always unload after live session to ensure LLM has resources
        logger.info("TranscriptionView: Live session ended. Unloading Whisper for memory efficiency...")
        self.service.transcriber.unload_model()

        self._run_ai_conversion(full_text)
        self.update()

    def _set_recording_ui_state(self, active: bool):
        self.btn_live.disabled = active
        self.btn_stop.disabled = not active
        self.btn_pick.disabled = active
        if active:
            self.btn_live.icon = ft.Icons.REC__RECORDING
        else:
            self.btn_live.icon = ft.Icons.MIC

    def _run_transcription_flow(self, file_path: str, model: str):
        try:
            self.status_text.value = f"📂 ファイル読み込み中: {os.path.basename(file_path)}"
            self.progress_bar.visible = True
            self.progress_bar.value = 0
            self.update()

            text = self.service.transcribe_file_sync(file_path=file_path, model_name=model, progress_callback=self._update_progress)

            self.raw_transcript_text.value = text
            self.status_text.value = "✅ 文字起こし完了。AIによる変換処理を開始します..."
            self.progress_bar.visible = False
            self.update()

            self._run_ai_conversion(text)
        except Exception as ex:
            logger.error(f"Transcription flow error: {ex}", exc_info=True)
            self.status_text.value = f"⚠️ エラーが発生しました: {str(ex)}"
            self.progress_bar.visible = False
            self.update()

    def _run_ai_conversion(self, text: str):
        if not text or len(text.strip()) < 10:
            self.status_text.value = "⚠️ 有効なテキストが検出されませんでした。"
            self.update()
            return

        self.status_text.value = "🧠 AI 思考中 (意図の解析と変換戦略の実行)..."
        self.update()

        provider = self.config_mgr.get_active_provider()
        model_config = self.config_mgr.get_provider_config(provider).get("model", "gemini-1.5-flash")

        # Determine intent and select strategy
        routing = self.router.route(text, provider, model_config)

        # Execute routing results (placeholder logic for now, in production this calls LLM)
        ai_result = f"# AI 変換レポート ({routing['strategy'].name})\n\n"
        ai_result += f"**信頼度:** {routing['confidence']:.1%}\n"
        ai_result += f"**検出された意図:** {routing['intent']}\n\n"
        ai_result += "--- \n\n"
        ai_result += text  # In real impl, this would be the LLM's summarized output

        self.result_text.value = ai_result
        self.tabs.selected_index = 0
        self.status_text.value = "✨ すべての処理が完了しました。"
        self.update()

    def _on_save_picked(self, e):
        if not e.path:
            return
        try:
            with open(e.path, "w", encoding="utf-8") as f:
                f.write(self.result_text.value)
            logger.info(f"Report saved to {e.path}")
        except Exception as ex:
            logger.error(f"Save operation failed: {ex}")

    def _update_progress(self, val: float):
        self.progress_bar.value = val
        self.update()

    def _safe_update(self):
        if self.page:
            self.update()

    def _initial_load(self):
        if self.local_smart_enabled:
            self._apply_local_smart()
        else:
            provider = self.config_mgr.get_active_provider()
            self._update_model_options(provider)
        self._safe_update()

    def _on_provider_change(self, e):
        provider = self.dd_provider.value
        self.config_mgr.set_active_provider(provider)
        threading.Thread(target=self._update_model_options, args=(provider,), daemon=True).start()

    def _update_model_options(self, provider: str):
        # Map "google" to "gemini" for backend service
        actual_provider = "gemini" if provider == "google" else provider

        self.dd_llm.options = [ft.dropdown.Option("取得中...", disabled=True)]
        self.dd_llm.value = None
        self._safe_update()

        models = self.minutes_service.get_available_models(actual_provider)
        config = self.config_mgr.get_provider_config(provider)
        last_model = config.get("model")

        if models:
            self.dd_llm.options = [ft.dropdown.Option(m) for m in models]
            if last_model in models:
                self.dd_llm.value = last_model
            else:
                self.dd_llm.value = models[0]
        else:
            self.dd_llm.options = [ft.dropdown.Option("モデルなし", disabled=True)]
            self.dd_llm.value = None
        self._safe_update()

    def _apply_local_smart(self):
        self.local_smart_ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text, dd_whisper=self.dd_whisper)
        self._safe_update()

    def _toggle_local_smart(self, e):
        self.local_smart_enabled = not self.local_smart_enabled
        self.local_smart_btn.selected = self.local_smart_enabled
        self.config_mgr.set_local_smart_enabled(self.local_smart_enabled)

        if self.local_smart_enabled:
            self._apply_local_smart()
        else:
            self.local_smart_ctrl.restore_manual_mode(
                self.dd_provider, self.dd_llm, self.status_text, dd_whisper=self.dd_whisper, update_callback=self._update_model_options
            )

        self._safe_update()

    def _refresh_ui(self):
        """
        Force UI refresh.
        """
        self.update()
