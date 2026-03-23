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
