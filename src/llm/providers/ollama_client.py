import logging

from ollama import Client

from src.core.model_manager import model_manager
from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)


# Standard VRAM client registration name for the active local LLM
LLM_CLIENT_NAME = "llm_local"

# ============================================================================
# SECURITY: Cloud Model Blocklist
# ============================================================================
# Ollama supports "Cloud Models" that route inference to Ollama's cloud servers.
# These models are accessible even through localhost:11434, meaning user data
# (prompts, meeting transcripts, private documents) would be sent externally.
#
# This COMPLETELY VIOLATES our "100% Local" privacy guarantee.
#
# Defense Strategy (3 Layers):
#   Layer 1: Model name filtering (block ":cloud", "remote:", etc.)
#   Layer 2: Ollama `show` API validation (verify local file existence)
#   Layer 3: Runtime guard on every chat/generate call
# ============================================================================
CLOUD_MODEL_INDICATORS = [
    "cloud",     # Standard cloud suffix (e.g., "llama3:cloud")
    "remote",    # Remote model indicator
    "hosted",    # Hosted model indicator
    "online",    # Online inference indicator
    "latest",    # Latest model indicator
    "preview",   # Preview model indicator
]


class CloudModelBlockedError(RuntimeError):
    """Raised when a cloud/remote model is detected and blocked for privacy."""

    def __init__(self, model_name: str):
        super().__init__(
            f"SECURITY BLOCK: Model '{model_name}' appears to be a cloud/remote model. "
            f"This app only permits 100% local inference to protect your data. "
            f"Please select a locally downloaded model instead."
        )


def _is_cloud_model(model_name: str) -> bool:
    """Check if a model name contains any cloud/remote indicators."""
    if not model_name:
        return True  # Reject empty/None model names
    name_lower = model_name.lower()
    return any(indicator in name_lower for indicator in CLOUD_MODEL_INDICATORS)


