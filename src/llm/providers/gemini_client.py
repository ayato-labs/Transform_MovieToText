import logging
import os
import time

from google import genai
from google.genai import types
from PIL import Image

from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key, **kwargs):
        self.client = genai.Client(api_key=api_key)
        logger.info("GeminiLLMClient initialized.")

    def get_available_models(self) -> list[str]:
        """Fetches and filters Gemini models. Returns an empty list on error instead of raising."""
        try:
            logger.info("Fetching available Gemini models...")
            start_time = time.time()
            models = self.client.models.list()
            duration = time.time() - start_time

            filtered_models = []
            for m in models:
                if any(x in m.name.lower() for x in ["gemini", "gemma"]):
                    actions = getattr(m, "supported_actions", [])
                    if "generate_content" in actions or "generateContent" in actions or not actions:
                        name = m.name.replace("models/", "")
                        filtered_models.append(name)

            result = sorted(filtered_models, reverse=True)
            logger.info(f"Successfully fetched {len(result)} models in {duration:.2f}s.")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch Gemini models (Possible API Key issue): {e}")
            # Return empty list instead of raising to allow app to continue booting
            return []

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        """Generates meeting minutes using Gemini, with optional multimodal context."""
        logger.info(f"Generating minutes using Gemini model: {model_name} (Visual Contexts: {len(visual_contexts) if visual_contexts else 0})...")

        system_instruction = (
            "あなたはプロの書記です。提供された音声の文字起こしテキストと、会議中のスクリーンショット画像（タイムスタンプ付き）を組み合わせて、"
            "非常に詳細で正確なMarkdown形式の議事録を作成してください。\n"
            "画像にはスライドやデモ、ホワイトボードの内容が含まれている可能性があるため、それらを「視覚情報」として議事録の内容に反映させてください。\n"
            "項目は「会議の概要」「詳細内容（視覚情報を含む）」「決定事項」「ネクストアクション」を含めてください。"
        )

        contents = []

        # 1. Add Visual Contexts if available
        if visual_contexts:
            contents.append("以下は会議中にキャプチャされた視覚的なコンテキストです：\n")
            for ctx in visual_contexts:
                img_path = ctx.get("image_path")
                ts = ctx.get("timestamp_sec", 0)
                if img_path and os.path.exists(img_path):
                    try:
                        img = Image.open(img_path)
                        contents.append(f"--- タイムスタンプ: {ts:.1f}秒のスクリーンショット ---")
                        contents.append(img)
                    except Exception as e:
                        logger.warning(f"Failed to load image {img_path}: {e}")

        # 2. Add Transcript
        contents.append(f"\n--- 音声文字起こしテキスト ---\n{transcript}")

        try:
            start_time = time.time()
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                ),
            )
            duration = time.time() - start_time
            logger.info(f"Minutes generated successfully by Gemini in {duration:.2f}s.")
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return f"⚠️ Minutes generation failed. Please check your Gemini API key in Settings.\nError: {e}"

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category/label (1-3 keywords) from the transcript."""
        logger.info(f"Extracting category using Gemini model: {model_name}...")

        prompt = (
            "以下の文字起こしテキストから、その内容を最もよく表す1〜3個の日本語キーワード、または"
            "短いカテゴリー名（例：AI技術, プロジェクト進捗, 顧客ヒアリング）を抽出してください。\n"
            "出力はキーワードのみ（カンマ区切り）とし、余計な説明は一切含めないでください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Low temperature for more consistent labels
                ),
            )
            category = response.text.strip().replace("\n", "")
            logger.info(f"Extracted category: {category}")
            return category
        except Exception as e:
            logger.error(f"Gemini category extraction failed: {e}")
            return "未分類"  # Fallback

    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a concise meeting title using Gemini."""
        logger.info(f"Generating title using Gemini model: {model_name}...")
        prompt = (
            "以下の文字起こしテキストの内容を要約し、非常に簡潔で分かりやすい「会議のタイトル」を1つ生成してください。\n"
            "タイトルは20文字以内とし、余計な説明や記号、前置き（例：「タイトルは〜」）は一切含めないでください。タイトルのみを出力してください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=types.GenerateContentConfig(temperature=0.5),
            )
            title = response.text.strip().replace("\n", "").replace("#", "")
            logger.info(f"Generated title: {title}")
            return title
        except Exception as e:
            logger.error(f"Gemini title generation failed: {e}")
            return "タイトルなし"

    def transform(self, transcript: str, model_name: str, system_instruction: str, visual_contexts: list = None) -> str:
        """Overridden transform to use Gemini's native multimodal and system_instruction features."""
        contents = []
        if visual_contexts:
            for ctx in visual_contexts:
                img_path = ctx.get("image_path")
                if img_path and os.path.exists(img_path):
                    img = Image.open(img_path)
                    contents.append(img)

        contents.append(transcript)

        response = self.client.models.generate_content(
            model=model_name, contents=contents, config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.7)
        )
        return response.text

    def chat(self, model_name: str, messages: list[dict]) -> str:
        """Sends a list of messages to Gemini."""
        # Convert roles (UI uses 'user'/'assistant', Gemini uses 'user'/'model')
        gemini_messages = []
        for m in messages:
            role = "model" if m["role"] in ["assistant", "model", "bot"] else "user"
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})

        try:
            response = self.client.models.generate_content(
                model=model_name, contents=gemini_messages, config=types.GenerateContentConfig(temperature=0.7)
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini chat failed: {e}")
            return f"⚠️ Chat failed. (API Key error?)\nError: {e}"
