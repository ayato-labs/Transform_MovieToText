import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models:")
try:
    # Google GenAI SDK (New version) uses client.models.list()
    # Let's see what's there
    for m in client.models.list():
        if "gemma" in m.name.lower():
            print(f"- {m.name} (Supported: {m.supported_actions})")
except Exception as e:
    print(f"Error listing: {e}")
