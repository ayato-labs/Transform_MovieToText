import logging
import threading

import flet as ft

from src.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class SettingsView(ft.Column):
    def __init__(self, config_mgr: ConfigManager, hw_info: dict, model_requirements: dict, history_ctrl=None, minutes_ctrl=None):
        super().__init__(expand=True, scroll="auto")
        self.config_mgr = config_mgr
        self.hw_info = hw_info
        self.model_requirements = model_requirements
        self.history_ctrl = history_ctrl
        self.minutes_ctrl = minutes_ctrl

        # Pickers
        self.knowledge_folder_picker = ft.FilePicker(on_result=self._on_knowledge_folder_result)

        # AI Provider Selection
        self.provider_dd = ft.Dropdown(
            label="AIプロバイダー (文字起こし後の解析用)",
            width=300,
            options=[
                ft.dropdown.Option("ollama_local", "Ollama (100% ローカル)"),
                ft.dropdown.Option("gemini_api", "Gemini API (Google クラウド)"),
            ],
            on_change=self._on_provider_change
        )

        # Ollama Settings
        self.ollama_url = ft.TextField(
            label="Ollama Base URL", 
            width=500, 
            hint_text="http://localhost:11434",
            on_change=self._on_settings_change
        )

        # Gemini Settings
        self.gemini_key = ft.TextField(
            label="Gemini API Key",
            width=500,
            password=True,
            can_reveal_password=True,
            on_change=self._on_settings_change
        )

        # Settings Containers
        self.ollama_container = ft.Column([
            ft.Text("Ollama 設定", weight="bold"),
            self.ollama_url,
        ], visible=False)

        self.gemini_container = ft.Column([
            ft.Text("Gemini API 設定", weight="bold"),
            self.gemini_key,
            ft.Text("※ APIキーは端末にのみ保存され、開発元には送信されません。", size=12, color="grey500"),
        ], visible=False)

        # Knowledge Library
        self.knowledge_dir_field = ft.TextField(
            label="ナレッジディレクトリ",
            expand=True,
            read_only=True,
        )
        
        # Hardware & Model Info
        self.model_list_column = ft.Column(spacing=5)
        self.force_gpu_checkbox = ft.Checkbox(label="GPUを強制使用する", on_change=self._on_force_gpu_change)

        # Build Layout
        self.controls = [
            ft.Text("設定", size=24, weight="bold"),
            ft.Divider(),
            
            # AI Provider Section
            ft.Text("AIプロバイダー構成", size=18, weight="w500"),
            self.provider_dd,
            ft.Container(height=10),
            self.ollama_container,
            self.gemini_container,
            ft.Divider(),

            # Model Management
            ft.Text("ローカルAIモデル管理", size=18, weight="w500"),
            ft.Container(
                content=self.model_list_column,
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=10,
            ),
            ft.Divider(),

            # Knowledge Base
            ft.Text("ナレッジエンジン (Local RAG)", size=18, weight="w500"),
            ft.Row([
                self.knowledge_dir_field,
                ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: self.knowledge_folder_picker.get_directory_path()),
                ft.ElevatedButton("同期", icon=ft.Icons.SYNC, on_click=self._on_sync_click),
            ]),
            ft.Divider(),

            # HW Info
            ft.Text("ハードウェア情報", size=18, weight="w500"),
            ft.Row([ft.Icon(ft.Icons.MEMORY), ft.Text(f"RAM: {self.hw_info['ram']} GB")]),
            ft.Row([ft.Icon(ft.Icons.DEVELOPER_BOARD), ft.Text(f"VRAM: {self.hw_info['vram']} GB")]),
            ft.Divider(),

            # Debug
            ft.Text("デバッグ・保守", size=18, weight="w500"),
            ft.Row([
                ft.ElevatedButton("ログをコピー", icon=ft.Icons.COPY_ALL, on_click=self._on_export_logs_click),
                ft.ElevatedButton("フォルダを開く", icon=ft.Icons.FOLDER_SHARED, on_click=self._on_open_data_dir_click),
            ]),
            ft.Divider(),

            ft.Text("Whisper設定", size=18, weight="w500"),
            self.force_gpu_checkbox,
        ]

    def _on_provider_change(self, e):
        provider = self.provider_dd.value
        self.config_mgr.set_active_provider(provider)
        self._update_visibility()
        self._refresh_model_list()

    def _update_visibility(self):
        provider = self.config_mgr.get_active_provider()
        self.ollama_container.visible = (provider == "ollama_local")
        self.gemini_container.visible = (provider == "gemini_api")
        self._safe_update()

    def _on_settings_change(self, e):
        provider = self.config_mgr.get_active_provider()
        if provider == "ollama_local":
            self.config_mgr.set_provider_config("ollama_local", {"base_url": self.ollama_url.value, "api_key": ""})
        elif provider == "gemini_api":
            self.config_mgr.set_provider_config("gemini_api", {"base_url": None, "api_key": self.gemini_key.value})

    def _on_force_gpu_change(self, e):
        self.config_mgr.set_force_gpu(e.control.value)

    def _refresh_model_list(self):
        if not self.minutes_ctrl:
            return
        self.model_list_column.controls = [ft.Text("取得中...", italic=True)]
        self._safe_update()

        def fetch_worker():
            try:
                provider = self.config_mgr.get_active_provider()
                models = self.minutes_ctrl.service.get_models_info(provider)
                new_controls = []
                if not models:
                    new_controls.append(ft.Text("モデルが見つかりません。", color="grey500"))
                else:
                    for m in models:
                        new_controls.append(ft.Row([
                            ft.Icon(ft.Icons.SETTINGS_INPUT_COMPONENT, size=16),
                            ft.Text(m["name"], expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda _, n=m["name"]: self._delete_model(n))
                        ]))
                self.model_list_column.controls = new_controls
                self._safe_update()
            except Exception:
                self.model_list_column.controls = [ft.Text("エラー発生", color="red")]
                self._safe_update()
        threading.Thread(target=fetch_worker, daemon=True).start()

    def _delete_model(self, name):
        if self.minutes_ctrl.service.delete_model(self.config_mgr.get_active_provider(), name):
            self._refresh_model_list()

    def _on_sync_click(self, e):
        # Implementation in history_ctrl
        logger.warning("SettingsView: Sync functionality not implemented yet.")

    def _on_knowledge_folder_result(self, e):
        if e.path:
            self.knowledge_dir_field.value = e.path
            self.config_mgr.set_knowledge_dir(e.path)
            self._safe_update()

    def _on_export_logs_click(self, e):
        # Existing logic
        logger.warning("SettingsView: Export logs functionality not implemented yet.")

    def _on_open_data_dir_click(self, e):
        # Existing logic
        logger.warning("SettingsView: Open data directory functionality not implemented yet.")

    def init_view(self):
        if self.page and self.knowledge_folder_picker not in self.page.overlay:
            self.page.overlay.append(self.knowledge_folder_picker)
        
        provider = self.config_mgr.get_active_provider()
        self.provider_dd.value = provider
        
        o_conf = self.config_mgr.get_provider_config("ollama_local")
        self.ollama_url.value = o_conf.get("base_url", "http://localhost:11434")
        
        g_conf = self.config_mgr.get_provider_config("gemini_api")
        self.gemini_key.value = g_conf.get("api_key", "")
        
        self.force_gpu_checkbox.value = self.config_mgr.get_force_gpu()
        self.knowledge_dir_field.value = self.config_mgr.get_knowledge_dir()
        
        self._update_visibility()
        self._refresh_model_list()

    def _safe_update(self):
        try:
            self.update()
        except Exception as e:
            logger.debug(f"UI Update failed (possibly detached): {e}")
