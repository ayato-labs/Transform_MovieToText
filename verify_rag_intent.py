import os
import json
import logging
from dotenv import load_dotenv
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 1. Load Environment Variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    logger.error("GEMINI_API_KEY not found in .env")
    exit(1)

# 2. Initialize Google GenAI Client
client = genai.Client(api_key=api_key)

# 3. Test Configuration (Mock Data)
AVAILABLE_PROJECTS = ["Ayato-AI", "Marketing", "Recruitment-2025", "Secret-Project-X"]
AVAILABLE_TAGS = ["Minutes", "Strategy", "Bug-Report", "Feature-Request", "Draft"]

# 4. Prompt Engineering (Combined)
def build_prompt(query, projects, tags):
    return f"""
あなたは検索意図解析アシスタントです。
ユーザーの質問を分析し、関連するプロジェクト名・タグ名・検索ワードを抽出してJSONのみを返してください。

【対象プロジェクト】
{projects}

【対象タグ】
{tags}

【出力JSONフォーマット】
{{
  "projects": ["プロジェクト名1", "プロジェクト名2"],
  "categories": ["タグ1", "タグ2"],
  "keywords": ["重要単語1", "重要単語2"],
  "reason": "抽出した理由"
}}

ユーザーの質問: {query}
"""

def verify_intent_extraction(query: str):
    logger.info(f"--- Query: {query} ---")
    
    # Standard Gemma 3 model ID confirmed from listing attempt
    model_id = 'gemma-3-1b-it'
    
    prompt = build_prompt(query, AVAILABLE_PROJECTS, AVAILABLE_TAGS)
    
    try:
        # Simplest possible call
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Robust parsing for JSON
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
        elif "{" in raw_text and "}" in raw_text:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            raw_text = raw_text[start:end]
            
        data = json.loads(raw_text)
        print(f"Results:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to analyze query: {e}")
        return None

if __name__ == "__main__":
    queries = [
        "Ayato-AIとMarketingの議事録が欲しい",
        "採用のバグ報告はある？"
    ]
    for q in queries:
        verify_intent_extraction(q)
        print("-" * 40)
