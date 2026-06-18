import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from google import genai
from google.genai import types, errors

from src.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)

def is_transient_error(e: Exception) -> bool:
    """
    Check if the error is transient and should be retried.
    Handles Gemini-specific 503 (high demand) and 429 (rate limit) errors.
    """
    # 1. Check by explicit type if available
    if isinstance(e, errors.ServerError) or isinstance(e, errors.ClientError):
        # google-genai errors often have a code attribute
        code = getattr(e, "code", None)
        if code in [429, 503]:
            return True
    
    # 2. Check by attributes (duck typing for resilience)
    if hasattr(e, "code") and e.code in [429, 503]:
        return True
    if hasattr(e, "status") and "UNAVAILABLE" in str(e.status):
        return True

    # 3. Fallback to string matching
    err_msg = str(e).lower()
    transient_indicators = ["503", "429", "unavailable", "busy", "high demand", "rate limit"]
    return any(indicator in err_msg for indicator in transient_indicators)

class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API via google-genai SDK."""
    
    def __init__(self, api_key: str, temperature: float = 0.7):
        if not api_key:
            raise ValueError("Gemini API Key is required.")
        
        # Layer 1: SDK-level retry configuration
        # This provides the first line of defense with the SDK's internal tenacity loop.
        retry_options = types.HttpRetryOptions(
            attempts=5,                    # 1 initial + 4 retries
            initial_delay=2.0,
            max_delay=60.0,
            http_status_codes=[503, 429]
        )
        
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=retry_options,
                timeout=120 * 1000  # 120 seconds timeout
            )
        )
        self._model_name = "gemma-4-31b-it" # Default model
        self.temperature = float(temperature)

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        retry=retry_if_exception(is_transient_error),
        before_sleep=lambda retry_state: logger.warning(
            f"Gemini API busy (App-level attempt {retry_state.attempt_number}). "
            f"Retrying in {retry_state.next_action.sleep}s... Error: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    def _generate_content_with_retry(self, model, contents, config=None):
        """Helper to call generate_content with exponential backoff."""
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception(is_transient_error),
        reraise=True
    )
    def _list_models_with_retry(self):
        """Helper to call models.list with retries."""
        return list(self.client.models.list())

    def transform(self, transcript: str, model_name: str, system_instruction: str, visual_contexts: list = None) -> str:
        """Unified transformation method using Gemini's system_instruction."""
        logger.info(f"GeminiClient: Transforming with model={model_name or self._model_name}")
        try:
            # Use generate_content with system_instruction and retry
            response = self._generate_content_with_retry(
                model=model_name or self._model_name,
                contents=[transcript],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.temperature
                )
            )
            return response.text
        except Exception as e:
            logger.exception(f"Gemini API transform failed after retries: {e}")
            raise RuntimeError(f"Transform failed: {str(e)}") from e

    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        """Generates structured minutes using Gemini API."""
        logger.info(f"GeminiClient: Generating minutes for model={model_name or self._model_name}, transcript_len={len(transcript)}")
        
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

            response = self._generate_content_with_retry(
                model=model_name or self._model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=self.temperature)
            )
            
            return response.text
        except Exception as e:
            logger.exception(f"Gemini API generation failed after retries: {e}")
            raise RuntimeError(f"Gemini API Error: {str(e)}") from e

    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category using Gemini API."""
        try:
            prompt = (
                "以下のテキストの内容から、最も適切なカテゴリを1つから3つのキーワードで答えてください。"
                "例: 技術会議, 営業進捗, デザインレビュー\n\n"
                f"内容: {transcript[:2000]}"
            )
            response = self._generate_content_with_retry(
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
            response = self._generate_content_with_retry(
                model=model_name or self._model_name,
                contents=prompt
            )
            return response.text.strip().replace('"', '')
        except Exception:
            logger.exception("Gemini title generation failed.")
            return "無題の会議"

    def chat(self, model_name: str, messages: list[dict]) -> str:
        """Sends a list of messages to Gemini API."""
        try:
            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

            response = self._generate_content_with_retry(
                model=model_name or self._model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=self.temperature)
            )
            return response.text
        except Exception as e:
            logger.exception(f"Gemini API chat failed after retries: {e}")
            raise RuntimeError(f"Chat failed: {str(e)}") from e

    def get_available_models(self) -> list[str]:
        """Fetches available models from Gemini API."""
        try:
            models = []
            # Use retry for listing models too
            model_list = self._list_models_with_retry()
            for m in model_list:
                # Correct attribute names in current google-genai SDK
                supported_actions = getattr(m, "supported_actions", [])
                
                # Check for content generation capability
                if "generateContent" in supported_actions:
                    # Strip 'models/' prefix if present
                    name = m.name.replace("models/", "")
                    
                    # Optional: filter out legacy or experimental models if needed
                    # but for now, we follow the pattern of including all that support generateContent
                    models.append(name)
            return sorted(models)
        except Exception as e:
            error_str = str(e)
            if "API_KEY_INVALID" in error_str or "API key expired" in error_str or "API key not valid" in error_str:
                logger.warning("Gemini API key is invalid or expired. Models could not be fetched.")
            else:
                logger.error(f"Failed to fetch Gemini models from API: {e}")
            return []

    def get_models_info(self) -> list[dict]:
        """Returns detailed information about Gemini models."""
        return [
            {"name": model, "size_bytes": 0, "size_gb": 0.0} 
            for model in self.get_available_models()
        ]

    def delete_model(self, model_name: str) -> bool:
        """Gemini models cannot be deleted."""
        logger.warning(f"GeminiClient: Cannot delete cloud model '{model_name}'.")
        return False
