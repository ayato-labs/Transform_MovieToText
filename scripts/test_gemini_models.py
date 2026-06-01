
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.llm.providers.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)

def test_gemini_model_fetch():
    api_key = "AIzaSyAaFFBIY99IXzj8mp9Drus_WU5Ve4y3UsY"
    print(f"Testing GeminiClient with API Key: {api_key[:10]}...")
    
    try:
        client = GeminiClient(api_key=api_key)
        models = client.get_available_models()
        
        print(f"\nResult: Found {len(models)} models.")
        for m in models:
            print(f" - {m}")
            
        if not models:
            print("\nWarning: Model list is empty!")
            
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_model_fetch()
