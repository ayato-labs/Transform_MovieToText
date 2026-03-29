import sys
from pathlib import Path

from google import genai

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.config_manager import ConfigManager


def test_connectivity():
    config_mgr = ConfigManager()
    # Force use of gemini config regardless of active provider
    gemini_conf = config_mgr.get_provider_config("gemini")
    api_key = gemini_conf.get("api_key")

    if not api_key:
        print("Error: Gemini API key not found in config.")
        return

    client = genai.Client(api_key=api_key)

    print("Testing connection to gemini-1.5-flash...")
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=["Hello, are you there?"],
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    test_connectivity()
