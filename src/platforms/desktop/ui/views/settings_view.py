import logging
import os
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.platform_utils import get_log_path

logger = logging.getLogger(__name__)


class SettingsView(ft.Column):
    def __init__(self, config_mgr: ConfigManager, hw_info: dict, model_requirements: dict, history_ctrl=None, minutes_ctrl=None):
        super().__init__(expand=True, scroll="auto")
        self.config_mgr = config_mgr
        self.hw_info = hw_info
        self.model_requirements = model_requirements
        self.history_ctrl = history_ctrl
        self.minutes_ctrl = minutes_ctrl

        # Folder picker for Knowledge Library
        self.knowledge_folder_picker = ft.FilePicker(on_result=self._on_knowledge_folder_result)

        # Initialize UI Components
        self.ollama_local_url = ft.TextField(
            label="Ollama Local Base URL", width=500, hint_text="http://localhost:11434", on_change=self._on_settings_change
        )
        self.force_gpu_checkbox = ft.Checkbox(label="GPUを強制使用する (VRAM不足警告を無視)", on_change=self._on_force_gpu_change)

        # Knowledge Library UI
        self.knowledge_dir_field = ft.TextField(
            label="ナレッジライブラリのディレクトリ (.md, .txt, .csv)",
            expand=True,
            read_only=True,
            hint_text="フォルダを選択してください...",
        )
        self.knowledge_sync_btn = ft.ElevatedButton(
            "ナレッジを同期",
            icon=ft.Icons.SYNC,
            on_click=self._on_sync_click,
            tooltip="フォルダ内のファイルをスキャンしてデータベースを更新します",
        )

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

        # Hardware display
        self.hw_rows = ft.Column(
            [
                ft.Row([ft.Icon(ft.Icons.COMPUTER), ft.Icon(ft.Icons.MEMORY), ft.Text(f"System RAM: {self.hw_info['ram']} GB")]),
                ft.Row([ft.Icon(ft.Icons.STORAGE), ft.Icon(ft.Icons.DEVELOPER_BOARD), ft.Text(f"GPU VRAM: {self.hw_info['vram']} GB")]),
            ]
        )

        # Model compatibility list
        self.comp_items = ft.Column(spacing=0)
        self._build_compatibility_list()

        # Model Management Column
        self.model_list_column = ft.Column(spacing=5)

        # Build Layout
        self.controls = [
            ft.Text("設定", size=24, weight="bold"),
            ft.Divider(),
            ft.Text("ローカルAIモデル管理", size=18, weight="w500"),
            ft.Text("PC内に保存されているAIモデルです。不要なモデルを削除してディスク容量を確保できます。", size=13, color="grey500"),
            ft.Container(
                content=self.model_list_column,
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=10,
            ),
            ft.Divider(),
            ft.Text("ナレッジエンジン (Local RAG)", size=18, weight="w500"),
            ft.Text("指定したフォルダ内のドキュメントを検索対象に含めます。外部送信は一切行われません。", size=13, color="grey500"),
            ft.Row(
                [
                    self.knowledge_dir_field,
                    ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: self.knowledge_folder_picker.get_directory_path()),
                    self.knowledge_sync_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Divider(),
            ft.Text("プロジェクト管理", size=18, weight="w500"),
            ft.Text("プロジェクトを削除すると、そのプロジェクトに属していたデータは自動的に「その他」へ移動されます。", size=13, color="grey500"),
            ft.Row([self.project_to_delete_dd, self.delete_project_btn], alignment=ft.MainAxisAlignment.START),
            ft.Divider(),
            ft.Text("AIプロバイダー構成 (完全ローカル)", size=18, weight="w500"),
            ft.Text("1バイトも外部に送信されません。機密情報は安全に保護されます。", size=13, color=ft.Colors.GREEN),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([ft.Text("Ollama Local", weight="bold"), self.ollama_local_url]),
                    padding=15,
                    border_radius=10,
                )
            ),
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
            ft.Text("デバッグ・ログ設定", size=18, weight="w500"),
            ft.Text(f"Log Path: {get_log_path()}", size=11, color="grey"),
            ft.ElevatedButton("デバッグログをクリップボードにコピー", icon=ft.Icons.COPY_ALL, on_click=self._on_export_logs_click),
            ft.Divider(),
            ft.Text("Whisper設定", size=18, weight="w500"),
            self.force_gpu_checkbox,
        ]

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

    def _refresh_model_list(self):
        if not self.minutes_ctrl:
            return
            
        self.model_list_column.controls = [ft.Text("モデル情報を取得中...", italic=True, color="grey500")]
        self._safe_update()

        def fetch_worker():
            try:
                provider = self.config_mgr.get_active_provider()
                models = self.minutes_ctrl.service.get_models_info(provider)
                
                new_controls = []
                if not models:
                    new_controls.append(ft.Text("インストール済みのモデルはありません。", color="grey500"))
                else:
                    for m in models:
                        new_controls.append(
                            ft.Row([
                                ft.Icon(ft.Icons.SETTINGS_INPUT_COMPONENT, size=16),
                                ft.Text(m["name"], weight="bold", expand=True),
                                ft.Text(f"{m['size_gb']} GB", color="grey500"),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    tooltip="このモデルを削除",
                                    icon_color=ft.Colors.RED_300,
                                    on_click=lambda _, name=m["name"]: self._show_model_delete_confirmation(name)
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        )
                
                self.model_list_column.controls = new_controls
                self._safe_update()
            except Exception as e:
                logger.error(f"Failed to refresh model list: {e}")
                self.model_list_column.controls = [ft.Text(f"エラー: {e}", color="red")]
                self._safe_update()

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _show_model_delete_confirmation(self, model_name):
        def confirm_delete(e_close):
            if self.page:
                self.page.close(confirm_dialog)
            self._execute_model_deletion(model_name)

        def cancel_delete(e_close):
            if self.page:
                self.page.close(confirm_dialog)

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("AIモデルの削除"),
            content=ft.Text(f"モデル「{model_name}」をPCから完全に削除しますか？\n再度使用するには再ダウンロードが必要です。"),
            actions=[
                ft.TextButton("キャンセル", on_click=cancel_delete),
                ft.TextButton(content=ft.Text("削除する", weight="bold", color=ft.Colors.RED), on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if self.page:
            self.page.open(confirm_dialog)

    def _execute_model_deletion(self, model_name):
        provider = self.config_mgr.get_active_provider()
        success = self.minutes_ctrl.service.delete_model(provider, model_name)
        if success:
            self._show_info(f"モデル「{model_name}」を削除しました。")
            self._refresh_model_list()
        else:
            self._show_info(f"モデル「{model_name}」の削除に失敗しました。", bgcolor=ft.Colors.RED_700)

    def _on_knowledge_folder_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.knowledge_dir_field.value = e.path
            self.config_mgr.set_knowledge_dir(e.path)
            self._show_info(f"ナレッジディレクトリを設定しました: {e.path}")
            self._safe_update()

    def _on_sync_click(self, e):
        if not self.history_ctrl:
            return

        target_dir = self.knowledge_dir_field.value
        if not target_dir or not os.path.exists(target_dir):
            self._show_info("有効なディレクトリを選択してください。", bgcolor=ft.Colors.RED_400)
            return

        self.knowledge_sync_btn.disabled = True
        self.knowledge_sync_btn.text = "同期中..."
        self._safe_update()

        try:
            # We'll implement sync_knowledge in the controller later
            if hasattr(self.history_ctrl, "sync_knowledge"):
                count = self.history_ctrl.sync_knowledge(target_dir)
                self._show_info(f"同期完了: {count}個のファイルをインデックスしました。")
            else:
                self._show_info("エラー: 同期機能がまだ実装されていません。", bgcolor=ft.Colors.RED_400)
        except Exception as ex:
            logger.error(f"Sync failed: {ex}")
            self._show_info(f"同期失敗: {ex}", bgcolor=ft.Colors.RED_400)

        self.knowledge_sync_btn.disabled = False
        self.knowledge_sync_btn.text = "ナレッジを同期"
        self._safe_update()

    def _show_delete_confirmation(self, e):
        project_name = self.project_to_delete_dd.value
        if not project_name:
            self._show_info("削除するプロジェクトを選択してください。")
            return

        def confirm_delete(e_close):
            if self.page:
                self.page.close(confirm_dialog)
            self._execute_project_deletion(project_name)

        def cancel_delete(e_close):
            if self.page:
                self.page.close(confirm_dialog)

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("プロジェクトの削除"),
            content=ft.Text(f"プロジェクト「{project_name}」を削除しますか？\n所属していたデータは「その他」に移動されます。"),
            actions=[
                ft.TextButton("キャンセル", on_click=cancel_delete),
                ft.TextButton(content=ft.Text("削除する", weight="bold", color=ft.Colors.RED), on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if self.page:
            self.page.open(confirm_dialog)

    def _execute_project_deletion(self, project_name):
        if not self.history_ctrl:
            return

        success = self.history_ctrl.reassign_project(project_name, "その他")
        if success:
            self._update_project_options()
            self._show_info(f"プロジェクト「{project_name}」を削除しました。")
        else:
            self._show_info("プロジェクトの削除に失敗しました。", bgcolor=ft.Colors.RED_700)

    def _update_project_options(self):
        if not self.history_ctrl:
            return

        projects = self.history_ctrl.get_projects()
        if self.page:
            self.project_to_delete_dd.options = [ft.dropdown.Option(p) for p in projects if p and p != "その他"]
            self.project_to_delete_dd.value = None
            self._safe_update()

    def _on_settings_change(self, e):
        self.config_mgr.set_provider_config("ollama_local", {"base_url": self.ollama_local_url.value})

    def _on_force_gpu_change(self, e):
        self.config_mgr.set_force_gpu(e.control.value)

    def init_view(self):
        # Attach file picker to page overlay
        if self.page and self.knowledge_folder_picker not in self.page.overlay:
            self.page.overlay.append(self.knowledge_folder_picker)

        ollama_local_conf = self.config_mgr.get_provider_config("ollama_local")
        self.ollama_local_url.value = ollama_local_conf.get("base_url", "http://localhost:11434")
        self.force_gpu_checkbox.value = self.config_mgr.get_force_gpu()
        self.knowledge_dir_field.value = self.config_mgr.get_knowledge_dir()

        self._update_project_options()
        self._refresh_model_list()
        self._safe_update()

    def _safe_update(self):
        """Helper to update the control only if it is currently attached to a page."""
        try:
            if self.page:
                self.update()
        except Exception:
            # Control might have been removed from the page tree during async operation
            pass

    def _on_export_logs_click(self, e):
        log_file = get_log_path()
        if not os.path.exists(log_file):
            self._show_info("ログファイルが見つかりません。")
            return
        try:
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
            self.page.set_clipboard(content)
            self._show_info("ログをクリップボードにコピーしました。")
        except Exception as ex:
            logger.error(f"Failed to export logs: {ex}")
            self._show_info(f"ログ出力失敗: {ex}", bgcolor=ft.Colors.RED_400)

    def _show_info(self, text: str, bgcolor: str = None):
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=bgcolor)
            self.page.snack_bar.open = True
            self.page.update()
