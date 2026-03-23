import sys
from pathlib import Path

from google import genai

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.config_manager import ConfigManager


def find_models():
    config_mgr = ConfigManager()
    gemini_conf = config_mgr.get_provider_config("gemini")
    api_key = gemini_conf.get("api_key")

    if not api_key:
        print("Error: Gemini API key not found in config.")
        return

    client = genai.Client(api_key=api_key)

    # Try explicit IDs
    candidates = ["gemma-3-27b-it", "gemma-3-27b", "gemma-3-4b-it", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
    print("Checking specific candidates...")
    for cid in candidates:
        try:
            client.models.get(model=cid)
            print(f"SUCCESS: {cid} is AVAILABLE.")
        except Exception:
            # print(f"DEBUG: {cid} check failed.")
            pass

    print("\nListing all matching models (Gemma/Gemini)...")
    try:
        for model in client.models.list():
            name = model.name.lower()
            if "gemma" in name or "gemini" in name:
                print(f"Found: {model.name}")
    except Exception as e:
        print(f"List failed: {e}")


if __name__ == "__main__":
    find_models()
