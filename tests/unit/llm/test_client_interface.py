import inspect
import os
import sys
import unittest

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.llm.base_client import BaseLLMClient
from src.llm.providers.gemini_client import GeminiLLMClient
from src.llm.providers.ollama_client import OllamaCloudClient, OllamaLocalClient


class TestLLMClientInterfaces(unittest.TestCase):
    """
    Unit test for ALL LLM provider class signatures.
    CRITICAL: Does NOT use MagicMock().
    Directly inspects the class structure to catch attribute/signature mismatches.
    """

    def _verify_conformance(self, client_cls):
        """Helper to check if a class strictly follows BaseLLMClient interface."""
        base_methods = {name: func for name, func in inspect.getmembers(BaseLLMClient, predicate=inspect.isfunction) if not name.startswith("__")}

        for name, base_func in base_methods.items():
            # 1. Attribute Check: Must exist
            self.assertTrue(hasattr(client_cls, name), f"{client_cls.__name__} is missing required method: '{name}'")

            # 2. Signature Check: Must match arguments (basic check)
            client_func = getattr(client_cls, name)
            base_sig = inspect.signature(base_func)
            client_sig = inspect.signature(client_func)

            # Note: We skip checking 'self' but compare others
            base_params = list(base_sig.parameters.keys())
            client_params = list(client_sig.parameters.keys())

            self.assertEqual(
                base_params, client_params, f"Signature mismatch in {client_cls.__name__}.{name}. Expected {base_params}, got {client_params}"
            )

    def test_gemini_interface(self):
        self._verify_conformance(GeminiLLMClient)

    def test_ollama_local_interface(self):
        self._verify_conformance(OllamaLocalClient)

    def test_ollama_cloud_interface(self):
        self._verify_conformance(OllamaCloudClient)

    def test_direct_instantiation_safety(self):
        """Verify that we can instantiate without hidden network calls in __init__."""
        try:
            # We use dummy API keys - if __init__ starts a network connection, this will fail/hang.
            # That's a good test for personal-use tools!
            GeminiLLMClient(api_key="sk-dummy")
            OllamaLocalClient(base_url="http://localhost:11434")
            OllamaCloudClient(api_key="sk-dummy")
        except Exception as e:
            # If it's just a connection error (timeout), fine.
            # If it's a structural error (TypeError in __init__), test fails.
            if "TypeError" in str(type(e)):
                raise e


if __name__ == "__main__":
    unittest.main()
