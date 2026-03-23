import logging
import sys
from pathlib import Path

from google import genai
from google.genai import types

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_experiment():
    # 1. Load API Key
    config_mgr = ConfigManager()
    gemini_conf = config_mgr.get_provider_config("gemini")
    api_key = gemini_conf.get("api_key")

    if not api_key:
        print("Error: Gemini API key not found in config.")
        return

    # 2. Initialize Client
    client = genai.Client(api_key=api_key)

    # We use gemma-3-27b-it
    model_id = "models/gemma-3-27b-it"

    # 3. Path to test images (generated previously)
    # The agent knows these paths from artifact directory
    artifact_dir = Path("C:/Users/saiha/.gemini/antigravity/brain/000b5406-64cc-4fae-a069-1469a7a2b5d6")
    image_paths = list(artifact_dir.glob("test_*.png"))

    if not image_paths:
        print(f"Error: No test images found in {artifact_dir}")
        return

    print(f"Testing with {len(image_paths)} images: {[p.name for p in image_paths]}")

    # 4. Construct Interleaved Content
    content_parts = []
    content_parts.append("以下は、会議中にキャプチャされた複数の画像と、それに関連する状況の説明です。\n")
    content_parts.append(
        "画像1は売上チャート、画像2はシステム構成図です。これらを組み合わせて、現在のビジネス状況と技術インフラの関係を分析してください。\n"
    )

    for img_path in image_paths:
        with open(img_path, "rb") as f:
            image_bytes = f.read()
            content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

    # 5. Send Request
    print(f"Sending request to {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=content_parts,
        )
        print("\n--- Gemma 3 Response ---")
        print(response.text)
        print("--------------------------")
    except Exception as e:
        print(f"Experiment failed: {e}")
        print("Note: If gemma-3-27b-it is not yet available, try listing models.")


if __name__ == "__main__":
    run_experiment()