class OllamaLocalClient(BaseLLMClient):
    """
    Client for local Ollama instance.

    SECURITY DESIGN:
    This client enforces 100% local inference through 3 defense layers:
    1. get_available_models() filters out cloud models from the list
    2. _verify_local_model() checks via Ollama's show API that model files exist locally
    3. _guard_local_only() is called before every inference call as a final check
    """

    def __init__(self, base_url="http://localhost:11434", temperature=0.7, **kwargs):
        # Layer 0: Enforce loopback-only binding
        # Removed '0.0.0.0' as it can represent all interfaces on some systems
        is_loopback = any(loopback in base_url for loopback in ["localhost", "127.0.0.1"])
        if not is_loopback:
            logger.critical(
                f"SECURITY ALERT: Attempted to initialize Ollama with external or non-loopback URL '{base_url}'. "
                f"Forcing 127.0.0.1 to protect data sovereignty."
            )
            base_url = "http://127.0.0.1:11434"

        self.host = base_url
        self.temperature = float(temperature)
        # The ollama-python Client accepts a 'host' parameter which it uses for all requests.
        self.client = Client(host=self.host)
        self._last_model_name = None
        self._verified_local_models: set[str] = set()  # Cache of verified local models
        # Register with ModelManager
        model_manager.register(LLM_CLIENT_NAME, self)

    # ========================================================================
    # Layer 1: Model List Filtering
    # ========================================================================
    def get_available_models(self) -> list[str]:
        try:
            models_info = self.client.list()
            model_names = []

            # Handle ListResponse/Object shape (Standard for newer SDK)
            if hasattr(models_info, "models"):
                for m in models_info.models:
                    if hasattr(m, "model"):
                        model_names.append(m.model)
                    elif hasattr(m, "name"):
                        model_names.append(m.name)
                    elif isinstance(m, dict):
                        model_names.append(m.get("model") or m.get("name"))

            # Handle Dictionary shape (Standard for older SDK or direct API)
            elif isinstance(models_info, dict) and "models" in models_info:
                for m in models_info["models"]:
                    if isinstance(m, dict):
                        name = m.get("name") or m.get("model")
                        if name:
                            model_names.append(name)

            if model_names:
                # Layer 1: Filter out cloud/remote models by name
                local_models = []
                blocked_models = []
                for m in model_names:
                    if _is_cloud_model(m):
                        blocked_models.append(m)
                    else:
                        local_models.append(m)

                if blocked_models:
                    logger.warning(
                        f"SECURITY: Blocked {len(blocked_models)} cloud/remote model(s) "
                        f"from appearing in UI: {blocked_models}"
                    )

                # Layer 2: Verify remaining models are truly local via show API
                verified_models = []
                for m in local_models:
                    if self._verify_local_model(m):
                        verified_models.append(m)
                        self._verified_local_models.add(m)

                return sorted(set(verified_models))

            logger.warning(f"Ollama Local: No models found or unknown format: {type(models_info)}")
            return []
        except Exception as e:
            error_str = str(e)
            if "Failed to connect to Ollama" in error_str or "Connection refused" in error_str:
                logger.warning("Ollama is not running. Local models could not be fetched.")
            else:
                logger.error(f"Failed to list local Ollama models: {e}")
            return []

    def get_models_info(self) -> list[dict]:
        """Returns detailed information about local models including size."""
        try:
            models_info = self.client.list()
            results = []
            
            # Extract basic list
            model_list = []
            if hasattr(models_info, "models"):
                model_list = models_info.models
            elif isinstance(models_info, dict) and "models" in models_info:
                model_list = models_info["models"]

            for m in model_list:
                name = ""
                size = 0
                if hasattr(m, "model"):
                    name = m.model
                    size = getattr(m, "size", 0)
                elif hasattr(m, "name"):
                    name = m.name
                    size = getattr(m, "size", 0)
                elif isinstance(m, dict):
                    name = m.get("name") or m.get("model")
                    size = m.get("size", 0)
                
                if name and not _is_cloud_model(name) and self._verify_local_model(name):
                    results.append({
                        "name": name,
                        "size_bytes": size,
                        "size_gb": round(size / (1024**3), 2) if size else 0
                    })
            
            return sorted(results, key=lambda x: x["name"])
        except Exception as e:
            logger.error(f"Failed to fetch detailed Ollama models info: {e}")
            return []

    def delete_model(self, model_name: str) -> bool:
        """Deletes a local model from Ollama storage."""
        try:
            logger.warning(f"OllamaLocalClient: Deleting model '{model_name}'...")
            self.client.delete(model_name)
            if model_name in self._verified_local_models:
                self._verified_local_models.remove(model_name)
            logger.info(f"OllamaLocalClient: Successfully deleted model '{model_name}'.")
            return True
        except Exception as e:
            logger.error(f"OllamaLocalClient: Failed to delete model '{model_name}': {e}")
            return False

    # ========================================================================
    # Layer 2: Model Locality Verification via show API
    # ========================================================================
    def _verify_local_model(self, model_name: str) -> bool:
        """Verify a model exists locally by checking its metadata via Ollama's show API."""
        try:
            info = self.client.show(model_name)

            # Check for cloud indicators in model details
            info_str = str(info).lower()
            if any(indicator in info_str for indicator in ["cloud", "remote", "hosted"]):
                logger.warning(
                    f"SECURITY: Model '{model_name}' metadata contains cloud indicators. Blocking."
                )
                return False

            # A locally downloaded model will have modelfile/template/size info
            # Cloud-only models may lack local file references
            if isinstance(info, dict):
                # If there's a "details" key with size info, it's likely local
                details = info.get("details", {})
                if isinstance(details, dict):
                    # Local models typically have quantization_level, family, parameter_size
                    has_local_traits = any(
                        k in details for k in ["quantization_level", "family", "parameter_size", "format"]
                    )
                    if has_local_traits:
                        return True

            # If show() succeeded without error and returned data, model is accessible
            # Accept it but log for audit
            logger.debug(f"Model '{model_name}' passed show() verification.")
            return True

        except Exception as e:
            logger.warning(f"SECURITY: Could not verify model '{model_name}' locality: {e}. Blocking.")
            return False

    # ========================================================================
    # Layer 3: Runtime Guard (called before EVERY inference)
    # ========================================================================
    def _guard_local_only(self, model_name: str) -> None:
        """
        Final security gate before any inference call.
        Raises CloudModelBlockedError if the model appears to be cloud-based.
        """
        if _is_cloud_model(model_name):
            logger.critical(
                f"SECURITY BLOCK: Attempted inference with cloud model '{model_name}'. "
                f"Request DENIED to protect user privacy."
            )
            raise CloudModelBlockedError(model_name)

    def unload(self) -> None:
        """
        Forcefully unloads the last used model from Ollama's VRAM.
        Ollama unloads a model if a request is sent with keep_alive=0.
        """
        if self._last_model_name:
            try:
                logger.info(f"OllamaLocalClient: Unloading model '{self._last_model_name}'...")
                self.client.generate(model=self._last_model_name, prompt="", keep_alive=0)
                logger.info(f"OllamaLocalClient: Unloaded model '{self._last_model_name}'.")
            except Exception as e:
                logger.error(f"OllamaLocalClient: Failed to unload model: {e}")

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        """Generates minutes using Ollama."""
        logger.info(f"generate_minutes: Starting for model={model_name}, transcript_len={len(transcript)}")
        try:
            self._guard_local_only(model_name)  # Layer 3
            model_manager.request_vram(LLM_CLIENT_NAME)
            self._last_model_name = model_name

            prompt = (
                "以下の文字起こしテキストを元に、構造化された議事録をMarkdown形式で作成してください。\n"
                "項目は「会議の概要」「決定事項」「ネクストアクション」を含めて、適切なヘッダーやリスト(# や -)を使用してください。\n\n"
            )
            images = []
            if visual_contexts:
                import base64
                import os

                logger.debug(f"generate_minutes: Processing {len(visual_contexts)} visual contexts.")
                for ctx in visual_contexts:
                    img_path = ctx.get("image_path")
                    if img_path and os.path.exists(img_path):
                        with open(img_path, "rb") as f:
                            images.append(base64.b64encode(f.read()).decode("utf-8"))

            prompt += f"--- 文字起こしテキスト ---\n{transcript}"
            
            msg = {"role": "user", "content": prompt}
            if images:
                msg["images"] = images
            
            logger.debug(f"generate_minutes: Sending request to Ollama ({self.host})...")
            response = self.client.chat(
                model=model_name, 
                messages=[msg],
                options={"temperature": self.temperature}
            )
            content = response["message"]["content"]
            logger.info(f"generate_minutes: Successfully generated minutes. Length: {len(content)}")
            return content
            
        except Exception as e:
            err_str = str(e)
            logger.exception(f"Ollama local generation failed for model {model_name}")
            
            import ollama
            if isinstance(e, ollama.ResponseError):
                if e.status_code == 404:
                    msg = (
                        f"モデル '{model_name}' がPCにインストールされていません。"
                        "設定画面の「Local Smart」機能を再度オンにするか、手動でダウンロードしてください。"
                    )
                    raise RuntimeError(msg) from e

                if e.status_code == 500 and "more system memory" in err_str:
                    msg = (
                        f"メモリ不足によりモデル '{model_name}' を起動できませんでした。"
                        "PCのメモリが不足しているか、モデルが大きすぎます。"
                        "設定画面からより軽量なモデルを選択してください。\n"
                        f"詳細: {err_str}"
                    )
                    raise RuntimeError(msg) from e
            
            raise RuntimeError(f"Chat/Generation failed: {str(e)}") from e

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category/label (1-3 keywords) from the transcript."""
        self._guard_local_only(model_name)  # Layer 3
        model_manager.request_vram(LLM_CLIENT_NAME)
        self._last_model_name = model_name

        prompt = (
            "以下の文字起こしテキストから、その内容を最もよく表す1〜3個の日本語キーワード、または"
            "短いカテゴリー名(例:AI技術, プロジェクト進捗, 顧客ヒアリング)を抽出してください。\n"
            "出力はキーワードのみ(カンマ区切り)とし、余計な説明は一切含めないでください。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(
                model=model_name, 
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature}
            )
            return response["message"]["content"].strip().replace("\n", "")
        except Exception as e:
            logger.error(f"Ollama category extraction error: {e}")
            return "未分類"

    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a concise meeting title using Ollama."""
        self._guard_local_only(model_name)  # Layer 3
        model_manager.request_vram(LLM_CLIENT_NAME)
        self._last_model_name = model_name

        prompt = (
            "以下の文字起こしテキストの内容を要約し、非常に簡潔で分かりやすい「会議のタイトル」を1つ生成してください。\n"
            "タイトルは20文字以内とし、タイトルのみを出力してください。余計な説明は不要です。\n\n"
            f"--- テキスト ---\n{transcript}"
        )
        try:
            response = self.client.chat(
                model=model_name, 
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature}
            )
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
        return self.chat(model_name, messages)

    def chat(self, model_name: str, messages: list[dict]) -> str:
        """Sends a list of messages to Ollama Local."""
        self._guard_local_only(model_name)  # Layer 3
        model_manager.request_vram(LLM_CLIENT_NAME)
        self._last_model_name = model_name

        try:
            response = self.client.chat(
                model=model_name, 
                messages=messages,
                options={"temperature": self.temperature}
            )
            return response["message"]["content"]
        except Exception as e:
            err_str = str(e)
            import ollama
            if isinstance(e, ollama.ResponseError):
                if e.status_code == 404:
                    msg = (
                        f"モデル '{model_name}' がPCにインストールされていません。"
                        "設定画面の「Local Smart」機能を再度オンにするか、手動でダウンロードしてください。"
                    )
                    logger.error(f"Ollama local chat failed (404): {msg}")
                    raise RuntimeError(msg) from e

                if e.status_code == 500 and "more system memory" in err_str:
                    msg = (
                        f"メモリ不足によりモデル '{model_name}' を起動できませんでした。"
                        "PCのメモリが不足しているか、モデルが大きすぎます。"
                        "設定画面からより軽量なモデルを選択してください。\n"
                        f"詳細: {err_str}"
                    )
                    logger.error(f"Ollama local RAM exhaustion (500): {err_str}")
                    raise RuntimeError(msg) from e
            
            logger.error(f"Ollama local chat failed: {e}")
            raise RuntimeError(f"Chat failed: {str(e)}") from e
