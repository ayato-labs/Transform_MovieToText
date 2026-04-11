import logging

logger = logging.getLogger(__name__)

class FakeLLMClient:
    """
    A deterministic LLM client for unit tests.
    Does not use MagicMock, satisfying the strict unit testing constraints.
    """
    def __init__(self, responses=None):
        # Mapping of prompt substring to response string
        self.responses = responses or {}
        self.generate_calls = []
        self.chat_calls = []

    def generate(self, prompt, model_name=None):
        self.generate_calls.append({"prompt": prompt, "model": model_name})
        for key, resp in self.responses.items():
            if key in prompt:
                return resp
        return "default fake output"

    def chat(self, messages, model_name=None):
        self.chat_calls.append({"messages": messages, "model": model_name})
        # Try to match based on the content of the last message
        last_msg = messages[-1]["content"] if messages else ""
        for key, resp in self.responses.items():
            if key in last_msg:
                return resp
        return "default fake chat response"

    def get_available_models(self):
        return ["fake-model-1", "fake-model-2"]
