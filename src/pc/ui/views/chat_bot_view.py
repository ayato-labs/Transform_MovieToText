import logging
import threading

import flet as ft

from src.core.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.core.minutes_service import MinutesService
from src.core.query_analyzer import QueryAnalyzer
from src.pc.controllers.local_smart_ctrl import LocalSmartController

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
                    ft.Text("USER" if is_user else "AI助理", weight=ft.FontWeight.BOLD, size=12),
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
    Allows users to query their transcription knowledge base.
    """

    def __init__(self, page: ft.Page, config_mgr: ConfigManager):
        super().__init__(expand=True)
        # self.page is a property of ft.Control, cannot be set directly.
        # It will be set automatically when the control is added to a page.
        # For unit tests and immediate access, we can keep a local reference.
        self._page_ref = page
        self.config_mgr = config_mgr
        self.history_mgr = history_mgr
        self.minutes_service = MinutesService(config_mgr)
        self.local_smart_ctrl = LocalSmartController(config_mgr)
        self.hw_info = self._get_hw_info()
        self.local_smart_enabled = config_mgr.get_local_smart_enabled()

        # UI Components
        self.chat_history = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS, spacing=20)
        self.input_field = ft.TextField(
            hint_text="文字起こしデータについて質問してください...",
            expand=True,
            on_submit=self._on_send_click,
            border_radius=20,
            bgcolor=ft.Colors.BLACK12,
        )

        # Provider & Model Selection
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

        self.status_text = ft.Text("待機中...", size=12, color=ft.Colors.GREY_500)

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("AIチャット (RAG)", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("蓄積された文字起こしデータから、AIが質問に回答します", size=13, color=ft.Colors.GREY_500),
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
                            self.dd_provider,
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
        ]

        # Fetch models in background thread to avoid blocking UI
        threading.Thread(target=self._initial_load, daemon=True).start()

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
            # Flet controls have a private __uid attribute.
            # If it's None, the control isn't rendered yet.
            if self.page and getattr(self, "_Control__uid", None) is not None:
                self.update()
        except Exception as e:
            logger.debug(f"ChatBotView: Skipping update as control is not yet ready: {e}")

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
        actual_provider = "gemini" if provider == "google" else provider
        self.dd_llm.options = [ft.dropdown.Option("取得中...", disabled=True)]
        self.dd_llm.value = None
        self._safe_update()

        models = self.minutes_service.get_available_models(actual_provider)
        config = self.config_mgr.get_provider_config(provider)
        last_model = config.get("model")

        if models:
            self.dd_llm.options = [ft.dropdown.Option(m) for m in models]
            self.dd_llm.value = last_model if last_model in models else models[0]
        else:
            self.dd_llm.options = [ft.dropdown.Option("モデルなし", disabled=True)]
            self.dd_llm.value = None
        self._safe_update()

    def _toggle_local_smart(self, e):
        self.local_smart_enabled = not self.local_smart_enabled
        self.local_smart_btn.selected = self.local_smart_enabled
        self.config_mgr.set_local_smart_enabled(self.local_smart_enabled)

        if self.local_smart_enabled:
            self.local_smart_ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text)
        else:
            self.local_smart_ctrl.restore_manual_mode(self.dd_provider, self.dd_llm, self.status_text, update_callback=self._update_model_options)
        self._safe_update()

    def _apply_local_smart(self):
        self.local_smart_ctrl.apply_optimization(self.dd_provider, self.dd_llm, self.status_text)
        self._safe_update()

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
            # 1. Intent Analysis using 1B Model + Robust Parser
            all_projs = self.history_mgr.get_projects()
            all_cats = self.history_mgr.get_categories()

            analyzer = QueryAnalyzer(all_projs, all_cats)
            intent = analyzer.analyze(query)

            logger.info(f"RAG Intent Extracted: {intent}")

            # 2. Metadata-Filtered Search (Multi-filter)
            # Use extracted keywords for FTS5, scoped by projects/categories
            search_text = " ".join(intent["keywords"]) if intent["keywords"] else query
            results = self.history_mgr.get_meetings_filtered(
                project_names=intent["projects"], categories=intent["categories"], search_query=search_text, limit=5
            )

            # 3. Format Context with Metadata
            context_blocks = []
            for r in results:
                title = r.get("title", "名称未設定の会議")
                timestamp = r.get("timestamp", "不明な日時")
                project = r.get("project_name") or "その他"
                category = r.get("category") or "未分類"

                content_source = "Summary" if r.get("minutes") else "Transcript"
                content = r.get("minutes") if r.get("minutes") else r.get("transcript", "")

                context_blocks.append(
                    f"### Meeting: {title} ({timestamp})\n"
                    f"- Project: {project}\n"
                    f"- Tags: {category}\n"
                    f"- Source: {content_source}\n"
                    f"Content: {content[:1000]}..."  # Optimized context length
                )

            context = "\n\n---\n\n".join(context_blocks)

            if not context:
                logger.info("RAG: No relevant context found.")
                context = "過去の会議データに関連する情報は特に見つかりませんでした。"

            # 3. Enhance Prompt with the retrieved knowledge
            system_prompt = (
                "あなたは、過去の高度な会議履歴（文字起こし、要約、プロジェクト情報、AIタグ）にアクセスできる専門アシスタントです。\n"
                "以下のコンテキスト情報を参考にして、ユーザーの質問に日本語で詳しく回答してください。\n"
                "回答時には、必ず関連する『プロジェクト名』や『日付』に言及し、どの会議に基づいた情報かを明確にしてください。\n"
                "複数のプロジェクトを跨いだ質問の場合、それぞれの文脈を区別して整理して答えてください。\n"
                "もし情報が不十分な場合は、推測せず、その旨を伝えてください。\n\n"
                f"[Context Info]\n{context}\n"
            )

            # 4. Actual LLM Call with Context (Unified Chat Interface)
            provider = self.dd_provider.value
            llm_model = self.dd_llm.value

            # Build standardized message list
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

            conf = self.config_mgr.get_provider_config(provider)
            client = self.config_mgr.get_llm_client(provider, conf.get("api_key"))

            # Call using standardized 'messages' instead of incompatible 'message=' or 'system_instruction='
            response = client.chat(model_name=llm_model, messages=messages)

            # 5. Automatically append source information (Title / Project / Timestamp)
            if results:
                # Deduplicate sources based on title+timestamp
                seen_sources = set()
                source_bullets = []
                for r in results:
                    s_label = f"{r.get('title', '無題')} ({r.get('timestamp', '不明')})"
                    if s_label not in seen_sources:
                        source_bullets.append(f"- {s_label}")
                        seen_sources.add(s_label)

                if source_bullets:
                    source_footer = "\n\n---\n💡 **参考にした会議:**\n" + "\n".join(source_bullets)
                    response += source_footer

            self.chat_history.controls.append(ChatMessage(response, is_user=False))
            self.status_text.value = "回答完了 ✨"
            self._safe_update()
        except Exception as ex:
            logger.error(f"RAG Chat error: {ex}")
            self.chat_history.controls.append(ChatMessage(f"エラーが発生しました: {ex}", is_user=False))
            self.status_text.value = "エラー発生"
            self._safe_update()
