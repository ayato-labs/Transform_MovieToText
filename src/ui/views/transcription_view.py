import os

import flet as ft

from src.controllers.transcription_ctrl import TranscriptionController
from src.core.state import state


class TranscriptionView(ft.Column):
    def __init__(self, controller: TranscriptionController, file_picker: ft.FilePicker, save_picker: ft.FilePicker):
        super().__init__(expand=True, scroll="auto")
        self.controller = controller
        self.file_picker = file_picker
        self.save_picker = save_picker

        # Initialize UI Components
        self.path_text = ft.Text("ファイルが選択されていません", color="grey500")

        # Whisper model dropdown (initial value from state)
        self.whisper_model_dropdown = ft.Dropdown(label="Whisperモデル", width=250, on_change=self._on_model_change)

        self.force_gpu_checkbox = ft.Checkbox(label="GPUを強制使用する", on_change=self._on_force_gpu_change)
        self.visual_capture_checkbox = ft.Checkbox(label="映像も記録する", value=True, on_change=self._on_visual_capture_change)

        self.audio_source_radio = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="system", label="システム音 (Stereo Mix)"),
                    ft.Radio(value="microphone", label="マイク (Default Mic)"),
                ]
            ),
            on_change=self._on_source_change,
        )

        self.project_name_field = ft.TextField(
            label="プロジェクト名 (空欄で「その他」)", hint_text="例: AI研究プロジェクト", width=300, on_change=self._on_project_change
        )

        self.category_field = ft.TextField(
            label="大分類 (空欄でAI自動生成)", hint_text="例: AI, Python, 議事録", width=300, on_change=self._on_category_change
        )

        self.transcribe_btn = ft.ElevatedButton(
            "動画ファイルを選択して開始",
            icon="play_arrow",
            style=ft.ButtonStyle(color="white", bgcolor="green700"),
            on_click=self._on_transcribe_click,
        )

        self.live_record_btn = ft.ElevatedButton(
            "録音文字起こし開始", icon="mic", style=ft.ButtonStyle(color="white", bgcolor="red700"), on_click=self._on_live_click
        )

        self.status_text = ft.Text("待機中", color="grey400")
        self.gpu_warning_text = ft.Text("", color="orange700", weight="bold", size=12)
        self.progress_bar = ft.ProgressBar(width=400, color="blue", visible=False)

        self.result_area = ft.TextField(
            label="文字起こし結果",
            multiline=True,
            min_lines=15,
            max_lines=20,
            expand=True,
            read_only=False,
            text_size=14,
            on_change=self._on_result_change,
        )

        # Build Layout
        self.controls = [
            ft.Text("文字起こし (Whisper)", size=24, weight="bold"),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "動画ファイルを選択",
                        icon="folder_open",
                        on_click=lambda _: self.file_picker.pick_files(),
                    ),
                    self.path_text,
                ]
            ),
            ft.Column(
                [
                    ft.Row([self.whisper_model_dropdown, self.force_gpu_checkbox, self.visual_capture_checkbox]),
                    ft.Row([ft.Text("録音ソース: ", weight="bold"), self.audio_source_radio]),
                    ft.Row([self.project_name_field, self.category_field]),
                    ft.Row([self.transcribe_btn, self.live_record_btn]),
                    self.status_text,
                    self.gpu_warning_text,
                    self.progress_bar,
                ]
            ),
            self.result_area,
            ft.Row(
                [
                    ft.ElevatedButton("結果を保存", icon="save", on_click=self._on_save_click),
                ],
                alignment="end",
            ),
        ]

        # Subscribe to state changes
        state.subscribe("transcript_text", self._update_result)
        state.subscribe("status_text", self._update_status)
        state.subscribe("is_recording", self._update_recording_ui)
        state.subscribe("is_processing", self._update_processing_ui)
        state.subscribe("gpu_warning", self._update_gpu_warning)
        state.subscribe("progress_visible", self._update_progress)
        state.subscribe("selected_file_path", self._update_path)

    def _update_result(self, val):
        self.result_area.value = val
        if self.page:
            self.update()

    def _update_status(self, val):
        self.status_text.value = val
        if self.page:
            self.update()

    def _update_recording_ui(self, is_recording):
        if is_recording:
            self.live_record_btn.text = "録音停止"
            self.live_record_btn.icon = "stop"
            self.live_record_btn.style.bgcolor = "grey700"
            self.transcribe_btn.disabled = True
        else:
            self.live_record_btn.text = "録音文字起こし開始"
            self.live_record_btn.icon = "mic"
            self.live_record_btn.style.bgcolor = "red700"
            self.transcribe_btn.disabled = False
        if self.page:
            self.update()

    def _update_processing_ui(self, is_processing):
        self.transcribe_btn.disabled = is_processing
        if self.page:
            self.update()

    def _update_gpu_warning(self, val):
        self.gpu_warning_text.value = val
        if self.page:
            self.update()

    def _update_progress(self, val):
        self.progress_bar.visible = val
        if self.page:
            self.update()

    def _update_path(self, val):
        self.path_text.value = os.path.basename(val) if val else "ファイルが選択されていません"
        if self.page:
            self.update()

    def _on_model_change(self, e):
        state.set("whisper_model", e.control.value)
        self.controller.config_mgr.set_whisper_model(e.control.value)

    def _on_force_gpu_change(self, e):
        state.set("force_gpu", e.control.value)
        self.controller.config_mgr.set_force_gpu(e.control.value)

    def _on_source_change(self, e):
        state.set("audio_source", e.control.value)
        self.controller.config_mgr.set_audio_source(e.control.value)

    def _on_project_change(self, e):
        state.set("project_name", e.control.value)

    def _on_category_change(self, e):
        state.set("category", e.control.value)

    def _on_visual_capture_change(self, e):
        state.set("visual_capture_enabled", e.control.value)
        self.controller.config_mgr.set_visual_capture_enabled(e.control.value)

    def _on_transcribe_click(self, e):
        path = state.get("selected_file_path")
        model = state.get("whisper_model")
        self.controller.start_file_transcription(path, model)

    def _on_live_click(self, e):
        model = state.get("whisper_model")
        source = state.get("audio_source")
        self.controller.toggle_live_recording(model, source)

    def _on_save_click(self, e):
        path = state.get("selected_file_path")
        base_name = os.path.splitext(os.path.basename(path))[0] if path else "transcript"
        self.save_picker.save_file(file_name=f"【文字起こし】{base_name}.txt")

    def _on_result_change(self, e):
        state.set("transcript_text", e.control.value, notify=False)  # Don't re-notify self

    def init_view(self, model_options):
        """Called once to set initial values from config."""
        self.whisper_model_dropdown.options = model_options
        self.whisper_model_dropdown.value = self.controller.config_mgr.get_whisper_model()
        self.force_gpu_checkbox.value = self.controller.config_mgr.get_force_gpu()
        self.visual_capture_checkbox.value = self.controller.config_mgr.get_visual_capture_enabled()
        self.audio_source_radio.value = self.controller.config_mgr.get_audio_source()
        # Set initial state
        state.set("whisper_model", self.whisper_model_dropdown.value, notify=False)
        state.set("force_gpu", self.force_gpu_checkbox.value, notify=False)
        state.set("visual_capture_enabled", self.visual_capture_checkbox.value, notify=False)
        state.set("audio_source", self.audio_source_radio.value, notify=False)
        if self.page:
            self.update()
