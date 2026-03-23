import sys
from pathlib import Path

from google import genai

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.config_manager import ConfigManager


def list_models():
    config_mgr = ConfigManager()
    gemini_conf = config_mgr.get_provider_config("gemini")
    api_key = gemini_conf.get("api_key")

    if not api_key:
        print("Error: Gemini API key not found in config.")
        return

    client = genai.Client(api_key=api_key)

    print("Listing models...")
    for model in client.models.list():
        print(f"Model: {model.name} (Display: {model.display_name})")
        print(f"  Supported Actions: {model.supported_actions}")


if __name__ == "__main__":
    list_models()
