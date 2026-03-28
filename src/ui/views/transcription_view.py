import logging
import os
import threading

import flet as ft

from src.config_manager import ConfigManager
from src.core.intent_router import IntentRouter, TransformationStrategy
from src.core.transcription_service import TranscriptionService
from src.core.utils import get_resource_path

logger = logging.getLogger(__name__)


class TranscriptionView(ft.UserControl):
    """
    Main View for Transcription and Transformation.
    Refactored for scrollable results and robust layout.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager, service: TranscriptionService):
        super().__init__()
        self.page = page
        self.config_mgr = config_mgr
        self.service = service
        self.router = IntentRouter(config_mgr)

        # UI Components
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.page.overlay.append(self.file_picker)

        self.status_text = ft.Text("待機中...", color=ft.colors.GREY_500)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=ft.colors.BLUE_400)

        self.result_text = ft.TextField(
            label="AI 変換結果",
            multiline=True,
            min_lines=15,
            max_lines=None,
            read_only=False,
            expand=True,
            text_size=14,
            border_color=ft.colors.BLUE_700,
            shift_enter=True,
        )

        self.raw_transcript_text = ft.TextField(
            label="生文字起こしログ",
            multiline=True,
            min_lines=15,
            max_lines=None,
            read_only=True,
            expand=True,
            text_size=12,
            border_color=ft.colors.GREY_700,
        )

        self.tab_results = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(text="AI 変換 (要約/議事録)", content=ft.Column([self.result_text], scroll=ft.ScrollMode.ALWAYS, expand=True)),
                ft.Tab(text="文字起こし全文", content=ft.Column([self.raw_transcript_text], scroll=ft.ScrollMode.ALWAYS, expand=True)),
            ],
        )

    def build(self):
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("文字起こし & AI 変換", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.icons.REFRESH, on_click=lambda _: self._refresh_ui()),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "ファイルを選択",
                            icon=ft.icons.UPLOAD_FILE,
                            on_click=lambda _: self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["mp4", "mkv", "mp3", "wav"]),
                        ),
                        ft.ElevatedButton("録音開始 (Live)", icon=ft.icons.MIC, on_click=self._on_start_live, color=ft.colors.RED_400),
                        ft.ElevatedButton("録音停止", icon=ft.icons.STOP, on_click=self._on_stop_live, color=ft.colors.GREY_400),
                    ],
                    spacing=10,
                ),
                self.status_text,
                self.progress_bar,
                ft.Container(
                    content=self.tab_results,
                    expand=True,
                    padding=10,
                    border=ft.border.all(1, ft.colors.GREY_800),
                    border_radius=10,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton("結果を保存", icon=ft.icons.SAVE, on_click=self._on_save_result, bgcolor=ft.colors.BLUE_900),
                        ft.Text("※Markdown形式で保存されます", size=12, color=ft.colors.GREY_500),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        )

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        file_path = e.files[0].path
        threading.Thread(target=self._process_file, args=(file_path,), daemon=True).start()

    def _process_file(self, file_path: str):
        try:
            self.status_text.value = f"処理中: {os.path.basename(file_path)}"
            self.progress_bar.visible = True
            self.update()

            model = self.config_mgr.get_last_model()
            transcript = self.service.transcribe_file_sync(
                file_path=file_path,
                model_name=model,
                progress_callback=self._update_progress
            )

            self.raw_transcript_text.value = transcript
            self.status_text.value = "文字起こし完了。AI 変換中..."
            self.update()

            # Intent Routing & Strategy Selection
            provider = self.config_mgr.get_active_provider()
            routing = self.router.route(transcript, provider, self.config_mgr.get_provider_config(provider).get("model", "gemini-1.5-flash"))
            
            self.status_text.value = f"AI戦略実行中: {routing['strategy'].name} ({routing['confidence']:.1%})"
            self.update()

            # Mock strategy execution for now
            ai_result = f"## 検出された戦略: {routing['strategy'].name}\n\n{transcript[:1000]}..."
            self.result_text.value = ai_result
            
            self.status_text.value = "すべての処理が完了しました。"
            self.progress_bar.visible = False
            self.tab_results.selected_index = 0
            self.update()

        except Exception as ex:
            logger.error(f"File processing failed: {ex}")
            self.status_text.value = f"エラー発生: {ex}"
            self.progress_bar.visible = False
            self.update()

    def _update_progress(self, val: float):
        self.progress_bar.value = val
        self.update()

    def _on_start_live(self, _):
        # Implementation omitted for brevity
        pass

    def _on_stop_live(self, _):
        # Implementation omitted for brevity
        pass

    def _on_save_result(self, _):
        # Implementation omitted for brevity
        pass

    def _refresh_ui(self):
        self.update()
