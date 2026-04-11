import difflib
import logging
import re

from src.core.config_manager import ConfigManager
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes user queries to extract metadata (projects, categories) and keywords
    using a 'Ultra-Minimal' strategy optimized for local 1B-8B parameter models.
    """

    # Common Japanese synonyms for standardization
    SYNONYMS = {
        "サマリー": "Minutes",
        "要約": "Minutes",
        "議事録": "Minutes",
        "不具合": "Bug-Report",
        "バグ": "Bug-Report",
        "エラー": "Bug-Report",
        "戦略": "Strategy",
        "ストラテジー": "Strategy",
        "目標": "Strategy",
        "宿題": "Action-Items",
        "アクション": "Action-Items",
        "採用": "Recruitment",
        "リクルー": "Recruitment",
        "アヤト": "Ayato-AI",
        "あやと": "Ayato-AI",
        "マーケット": "Marketing-Promotion",
        "マーケ": "Marketing-Promotion",
    }

    def __init__(self, projects: list[str], categories: list[str], config_mgr: ConfigManager = None, provider: str = None, model: str = None):
        self.projects = projects
        self.categories = categories
        self.config_mgr = config_mgr or ConfigManager()

        # Determine provider and model
        self.active_provider = provider or self.config_mgr.get_active_provider()
        
        # If model is not provided, try to get the last used model for that provider
        if not model:
            p_conf = self.config_mgr.get_provider_config(self.active_provider)
            self.model_id = p_conf.get("model")
        else:
            self.model_id = model

        # Initialize LLM Client via Factory
        try:
            p_conf = self.config_mgr.get_provider_config(self.active_provider)
            self.client = LLMFactory.create_client(
                provider_name=self.active_provider,
                api_key=p_conf.get("api_key"),
                base_url=p_conf.get("base_url")
            )
            logger.info(f"QueryAnalyzer: Initialized with {self.active_provider} ({self.model_id})")
        except Exception as e:
            logger.error(f"QueryAnalyzer: Failed to initialize LLM client: {e}")
            self.client = None

    def analyze(self, query: str) -> dict:
        """
        Extracts metadata candidates using LLM and reconciles them with system data.
        """
        if not self.client or not self.model_id:
            logger.warning("QueryAnalyzer: No LLM client or model configured. Falling back to keyword-only search.")
            return {"projects": [], "categories": [], "keywords": [query]}

        # 1. Get raw candidates from model (Ultra-Minimal Bullet-point prompt)
        raw_output = self._get_llm_candidates(query)

        # 2. Parse and reconcile using code-based logic
        return self._reconcile(raw_output, query)

    def _get_llm_candidates(self, query: str) -> str:
        prompt = f"""
以下の質問を読み、関係する【プロジェクト名】や【カテゴリー名】を、提示されたリストの中からすべて抜き出して答えなさい。
リストにないものは無視してください。

【プロジェクト名リスト】
{self.projects}

【カテゴリー名リスト】
{self.categories}

質問: {query}
答え:
"""
        try:
            # Using generate instead of chat to handle simple completions or single-turn prompts
            # This works for both Ollama and Gemini via our wrappers
            return self.client.generate(prompt=prompt, model_name=self.model_id)
        except Exception as e:
            logger.error(f"Error during intent extraction: {e}")
            return ""

    def _reconcile(self, raw_text: str, original_query: str) -> dict:
        """
        Aggregates original query, raw text, and system lists into a clean match.
        """
        # Combine raw text and original query for parsing
        search_pool = f"{raw_text}\n{original_query}"

        found_projects = set()
        found_categories = set()

        # 1. Direct and Synonym Matching
        # Split into alphanumeric/cjk words to check against dictionary
        words = re.findall(r"[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-]+", search_pool)

        for word in words:
            if len(word) < 2:
                continue

            # Check Synonyms
            normalized = self.SYNONYMS.get(word, word)

            # Match Projects
            if normalized in self.projects:
                found_projects.add(normalized)
                continue

            # Match Categories
            if normalized in self.categories:
                found_categories.add(normalized)
                continue

            # 2. Fuzzy Matching (FTS-friendly)
            p_match = difflib.get_close_matches(normalized, self.projects, n=1, cutoff=0.7)
            if p_match:
                found_projects.add(p_match[0])
                continue

            t_match = difflib.get_close_matches(normalized, self.categories, n=1, cutoff=0.7)
            if t_match:
                found_categories.add(t_match[0])
                continue

        # 3. Keyword extraction (Fall back to query words if nothing meaningful found)
        # We strip out matched metadata from keywords
        keywords = []
        for word in words:
            # Avoid long sentence-like 'words' and already identified metadata
            if 2 <= len(word) <= 15 and word not in found_projects and word not in found_categories:
                keywords.append(word)

        # If no keywords extracted, or they are too generic, try splitting by common Japanese particles/punctuations
        if not keywords:
            # Simple split by punctuation as a fallback
            parts = re.split(r"[、。！？\s]", original_query)
            for p in parts:
                if 2 <= len(p) <= 10:
                    keywords.append(p)

        return {
            "projects": sorted(found_projects),
            "categories": sorted(found_categories),
            "keywords": sorted(list(set(keywords))[:8]),
        }
