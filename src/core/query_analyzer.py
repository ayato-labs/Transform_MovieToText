import difflib
import logging
import os
import re

from dotenv import load_dotenv
from google import genai

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes user queries to extract metadata (projects, categories) and keywords
    using a 'Ultra-Minimal' strategy optimized for 1B parameter models.
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

    def __init__(self, projects: list[str], categories: list[str]):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        self.projects = projects
        self.categories = categories
        self.model_id = "gemma-3-1b-it"

    def analyze(self, query: str) -> dict:
        """
        Extracts metadata candidates using LLM and reconciles them with system data.
        """
        if not self.client:
            logger.warning("No Gemini API key found. Falling back to keyword-only search.")
            return {"projects": [], "categories": [], "keywords": [query]}

        # 1. Get raw candidates from 1B model (Ultra-Minimal Bullet-point prompt)
        raw_output = self._get_llm_candidates(query)

        # 2. Parse and reconcile using code-based logic
        return self._reconcile(raw_output, query)

    def _get_llm_candidates(self, query: str) -> str:
        prompt = f"""
以下の質問を読み、関係する【プロジェクト名】や【カテゴリー名】を、提示されたリストの中からすべて抜き出して答えなさい。

【プロジェクト名リスト】
{self.projects}

【カテゴリー名リスト】
{self.categories}

質問: {query}
答え:
"""
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return response.text
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
            "keywords": sorted(list(set(keywords))[:8]), # list(set(...))[:8] is fine to get slice first
        }
