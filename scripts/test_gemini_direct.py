import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.llm.providers.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)

def test_gemini_direct():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    print(f"Testing GeminiClient with API Key: {api_key[:10] if api_key else 'None'}...")
    
    try:
        client = GeminiClient(api_key=api_key)
        
        print("\n--- Testing Model List ---")
        models = client.get_available_models()
        print(f"Result: Found {len(models)} models.")
        if models:
            print(f"First 5 models: {models[:5]}")
            
        print("\n--- Testing Content Generation (gemma-4-31b-it) ---")
        try:
            res = client.generate_minutes(transcript="本日はプロトタイプのレビューを行います。", model_name="gemma-4-31b-it")
            print(f"Success! Response: {res[:100]}...")
        except Exception as e:
            print(f"Generation failed: {e}")
            
    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    test_gemini_direct()
