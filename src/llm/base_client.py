from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Returns a list of available model names for this provider."""
        pass

    @abstractmethod
    def generate_minutes(self, transcript: str, model_name: str, visual_contexts: list = None) -> str:
        """Generates meeting minutes from the transcript using the specified model.

        Args:
            transcript: The transcribed text.
            model_name: The name of the LLM model to use.
            visual_contexts: Optional list of dicts {'image_path': str, 'timestamp_sec': float, 'description': str}
        """
        pass

    @abstractmethod
    def extract_category(self, transcript: str, model_name: str) -> str:
        """Extracts a short category/label (1-3 words) from the transcript.

        Args:
            transcript: The transcribed text.
            model_name: The name of the LLM model to use.
        """
        pass

    @abstractmethod
    def generate_title(self, transcript: str, model_name: str) -> str:
        """Generates a concise title (max 20-30 chars) from the transcript.

        Args:
            transcript: The transcribed text.
            model_name: The name of the LLM model to use.
        """
        pass

    @abstractmethod
    def chat(self, model_name: str, messages: list[dict]) -> str:
        """General purpose chat interface.

        Args:
            model_name: The LLM model to use.
            messages: List of message dicts with 'role' and 'content'.
        """
        pass

    def get_models_info(self) -> list[dict]:
        """Returns detailed information about available models (name, size, etc.)."""
        return [{"name": m} for m in self.get_available_models()]

    def delete_model(self, model_name: str) -> bool:
        """Deletes a model from the provider's storage. Returns True if successful."""
        return False

    def transform(self, transcript: str, model_name: str, system_instruction: str, visual_contexts: list = None) -> str:
        """
        Unified transformation method. Higher-level than generate_minutes.
        Can be used for any JSON-returning analysis or general text conversion.
        """
        # Default implementation calls generate_minutes if not overridden
        return self.generate_minutes(transcript, model_name, visual_contexts)
