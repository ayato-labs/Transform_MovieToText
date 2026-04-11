import logging
import os

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.constants import EDITION_RESTRICTIONS, AppEdition
from src.core.platform_utils import get_log_path

logger = logging.getLogger(__name__)


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
        self.cloud_token = ft.TextField(
            label="Ayato Cloud Token",
            password=True,
            can_reveal_password=True,
            width=500,
            hint_text="ayato-xxxx-xxxx (PRO 機能を有効化)",
            on_change=self._on_cloud_token_change,
        )
        self.activate_btn = ft.ElevatedButton(
            "アクティベート",
            icon=ft.Icons.VERIFIED_OUTLINED,
            on_click=self._on_activate_click,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_900),
        )
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

        # Build Layout
        self.controls = [
            ft.Text("設定", size=24, weight="bold"),
            ft.Divider(),
            ft.Text("プロジェクト管理", size=18, weight="w500"),
            ft.Text("プロジェクトを削除すると、そのプロジェクトに属していたデータは自動的に「その他」へ移動されます。", size=13, color="grey500"),
            ft.Row([self.project_to_delete_dd, self.delete_project_btn], alignment=ft.MainAxisAlignment.START),
            ft.Divider(),
            ft.Text("Ayato Cloud アクティベーション", size=18, weight="bold", color=ft.Colors.BLUE_ACCENT),
            ft.Text("サブスクリプション特典のクラウド機能を有効化し、高品質な AI サーバーへアクセスします。", size=13),
            ft.Row([self.cloud_token, self.activate_btn]),
            ft.Divider(),
            ft.Text("AIプロバイダー構成", size=18, weight="w500"),
            self._create_provider_cards(),
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

    def _create_card(self, title: str, controls: list, disabled: bool = False, badge_text: str = None):
        header = [ft.Text(title, weight="bold")]
        if badge_text:
            header.append(
                ft.Container(
                    content=ft.Text(badge_text, size=10, color=ft.Colors.WHITE, weight="bold"),
                    bgcolor=ft.Colors.BLUE_ACCENT_700 if "PRO" in badge_text else ft.Colors.ORANGE_800,
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    border_radius=5,
                )
            )

        card_content = ft.Column(
            [
                ft.Row(header, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Column(controls, disabled=disabled),
            ]
        )

        if disabled:
            card_content.controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCK, size=14, color=ft.Colors.AMBER_300),
                        ft.Text("この機能は上位プランで利用可能です。クリックして詳細を表示", size=12, color=ft.Colors.AMBER_300, italic=True),
                    ]
                )
            )

        return ft.Card(
            content=ft.Container(
                content=card_content,
                padding=15,
                on_click=self._show_upgrade_modal if disabled else None,
                border_radius=10,
                ink=bool(disabled),  # Show ripple effect only when it's an 'upgrade' card
            ),
            opacity=0.6 if disabled else 1.0,
        )

    def _show_upgrade_modal(self, e):
        def copy_email(e_close):
            self.page.set_clipboard("cwblog69@gmail.com")
            self.page.snack_bar = ft.SnackBar(ft.Text("お問い合わせ先メールアドレスをコピーしました。"))
            self.page.snack_bar.open = True
            self.page.update()

        def close_modal(e_close):
            modal.open = False
            self.page.update()

        modal = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.UPGRADE, color=ft.Colors.AMBER), ft.Text("上位エディションへのアップグレード")]),
            content=ft.Column(
                [
                    ft.Text("商用利用、外部 AI 連携、データベース拡張などの高度な機能をご利用いただけます。", size=14),
                    ft.Divider(),
                    ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.BOLT, color=ft.Colors.BLUE),
                                title=ft.Text("PRO Edition"),
                                subtitle=ft.Text("Llama 3 / Phi 無制限利用、Gemini API 連携、商用ライセンス"),
                            ),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.BUSINESS, color=ft.Colors.PURPLE),
                                title=ft.Text("ENTERPRISE Edition"),
                                subtitle=ft.Text("MySQL / PostgreSQL 対応、組織内共有、専任サポート"),
                            ),
                        ],
                        tight=True,
                    ),
                    ft.Divider(),
                    ft.Text("詳細は、下記までお気軽にお問い合わせください：", size=12, weight="bold"),
                    ft.Row(
                        [
                            ft.Text("cwblog69@gmail.com", color=ft.Colors.BLUE_ACCENT),
                            ft.IconButton(ft.Icons.COPY, on_click=copy_email, tooltip="コピー"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                main_axis_size=ft.MainAxisSize.MIN,
                width=450,
            ),
            actions=[
                ft.TextButton("閉じる", on_click=close_modal),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = modal
        modal.open = True
        self.page.update()

    def _create_provider_cards(self):
        edition = self.config_mgr.get_edition()
        allowed = EDITION_RESTRICTIONS.get(edition, {}).get("allowed_providers", [])

        cards = ft.Column(spacing=10)

        # Ayato Cloud (Managed Gateway)
        is_cloud_locked = "ayato_cloud" not in allowed
        cards.controls.append(
            self._create_card(
                "Ayato Cloud (推奨・マネージド)",
                [ft.Text("APIキー不要で Gemini 等の最新モデルを利用可能", size=12, italic=True)],
                disabled=is_cloud_locked,
                badge_text="MANAGED" if not is_cloud_locked else "PRO ONLY",
            )
        )

        # Google Gemini
        is_gemini_locked = "gemini" not in allowed
        cards.controls.append(
            self._create_card(
                "Google Gemini (BYOK)", [self.gemini_api_key], disabled=is_gemini_locked, badge_text="PRO / BYOK" if is_gemini_locked else "BYOK"
            )
        )

        # Ollama Local
        cards.controls.append(self._create_card("Ollama Local (ローカル・Gemmaなど)", [self.ollama_local_url]))

        # Ollama Cloud
        is_ollama_cloud_locked = "ollama_cloud" not in allowed
        cards.controls.append(
            self._create_card(
                "Ollama Cloud (API利用)",
                [self.ollama_cloud_api_key, self.ollama_cloud_url],
                disabled=is_ollama_cloud_locked,
                badge_text="PRO / ENTERPRISE" if is_ollama_cloud_locked else None,
            )
        )

        return cards

    def _on_cloud_token_change(self, e):
        self.config_mgr.set_cloud_token(self.cloud_token.value)

    def _on_activate_click(self, e):
        # Trigger re-render of providers based on new token validation
        # ConfigManager.get_edition() will handle the logic
        self.controls[11] = self._create_provider_cards()  # Replace provider cards row
        self.update()

        edition = self.config_mgr.get_edition()
        if edition != AppEdition.FREE:
            self._show_info(f"アクティベーション成功: {edition.name} エディションが有効です。")
        else:
            self._show_info("無効なトークンです。再度ご確認ください。", bgcolor=ft.Colors.RED_700)

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

    def init_view(self):
        self.cloud_token.value = self.config_mgr.get_cloud_token()

        gemini_conf = self.config_mgr.get_provider_config("gemini")
        self.gemini_api_key.value = gemini_conf.get("api_key", "")

        ollama_local_conf = self.config_mgr.get_provider_config("ollama_local")
        self.ollama_local_url.value = ollama_local_conf.get("base_url", "http://localhost:11434")

        ollama_cloud_conf = self.config_mgr.get_provider_config("ollama_cloud")
        self.ollama_cloud_api_key.value = ollama_cloud_conf.get("api_key", "")
        self.ollama_cloud_url.value = ollama_cloud_conf.get("base_url", "https://ollama.com")

        self.force_gpu_checkbox.value = self.config_mgr.get_force_gpu()

        # Load and update projects list
        self._update_project_options()

        if self.page:
            self.update()

    def _on_export_logs_click(self, e):
        log_file = get_log_path()
        if not os.path.exists(log_file):
            self._show_info("ログファイルが見つかりません。")
            return

        try:
            # Clipboard fallback for debugging
            with open(log_file, encoding="utf-8") as f:
                content = f.read()

            self.page.set_clipboard(content)
            self._show_info("ログをクリップボードにコピーしました。")
            logger.info(f"Log exported from: {log_file}")

        except Exception as ex:
            logger.error(f"Failed to export logs: {ex}")
            self._show_info(f"ログ出力失敗: {ex}")

    def _show_info(self, text: str, bgcolor: str = None):
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=bgcolor)
            self.page.snack_bar.open = True
            self.page.update()
