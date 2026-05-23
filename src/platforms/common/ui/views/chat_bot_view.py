import logging
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.core.minutes_service import MinutesService
from src.core.query_analyzer import QueryAnalyzer
from src.platforms.common.ui.ui_utils import Debouncer
from src.platforms.desktop.controllers.local_smart_ctrl import LocalSmartController
from src.platforms.desktop.ui.local_smart_helper import LocalSmartUIHelper
from src.platforms.desktop.ui.ui_utils import sync_llm_models

logger = logging.getLogger(__name__)


class ChatMessage(ft.Row):
    def __init__(self, text: str, is_user: bool):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        avatar = ft.CircleAvatar(
            content=ft.Icon(ft.Icons.PERSON if is_user else ft.Icons.AUTO_AWESOME),
            bgcolor=ft.Colors.BLUE_900 if is_user else ft.Colors.AMBER_900,
        )
        self.controls = [
            avatar if is_user else None,
            ft.Column(
                [
                    ft.Text("USER" if is_user else "AIアシスタント", weight=ft.FontWeight.BOLD, size=12),
                    ft.Container(
                        content=ft.Text(text, selectable=True),
                        bgcolor=ft.Colors.BLACK26 if is_user else ft.Colors.BLUE_GREY_900,
                        padding=12,
                        border_radius=10,
                        width=500,
                    ),
                ],
                tight=True,
                expand=True,
            ),
            avatar if not is_user else None,
        ]
        # Filter out Nones
        self.controls = [c for c in self.controls if c]


