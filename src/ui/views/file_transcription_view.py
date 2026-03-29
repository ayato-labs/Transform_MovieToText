import logging
import os
import threading

import flet as ft

from src.controllers.transcription_ctrl import TranscriptionController
from src.core.config_manager import ConfigManager
from src.core.constants import DEFAULT_PROVIDERS, WHISPER_MODELS
from src.core.intent_router import IntentRouter
from src.ui.ui_utils import sync_llm_models

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
        self.router = IntentRouter(config_mgr)

        # File Pickers
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.save_picker = ft.FilePicker(on_result=self._on_save_picked)
        if self._page:
            self._page.overlay.extend([self.file_picker, self.save_picker])

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

        self.status_text = ft.Text("待機中...", color=ft.Colors.GREY_500)
        self.progress_bar = ft.ProgressBar(value=0, visible=False, color=ft.Colors.BLUE_400, height=8)

        self.dd_llm = ft.Dropdown(
            label="LLMモデル",
            width=220,
            options=[],  # Filled dynamically
            on_change=self._on_llm_change,
        )
        sync_llm_models(self._page, self.config_mgr, self.dd_provider.value, self.dd_llm, self.status_text)

        self.sw_visual = ft.Switch(
            label="映像情報を使用", value=False, tooltip="動画ファイルから10秒ごとに画像を抽出してAIに送信します（分析精度が向上します）"
        )

        self.btn_pick = ft.ElevatedButton(
            "ファイルを選択して開始",
            icon=ft.Icons.UPLOAD_FILE,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=lambda _: self.file_picker.pick_files(allow_multiple=False),
        )

        # Result Areas
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
            ft.Row([self.dd_whisper, self.dd_provider, self.dd_llm, self.sw_visual], spacing=10),
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

    def _create_whisper_option(self, model_name: str):
        req = {"tiny": 1, "base": 1, "small": 2, "medium": 5, "large-v2": 10, "large-v3": 10}.get(model_name, 5)
        can_gpu = self.hw_info.get("vram", 0.0) >= req
        suffix = "(GPU)" if can_gpu else "(CPU)"
        return ft.dropdown.Option(key=model_name, text=f"{model_name} {suffix}")

    def _on_whisper_change(self, e):
        self.config_mgr.set_whisper_model(self.dd_whisper.value)

    def _on_provider_change(self, e):
        self.config_mgr.set_active_provider(self.dd_provider.value)
        sync_llm_models(self._page, self.config_mgr, self.dd_provider.value, self.dd_llm, self.status_text)
        self.update()

    def _on_llm_change(self, e):
        self.config_mgr.set_last_model(self.dd_llm.value)

    def _on_file_picked(self, e):
        if not e.files:
            return
        file_path = e.files[0].path
        threading.Thread(target=self._process_flow, args=(file_path,), daemon=True).start()

    def _process_flow(self, file_path: str):
        try:
            self.btn_pick.disabled = True
            self.status_text.value = f"読み込み中: {os.path.basename(file_path)}"
            self.progress_bar.visible = True
            self.progress_bar.value = 0
            self.update()

            whisper_model = self.dd_whisper.value
            use_visual = self.sw_visual.value

            result_data = self.service.transcribe_file_sync(
                file_path=file_path, model_name=whisper_model, progress_callback=lambda p: self._update_progress(p), use_visual=use_visual
            )

            text = result_data["transcript"]
            visual_contexts = result_data.get("visual_contexts", [])

            self.raw_transcript_text.value = text
            if use_visual and visual_contexts:
                self.status_text.value = f"AIによるマルチモーダル解析中... (画像: {len(visual_contexts)}枚)"
            else:
                self.status_text.value = "AIによる解析中..."
            self.update()

            provider = self.dd_provider.value
            llm_model = self.dd_llm.value

            # Use unified transform for multimodal support
            system_prompt = (
                "あなたは文字起こしデータの分析エキスパートです。"
                "提供されたテキスト（および動画から抽出された画像コンテキスト）を分析し、"
                "最も重要と思われる内容を構造化されたレポートとして出力してください。"
            )

            ai_output = self.service.config_mgr.get_llm_client(provider, None).transform(
                transcript=text, model_name=llm_model, system_instruction=system_prompt, visual_contexts=visual_contexts if use_visual else None
            )

            self.result_text.value = ai_output
            self.tabs.selected_index = 0
            self.status_text.value = "処理完了"
            self.progress_bar.visible = False
            self.btn_pick.disabled = False
            self.update()
        except Exception as ex:
            error_msg = str(ex)
            if "VRAM不足" in error_msg:
                self.status_text.value = f"⚠️ {error_msg}"
                self.status_text.color = ft.Colors.RED_ACCENT_400
            else:
                self.status_text.value = f"エラー: {ex}"
                self.status_text.color = ft.Colors.RED_400
            self.btn_pick.disabled = False
            self.progress_bar.visible = False
            self.update()

    def _on_save_picked(self, e):
        if not e.path:
            return
        with open(e.path, "w", encoding="utf-8") as f:
            f.write(self.result_text.value)

    def _update_progress(self, val):
        self.progress_bar.value = val
        self.update()
