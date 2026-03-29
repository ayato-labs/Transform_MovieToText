import logging
import os
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.intent_router import IntentRouter
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
        self.router = IntentRouter(config_mgr)

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

        # Build Main View Layout
        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("文字起こし & AI 変換", size=32, weight=ft.FontWeight.BOLD),
                            ft.Text("動画や音声から議事録を自動生成します", size=14, color=ft.Colors.GREY_400),
                        ]
                    ),
                    ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._refresh_ui(), tooltip="表示を更新"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=30, color=ft.Colors.GREY_800),
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
            self.update()

            def on_chunk(text):
                # Update text in real-time
                self.raw_transcript_text.value += text + " "
                self.update()

            try:
                # Defaulting to system audio for live meetings
                self.service.start_live_recording(model_name=model, source="system", on_text_added=on_chunk)
                state.set("is_recording", True)
                self.status_text.value = "🎙 システム音をリアルタイム録音・文字起こし中..."
                self.update()
            except Exception as ex:
                logger.error(f"Live recording start failed: {ex}")
                self.status_text.value = f"⚠️ 録音開始エラー: {ex}"
                self._set_recording_ui_state(False)
                self.update()
        else:
            # Transition to STOP
            self.status_text.value = "録音を停止して最後の処理を行っています..."
            self.update()
            self.service.stop_live_recording(finalize_callback=self._on_live_finalized)

    def _on_live_finalized(self, full_text, category):
        state.set("is_recording", False)
        self._set_recording_ui_state(False)
        self.raw_transcript_text.value = full_text
        self.status_text.value = f"ライブ文字起こし完了 (自動分類: {category if category else '未分類'})"
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

    def init_view(self, model_options: list):
        """
        Stub for additional initialization if needed by FletApp.
        """
        pass

    def _refresh_ui(self):
        """
        Force UI refresh.
        """
        self.update()
