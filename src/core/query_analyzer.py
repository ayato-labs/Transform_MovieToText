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

    def __init__(self, projects: list[str], categories: list[str], config_mgr: ConfigManager = None, provider: str = None, model: str = None, client=None):
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

        # Initialize LLM Client via Factory OR use provided client (DI)
        if client:
            self.client = client
            logger.info(f"QueryAnalyzer: Initialized with provided client ({self.model_id})")
        else:
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

        # 1. Direct Substring and Synonym Matching (Crucial for Japanese/Non-spaced text)
        for proj in self.projects:
            if proj.lower() in search_pool.lower():
                found_projects.add(proj)
        
        for cat in self.categories:
            if cat.lower() in search_pool.lower():
                found_categories.add(cat)

        for syn_key, syn_val in self.SYNONYMS.items():
            if syn_key in search_pool:
                if syn_val in self.categories:
                    found_categories.add(syn_val)
                elif syn_val in self.projects:
                    found_projects.add(syn_val)

        # 2. Token-based and Fuzzy Matching
        words = re.findall(r"[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-]+", search_pool)
        
        for word in words:
            if len(word) < 2:
                continue
            
            # Fuzzy Matching (FTS-friendly)
            if word not in found_projects and word not in found_categories:
                p_match = difflib.get_close_matches(word, self.projects, n=1, cutoff=0.8)
                if p_match:
                    found_projects.add(p_match[0])
                    continue

                t_match = difflib.get_close_matches(word, self.categories, n=1, cutoff=0.8)
                if t_match:
                    found_categories.add(t_match[0])
                    continue

        # 3. Keyword extraction
        # Physically remove identified metadata and synonyms from the query to isolate keywords
        exclude_set = found_projects | found_categories
        
        clean_pool = search_pool
        # Sort by length descending to replace longer phrases first
        for meta in sorted(list(exclude_set), key=len, reverse=True):
            clean_pool = clean_pool.replace(meta, " ")
        
        # Also remove synonym keys
        for syn_key in sorted(list(self.SYNONYMS.keys()), key=len, reverse=True):
            clean_pool = clean_pool.replace(syn_key, " ")

        # Now extract tokens from the cleaned pool
        tokens = re.findall(r"[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-]+", clean_pool)
        
        keywords = []
        for t in tokens:
            if 2 <= len(t) <= 15:
                keywords.append(t)

        # If still no keywords, split original query by punctuation as last resort
        if not keywords:
            parts = re.split(r"[、。！？\s]", original_query)
            for p in parts:
                if 2 <= len(p) <= 15:
                    keywords.append(p)

        return {
            "projects": sorted(found_projects),
            "categories": sorted(found_categories),
            "keywords": sorted(list(set(keywords))[:8]),
        }
