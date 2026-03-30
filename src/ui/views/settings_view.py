import flet as ft

from src.core.config_manager import ConfigManager


class SettingsView(ft.Column):
    def __init__(self, config_mgr: ConfigManager, hw_info: dict, model_requirements: dict, history_ctrl=None):
        super().__init__(expand=True, scroll="auto")
        self.config_mgr = config_mgr
        self.hw_info = hw_info
        self.model_requirements = model_requirements
        self.history_ctrl = history_ctrl

        # Initialize UI Components
        self.gemini_api_key = ft.TextField(
            label="Gemini API Key", password=True, can_reveal_password=True, width=500, on_change=self._on_settings_change
        )
        self.ollama_local_url = ft.TextField(
            label="Ollama Local Base URL", width=500, hint_text="http://localhost:11434", on_change=self._on_settings_change
        )
        self.ollama_cloud_api_key = ft.TextField(
            label="Ollama Cloud API Key", password=True, can_reveal_password=True, width=500, on_change=self._on_settings_change
        )
        self.ollama_cloud_url = ft.TextField(label="Ollama Cloud URL", width=500, hint_text="https://ollama.com", on_change=self._on_settings_change)
        self.force_gpu_checkbox = ft.Checkbox(label="GPUを強制使用する (VRAM不足警告を無視)", on_change=self._on_force_gpu_change)

        # Project Management
        self.project_to_delete_dd = ft.Dropdown(
            label="削除するプロジェクトを選択",
            width=400,
            options=[],
        )
        self.delete_project_btn = ft.ElevatedButton(
            "選択したプロジェクトを削除",
            icon=ft.Icons.DELETE_FOREVER,
            color=ft.Colors.RED_400,
            on_click=self._show_delete_confirmation,
        )

        # Embedding Provider selection
        self.embedding_provider_dropdown = ft.Dropdown(
            label="Embeddingプロバイダー (将来の検索機能用)",
            options=[
                ft.dropdown.Option("local", "Local (FastEmbed - 効率的/プライバシー重視)"),
                ft.dropdown.Option("google", "Google Gemini (高性能/オンライン必須)"),
            ],
            width=500,
            on_change=self._on_embedding_provider_change,
        )

        # Hardware display
        self.hw_rows = ft.Column(
            [
                ft.Row([ft.Icon(ft.Icons.COMPUTER), ft.Icon(ft.Icons.MEMORY), ft.Text(f"System RAM: {hw_info['ram']} GB")]),
                ft.Row([ft.Icon(ft.Icons.STORAGE), ft.Icon(ft.Icons.DEVELOPER_BOARD), ft.Text(f"GPU VRAM: {hw_info['vram']} GB")]),
            ]
        )

        # Model compatibility list
        self.comp_items = ft.Column(spacing=0)
        self._build_compatibility_list()

        # Build Layout
        self.controls = [
            ft.Text("設定", size=24, weight="bold"),
            ft.Divider(),
            ft.Text("プロジェクト管理", size=18, weight="w500"),
            ft.Text("プロジェクトを削除すると、そのプロジェクトに属していたデータは自動的に「その他」へ移動されます。", size=13, color="grey500"),
            ft.Row([self.project_to_delete_dd, self.delete_project_btn], alignment=ft.MainAxisAlignment.START),
            ft.Divider(),
            ft.Text("AIプロバイダー設定", size=18, weight="w500"),
            self._create_card("Google Gemini", [self.gemini_api_key]),
            self._create_card("Ollama Local (ローカルまたはPattern 1)", [self.ollama_local_url]),
            self._create_card("Ollama Cloud (クラウドAPIを消費)", [self.ollama_cloud_api_key, self.ollama_cloud_url]),
            ft.Divider(),
            ft.Text("Embedding設定 (プライバシー/検索精度)", size=18, weight="w500"),
            self.embedding_provider_dropdown,
            ft.Divider(),
            ft.Text("ハードウェア情報", size=18, weight="w500"),
            self.hw_rows,
            ft.Text("モデル適合状況 (目安):", size=14, italic=True),
            ft.Container(
                content=self.comp_items,
                border=ft.border.all(1, "grey700"),
                border_radius=10,
                padding=10,
            ),
            ft.Divider(),
            ft.Text("Whisper設定", size=18, weight="w500"),
            self.force_gpu_checkbox,
        ]

    def _create_card(self, title: str, controls: list):
        return ft.Card(content=ft.Container(content=ft.Column([ft.Text(title, weight="bold")] + controls), padding=15))

    def _build_compatibility_list(self):
        self.comp_items.controls.clear()
        for m, req in self.model_requirements.items():
            can_gpu = self.hw_info["vram"] >= req
            can_cpu = self.hw_info["ram"] >= req
            status_icon = ft.Icons.CHECK_CIRCLE if (can_gpu or can_cpu) else ft.Icons.CANCEL
            status_color = ft.Colors.GREEN if can_gpu else (ft.Colors.AMBER if can_cpu else ft.Colors.RED)
            device_text = f"適合 (Requirement: {req}GB)" if (can_gpu or can_cpu) else "推奨スペック不足"

            self.comp_items.controls.append(
                ft.ListTile(
                    leading=ft.Icon(status_icon, color=status_color),
                    title=ft.Text(m),
                    subtitle=ft.Text(device_text),
                )
            )

    def _show_delete_confirmation(self, e):
        project_name = self.project_to_delete_dd.value
        if not project_name:
            # Show snackbar or error if no project selected
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("削除するプロジェクトを選択してください。"))
                self.page.snack_bar.open = True
                self.page.update()
            return

        def confirm_delete(e_close):
            confirm_dialog.open = False
            self.page.update()
            self._execute_project_deletion(project_name)

        def cancel_delete(e_close):
            confirm_dialog.open = False
            self.page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("プロジェクトの削除"),
            content=ft.Text(f"プロジェクト「{project_name}」を削除しますか？\n所属していたデータは「その他」に移動されます。"),
            actions=[
                ft.TextButton("キャンセル", on_click=cancel_delete),
                ft.TextButton("削除する", on_click=confirm_delete, font_weight="bold", color=ft.Colors.RED),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()

    def _execute_project_deletion(self, project_name):
        if not self.history_ctrl:
            return

        success = self.history_ctrl.reassign_project(project_name, "その他")
        if success:
            # Refresh project list after deletion
            self._update_project_options()
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"プロジェクト「{project_name}」を削除し、データを「その他」に移動しました。"))
                self.page.snack_bar.open = True
                self.page.update()
        else:
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("プロジェクトの削除に失敗しました。"), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()

    def _update_project_options(self):
        if not self.history_ctrl:
            return

        projects = self.history_ctrl.get_projects()
        # Exclude internal/default names from deletion list if necessary
        # We allow deleting any project that exists.
        self.project_to_delete_dd.options = [ft.dropdown.Option(p) for p in projects if p and p != "その他"]
        self.project_to_delete_dd.value = None
        if self.page:
            self.update()

    def _on_settings_change(self, e):
        self.config_mgr.set_provider_config("gemini", {"api_key": self.gemini_api_key.value})
        self.config_mgr.set_provider_config("ollama_local", {"base_url": self.ollama_local_url.value})
        self.config_mgr.set_provider_config("ollama_cloud", {"api_key": self.ollama_cloud_api_key.value, "base_url": self.ollama_cloud_url.value})

    def _on_force_gpu_change(self, e):
        self.config_mgr.set_force_gpu(e.control.value)

    def _on_embedding_provider_change(self, e):
        self.config_mgr.set_embedding_provider(e.control.value)

    def init_view(self):
        gemini_conf = self.config_mgr.get_provider_config("gemini")
        self.gemini_api_key.value = gemini_conf.get("api_key", "")

        ollama_local_conf = self.config_mgr.get_provider_config("ollama_local")
        self.ollama_local_url.value = ollama_local_conf.get("base_url", "http://localhost:11434")

        ollama_cloud_conf = self.config_mgr.get_provider_config("ollama_cloud")
        self.ollama_cloud_api_key.value = ollama_cloud_conf.get("api_key", "")
        self.ollama_cloud_url.value = ollama_cloud_conf.get("base_url", "https://ollama.com")

        self.force_gpu_checkbox.value = self.config_mgr.get_force_gpu()
        self.embedding_provider_dropdown.value = self.config_mgr.get_embedding_provider()

        # Load and update projects list
        self._update_project_options()

        if self.page:
            self.update()
