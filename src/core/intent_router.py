import json
import logging
from enum import Enum

from src.core.config_manager import ConfigManager
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class TransformationStrategy(Enum):
    MINUTES = "minutes"  # 議事録
    ACTION_ITEMS = "tasks"  # タスク抽出
    FAQ = "faq"  # FAQ作成
    SPEC = "spec"  # 技術仕様書
    ARTICLE = "article"  # 記事・ブログ
    CLEAN = "clean"  # 清書・要約


class IntentRouter:
    """
    Analyzes transcript content to recommend the best transformation strategy.
    Uses uniform LLM client interface for cross-provider compatibility.
    """

    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr

    def route(self, transcript: str, provider: str, model: str) -> dict:
        """
        Determines the intent and returns a recommended strategy.
        Returns: {"strategy": TransformationStrategy, "reason": str, "confidence": float}
        """
        if not transcript:
            return {"strategy": TransformationStrategy.CLEAN, "reason": "Empty content", "confidence": 1.0}

        conf = self.config_mgr.get_provider_config(provider)
        client = LLMFactory.create_client(provider_name=provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))

        system_prompt = (
            "あなたはプロのコンテンツ分析AIです。提供された文字起こしテキストを読み、"
            "最も適切な変換(アウトプット)形式を1つ選んでください。\n\n"
            "選択肢:\n"
            "- minutes: 会議や打ち合わせの記録。決定事項や経緯が重要な場合。\n"
            "- tasks: アクションアイテムや誰が何をいつまでにやるかというタスク管理が主眼の場合。\n"
            "- faq: 知識の共有、質問と回答のやり取り、ナレッジベース化が主な目的の場合。\n"
            "- spec: 技術的な議論、設計、アルゴリズム、ロジックの構築が含まれる場合。\n"
            "- article: ストーリー性がある、一般向けに読ませる記事、ブログ、レポートに適している場合。\n"
            "- clean: 上記に当てはまらない汎用的な要約や、単なる「話し言葉の清書」の場合。\n\n"
            "### 厳格な出力ルール:\n"
            "1. JSON形式のみを出力してください。\n"
            "2. 前置き、挨拶、まとめ、考察などは一切含めないでください。\n"
            "3. 文字起こしの内容そのものを要約しないでください。分類のみを行ってください。\n"
            "4. フォーマットは以下の通りです:\n"
            '{"strategy": "キーワード", "reason": "分類した理由", "confidence": 0.9}'
        )

        try:
            # Analyze a sample to save context window
            sample_text = transcript[:4000]

            # Use unified transform() method (Safe for Gemini and Ollama)
            raw_output = client.transform(transcript=f"文字起こしテキスト:\n{sample_text}", model_name=model, system_instruction=system_prompt)

            if not raw_output:
                logger.error("Intent routing failed: LLM returned empty output.")
                return {"strategy": TransformationStrategy.CLEAN, "reason": "LLM returned empty output", "confidence": 0.0}

            # Defensive JSON extraction
            raw_json = raw_output.strip()
            
            # Remove Markdown code blocks if present
            if "```" in raw_json:
                import re
                match = re.search(r"\{.*\}", raw_json, re.DOTALL)
                if match:
                    raw_json = match.group(0)
            
            # Further strip everything before { and after }
            if "{" in raw_json and "}" in raw_json:
                start = raw_json.find("{")
                end = raw_json.rfind("}") + 1
                raw_json = raw_json[start:end]

            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError as jde:
                # LLM ignored JSON instruction and returned natural language summary (as seen in the error log)
                # We log this and fallback to CLEAN/MINUTES based on text presence
                logger.warning(f"Intent routing: LLM returned text instead of JSON. Falling back to CLEAN. Output head: {raw_output[:200]}...")
                return {"strategy": TransformationStrategy.CLEAN, "reason": "Failed to parse JSON, falling back to default clean summary", "confidence": 0.0}

            strategy_key = str(data.get("strategy", "clean")).lower()

            # Map string to Enum
            strategy_map = {s.value: s for s in TransformationStrategy}
            strategy = strategy_map.get(strategy_key, TransformationStrategy.CLEAN)

            logger.info(f"Intent detected: {strategy.name} (Conf: {data.get('confidence')})")
            return {"strategy": strategy, "reason": data.get("reason", "No reason provided"), "confidence": data.get("confidence", 0.0)}
        except Exception as e:
            logger.error(f"Intent routing failed: {e}", exc_info=True)
            return {"strategy": TransformationStrategy.CLEAN, "reason": f"Classification error: {e}", "confidence": 0.0}