class ChatBotView(ft.Column):
    """
    RAG-powered ChatBot View with Local Smart integration.
    Allows users to query their meeting history and local knowledge documents.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager):
        super().__init__(expand=True)
        self._page_ref = page
        self.config_mgr = config_mgr
        self.history_mgr = history_mgr
        self.minutes_service = MinutesService(config_mgr)
        self.local_smart_ctrl = LocalSmartController(config_mgr)
        self.hw_info = self._get_hw_info()

        # UI State
        self.search_debouncer = Debouncer(delay=0.5)

        # UI Components
        self.chat_history = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS, spacing=20)

        # Context Preview (Real-time feedback as typing)
        self.context_preview = ft.Row(spacing=10, scroll=ft.ScrollMode.ALWAYS, visible=False)

        self.input_field = ft.TextField(
            hint_text="文字起こしデータについて質問してください...",
            expand=True,
            on_submit=self._on_send_click,
            on_change=self._on_input_change,
            border_radius=20,
            bgcolor=ft.Colors.BLACK12,
        )

        # Project Selection
        self.dd_project = ft.Dropdown(
            label="対象プロジェクト",
            width=200,
            options=[ft.dropdown.Option("すべてのプロジェクト")],
            value="すべてのプロジェクト",
        )

        self.dd_llm = ft.Dropdown(
            label="LLMモデル",
            width=220,
            options=[ft.dropdown.Option("取得中...", disabled=True)],
            value=None,
            on_change=self._on_llm_change,
        )

        self.local_smart_btn = ft.IconButton(
            icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            selected_icon=ft.Icons.AUTO_AWESOME,
            on_click=self._toggle_local_smart,
            tooltip="Local Smart: ハードウェアに最適なモデルを選択",
            selected=self.config_mgr.get_local_smart_enabled(),
        )

        self.status_text = ft.Text("待機中...", size=12, color=ft.Colors.GREY_500)

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("AIチャット (RAG)", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("蓄積された文字起こしデータから、AIが質問に回答します (100% Local)", size=13, color=ft.Colors.GREEN_400),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(f"RAM: {self.hw_info['ram']}GB", size=10, color=ft.Colors.BLUE_200),
                                        ft.Text(f"VRAM: {self.hw_info['vram']}GB", size=10, color=ft.Colors.PURPLE_200),
                                    ],
                                    spacing=0,
                                ),
                                padding=ft.padding.only(right=10),
                            ),
                            self.dd_project,
                            self.dd_llm,
                            self.local_smart_btn,
                        ],
                        spacing=10,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            self.status_text,
            ft.Container(
                content=self.chat_history,
                expand=True,
                padding=20,
                bgcolor=ft.Colors.BLACK26,
                border_radius=15,
            ),
            ft.Column(
                [
                    self.context_preview,
                    ft.Row(
                        [
                            self.input_field,
                            ft.FloatingActionButton(
                                icon=ft.Icons.SEND_ROUNDED,
                                on_click=self._on_send_click,
                                bgcolor=ft.Colors.BLUE_700,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=5,
            ),
        ]

        # Initialize Shared Helper
        self.smart_helper = LocalSmartUIHelper(
            config_mgr,
            self.local_smart_ctrl,
            None, # No provider dropdown in this view
            self.dd_llm,
            self.status_text,
            local_smart_btn=self.local_smart_btn
        )

        # Initial data load
        threading.Thread(target=self._initial_load_task, daemon=True).start()

    def _get_hw_info(self):
        import psutil
        import torch

        ram = round(psutil.virtual_memory().total / (1024**3), 1)
        vram = 0.0
        if torch.cuda.is_available():
            vram = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
        return {"ram": ram, "vram": vram}

    def _safe_update(self):
        """Updates the component safely, ensuring it is attached to a page."""
        try:
            if self.page and getattr(self, "_Control__uid", None) is not None:
                self.update()
        except Exception as e:
            logger.debug(f"ChatBotView: Skipping update: {e}")

    def _initial_load_task(self):
        # Update project list
        self._update_project_options()
        # Handle smart optimization
        self.smart_helper.initial_load(self._update_model_options)
        self._safe_update()

    def _update_project_options(self):
        projects = self.history_mgr.get_projects()
        opts = [ft.dropdown.Option("すべてのプロジェクト")]
        for p in projects:
            if p:
                opts.append(ft.dropdown.Option(p))
        self.dd_project.options = opts
        self._safe_update()

    def _update_model_options(self, provider: str):
        sync_llm_models(self._page_ref, self.config_mgr, provider, self.dd_llm, self.status_text, on_empty_results=self._handle_empty_models)

    def _handle_empty_models(self, provider: str):
        logger.warning(f"ChatBotView: No models found for {provider}")
        self.dd_llm.options = [ft.dropdown.Option("モデルなし", disabled=True)]
        self._safe_update()

    def _on_llm_change(self, e):
        self.config_mgr.set_last_model(self.dd_llm.value)

    def _toggle_local_smart(self, e):
        self.smart_helper.toggle_smart(update_callback=self._update_model_options)

    def _on_send_click(self, e):
        query = self.input_field.value.strip()
        if not query:
            return

        logger.info(f"ChatBotView: User sent query: {query}")
        self.chat_history.controls.append(ChatMessage(query, is_user=True))
        self.input_field.value = ""
        self.status_text.value = "AIが思考中..."
        self._safe_update()

        threading.Thread(target=self._run_rag_worker, args=(query,), daemon=True).start()

    def _run_rag_worker(self, query: str):
        try:
            # 1. Intent Analysis
            all_projs = self.history_mgr.get_projects()
            all_cats = self.history_mgr.get_categories()

            analyzer = QueryAnalyzer(all_projs, all_cats, config_mgr=self.config_mgr)
            intent = analyzer.analyze(query)

            # 2. Metadata-Filtered Search
            manual_filter = self.dd_project.value
            filter_projs = intent["projects"]
            if manual_filter and manual_filter != "すべてのプロジェクト":
                filter_projs = [manual_filter]

            search_text = " ".join(intent["keywords"]) if intent["keywords"] else query
            results = self.history_mgr.get_meetings_filtered(
                project_names=filter_projs, categories=intent["categories"], search_query=search_text, limit=5
            )

            # 3. Format Context
            context_blocks = []
            for r in results:
                title = r.get("title", "名称未設定のアイテム")
                timestamp = r.get("timestamp", "不明な日時")
                project = r.get("project_name") or "その他"
                category = r.get("category") or "未分類"
                s_type = r.get("source_type", "meeting")
                label = "Meeting" if s_type == "meeting" else "Document"

                content = r.get("minutes") or r.get("transcript", "")
                context_blocks.append(
                    f"### {label}: {title} ({timestamp})\n- Project: {project}\n- Tags: {category}\nContent: {content[:1000]}..."
                )

            context = "\n\n---\n\n".join(context_blocks) or "過去のデータに関連情報はありませんでした。"

            # 3. Enhanced Prompt
            system_prompt = (
                "あなたは、過去の会議履歴にアクセスできる専門アシスタントです。\n"
                "以下のコンテキスト情報を参考にして、日本語で詳しく回答してください。\n"
                f"[Context Info]\n{context}\n"
            )

            # 4. LLM Call
            provider = "ollama_local"
            llm_model = self.dd_llm.value
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]
            client = self.config_mgr.get_llm_client(provider)
            response = client.chat(model_name=llm_model, messages=messages)

            # 5. Append sources
            if results:
                source_bullets = [f"- {r.get('title')} ({r.get('timestamp')})" for r in results]
                response += "\n\n---\n**🔍 引用元:**\n" + "\n".join(source_bullets)

            self.chat_history.controls.append(ChatMessage(response, is_user=False))
            self.status_text.value = "回答完了"
            self._safe_update()
        except Exception as ex:
            logger.error(f"RAG Chat error: {ex}")
            self.chat_history.controls.append(ChatMessage(f"エラーが発生しました: {ex}", is_user=False))
            self.status_text.value = "エラー発生"
            self._safe_update()

    def _on_input_change(self, e):
        query = self.input_field.value.strip()
        if len(query) < 3:
            self.context_preview.visible = False
            self.context_preview.controls.clear()
            self._safe_update()
            return
        self.search_debouncer.run(self._update_context_preview)

    def _update_context_preview(self):
        query = self.input_field.value.strip()
        if not query: return
        try:
            all_projs = self.history_mgr.get_projects()
            all_cats = self.history_mgr.get_categories()
            analyzer = QueryAnalyzer(all_projs, all_cats, config_mgr=self.config_mgr)
            intent = analyzer.analyze(query)
            search_text = " ".join(intent["keywords"]) if intent["keywords"] else query
            results = self.history_mgr.get_meetings_filtered(
                project_names=intent["projects"], categories=intent["categories"], search_query=search_text, limit=3
            )
            self.context_preview.controls.clear()
            if results:
                self.context_preview.controls.append(ft.Text("🔍 関連:", size=10, color=ft.Colors.GREY_500))
                for r in results:
                    self.context_preview.controls.append(
                        ft.Container(
                            content=ft.Text(r.get("title", "無題"), size=10, color=ft.Colors.BLUE_200),
                            bgcolor=ft.Colors.BLUE_900 if r.get("minutes") else ft.Colors.BLUE_GREY_900,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border_radius=10,
                        )
                    )
                self.context_preview.visible = True
            else:
                self.context_preview.visible = False
            self._safe_update()
        except Exception as e:
            logger.debug(f"Context preview update failed: {e}")
