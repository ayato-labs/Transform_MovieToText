import logging

from google import genai
from google.genai import types

from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)

class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API via google-genai SDK."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API Key is required.")
        self.client = genai.Client(api_key=api_key)
        self._model_name = "gemini-2.0-flash" # Default model

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        """Generates structured minutes using Gemini API."""
        logger.info(f"GeminiClient: Generating minutes for model={model_name}, transcript_len={len(transcript)}")
        
        try:
            prompt = (
                "以下の文字起こしテキストを元に、構造化された議事録をMarkdown形式で作成してください。\n"
                "項目は「会議の概要」「決定事項」「ネクストアクション」を含めて、適切なヘッダーやリスト(# や -)を使用してください。\n\n"
                f"--- 文字起こしテキスト ---\n{transcript}"
            )
            
            contents = [prompt]
            
            # Add visual context if provided
            if visual_contexts:
                logger.debug(f"GeminiClient: Attaching {len(visual_contexts)} images.")
                for ctx in visual_contexts:
                    img_path = ctx.get("image_path")
                    if img_path:
                        import os
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

            response = self.client.models.generate_content(
                model=model_name or self._model_name,
                contents=contents
            )
            
            return response.text
        except Exception as e:
            logger.exception(f"Gemini API generation failed: {e}")
            raise RuntimeError(f"Gemini API Error: {str(e)}") from e

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category using Gemini API."""
        try:
            prompt = (
                "以下のテキストの内容から、最も適切なカテゴリを1つから3つのキーワードで答えてください。"
                "例: 技術会議, 営業進捗, デザインレビュー\n\n"
                f"内容: {transcript[:2000]}"
            )
            response = self.client.models.generate_content(
                model=model_name or self._model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception:
            logger.exception("Gemini category extraction failed.")
            return "未分類"

    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a title using Gemini API."""
        try:
            prompt = (
                "以下のテキストの内容を簡潔に表すタイトルを1行で作成してください。\n\n"
                f"内容: {transcript[:2000]}"
            )
            response = self.client.models.generate_content(
                model=model_name or self._model_name,
                contents=prompt
            )
            return response.text.strip().replace('"', '')
        except Exception:
            logger.exception("Gemini title generation failed.")
            return "無題の会議"

    def get_available_models(self) -> list[str]:
        """Returns standard Gemini models."""
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
