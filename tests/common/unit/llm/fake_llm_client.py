from src.llm.base_client import BaseLLMClient


class FakeLLMClient(BaseLLMClient):
    """
    A manual fake LLM client for unit tests.
    Does NOT use MagicMock. Returns predictable static data.
    """

    def __init__(self, **kwargs):
        self.recorded_calls = []
        self.available_models = ["model-1", "model-2"]

    def get_available_models(self) -> list[str]:
        return self.available_models

    def generate_minutes(
        self,
        transcript: str,
        model_name: str,
        visual_contexts: list = None,
        image_paths: list = None,
    ) -> str:
        self.recorded_calls.append(
            {
                "method": "generate_minutes",
                "transcript": transcript,
                "model_name": model_name,
                "visual_contexts": visual_contexts,
                "image_paths": image_paths,
            }
        )
        return "偽の議事録: 決定事項 - テストを成功させる。"

    def extract_category(self, transcript: str, model_name: str) -> str:
        self.recorded_calls.append({"method": "extract_category", "transcript": transcript, "model_name": model_name})
        return "テストカテゴリー"

    def generate_title(self, transcript: str, model_name: str) -> str:
        self.recorded_calls.append({"method": "generate_title", "transcript": transcript, "model_name": model_name})
        return "テストタイトル"

    def chat(self, model_name: str, messages: list[dict]) -> str:
        self.recorded_calls.append({"method": "chat", "model_name": model_name, "messages": messages})
        return "偽の回答"