import logging

from ollama import Client

from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaLocalClient(BaseLLMClient):
    """Client for local Ollama instance."""

    def __init__(self, base_url="http://localhost:11434", **kwargs):
        self.host = base_url
        self.client = Client(host=self.host)

    def get_available_models(self) -> list[str]:
        try:
            models_info = self.client.list()
            model_names = []

            # 1. Handle ListResponse/Object shape (Standard for newer SDK)
            if hasattr(models_info, "models"):
                for m in models_info.models:
                    if hasattr(m, "model"):
                        model_names.append(m.model)
                    elif hasattr(m, "name"):
                        model_names.append(m.name)
                    elif isinstance(m, dict):
                        model_names.append(m.get("model") or m.get("name"))

            # 2. Handle Dictionary shape (Standard for older SDK or direct API)
            elif isinstance(models_info, dict) and "models" in models_info:
                for m in models_info["models"]:
                    if isinstance(m, dict):
                        name = m.get("name") or m.get("model")
                        if name:
                            model_names.append(name)

            if model_names:
                return sorted(set(model_names))

            logger.warning(f"Ollama Local: No models found or unknown format: {type(models_info)}")
            return []
        except Exception as e:
            logger.error(f"Failed to list local Ollama models: {e}")
            return []

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        prompt = (
            "以下の文字起こしテキストを元に、構造化された議事録をMarkdown形式で作成してください。\n"
            "項目は「会議の概要」「決定事項」「ネクストアクション」を含めて、適切なヘッダーやリスト（# や -）を使用してください。\n\n"
        )
        images = []
        if visual_contexts:
            import base64
            import os

            for ctx in visual_contexts:
                img_path = ctx.get("image_path")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        images.append(base64.b64encode(f.read()).decode("utf-8"))

        prompt += f"--- 文字起こしテキスト ---\n{transcript}"
        try:
            # Pass images to ollama chat if any
            msg = {"role": "user", "content": prompt}
            if images:
                msg["images"] = images
            response = self.client.chat(model=model_name, messages=[msg])
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama local generation failed: {e}")
            raise RuntimeError(f"Failed to generate minutes: {str(e)}") from e

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category/label (1-3 keywords) from the transcript."""
        prompt = (
            "以下の文字起こしテキストから、その内容を最もよく表す1〜3個の日本語キーワード、または"
            "短いカテゴリー名（例：AI技術, プロジェクト進捗, 顧客ヒアリング）を抽出してください。\n"
            "出力はキーワードのみ（カンマ区切り）とし、余計な説明は一切含めないでください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"].strip().replace("\n", "")
        except Exception as e:
            logger.error(f"Ollama category extraction error: {e}")
            return "未分類"

    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a concise meeting title using Ollama."""
        prompt = (
            "以下の文字起こしテキストの内容を要約し、非常に簡潔で分かりやすい「会議のタイトル」を1つ生成してください。\n"
            "タイトルは20文字以内とし、タイトルのみを出力してください。余計な説明は不要です。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"].strip().replace("\n", "").replace("#", "")
        except Exception as e:
            logger.error(f"Ollama title generation error: {e}")
            return "タイトルなし"

    def generate(self, prompt, model_name, system_prompt=None):
        """Legacy/Internal helper for direct generation."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.client.chat(model=model_name, messages=messages)["message"]["content"]


class OllamaCloudClient(BaseLLMClient):
    """Client for Ollama Cloud API (Pattern 2)."""

    def __init__(self, api_key="", base_url="https://ollama.com", **kwargs):
        self.host = base_url
        self.api_key = api_key

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = Client(host=self.host, headers=headers)

    def get_available_models(self) -> list[str]:
        # Cloud might have a fixed set if listing fails
        try:
            models_info = self.client.list()
            model_names = []

            # Same robust check as local
            if hasattr(models_info, "models"):
                for m in models_info.models:
                    model_names.append(getattr(m, "model", getattr(m, "name", None)))
            elif isinstance(models_info, dict) and "models" in models_info:
                for m in models_info["models"]:
                    model_names.append(m.get("name") or m.get("model"))

            model_names = [m for m in model_names if m]
            if model_names:
                return sorted(set(model_names))

            return ["gpt-oss:120b"]
        except Exception as e:
            logger.warning(f"Failed to fetch models from Ollama Cloud: {e}")
            return ["gpt-oss:120b"]

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        prompt = (
            "以下の文字起こしテキストを元に、構造化された議事録をMarkdown形式で作成してください。\n"
            "項目は「会議の概要」「決定事項」「ネクストアクション」を含めて、適切なヘッダーやリスト（# や -）を使用してください。\n\n"
        )
        images = []
        if visual_contexts:
            import base64
            import os

            for ctx in visual_contexts:
                img_path = ctx.get("image_path")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        images.append(base64.b64encode(f.read()).decode("utf-8"))

        prompt += f"--- 文字起こしテキスト ---\n{transcript}"
        try:
            msg = {"role": "user", "content": prompt}
            if images:
                msg["images"] = images
            response = self.client.chat(model=model_name, messages=[msg])
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama Cloud generation error: {e}")
            raise

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category/label (1-3 keywords) from the transcript."""
        prompt = (
            "以下の文字起こしテキストから、その内容を最もよく表す1〜3個の日本語キーワード、または"
            "短いカテゴリー名（例：AI技術, プロジェクト進捗, 顧客ヒアリング）を抽出してください。\n"
            "出力はキーワードのみ（カンマ区切り）とし、余計な説明は一切含めないでください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"].strip().replace("\n", "")
        except Exception as e:
            logger.error(f"Ollama category extraction error: {e}")
            return "未分類"

    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a concise meeting title using Ollama Cloud."""
        prompt = (
            "以下の文字起こしテキストの内容を要約し、非常に簡潔で分かりやすい「会議のタイトル」を1つ生成してください。\n"
            "タイトルは20文字以内とし、タイトルのみを出力してください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"].strip().replace("\n", "").replace("#", "")
        except Exception as e:
            logger.error(f"Ollama cloud title generation error: {e}")
            return "タイトルなし"

    def generate(self, prompt, model_name, system_prompt=None):
        """Legacy/Internal helper for direct generation."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.client.chat(model=model_name, messages=messages)["message"]["content"]
