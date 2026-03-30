import os
import re
import logging
import difflib
import sys
import io
import json # Added missing import
from dotenv import load_dotenv
from google import genai

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# --- 1. System Knowledge ---
REAL_PROJECTS = ["Ayato-AI", "Marketing-Promotion", "Recruitment-2025", "Secret-Project-X"]
REAL_TAGS = ["Minutes", "Strategy", "Bug-Report", "Action-Items", "Draft"]

# --- 2. Regex-Based Robust Parser ---
class RegexParser:
    def __init__(self, projects, tags):
        self.projects = projects
        self.tags = tags

    def parse_raw_text(self, text):
        logger.info("Executing Regex-Based Extraction...")
        found_projects = []
        found_tags = []
        
        # 1. Strict Matching
        for p in self.projects:
            if p.lower() in text.lower(): found_projects.append(p)
        for t in self.tags:
            if t.lower() in text.lower(): found_tags.append(t)
            
        # 2. Fuzzy Matching for terms in text
        words = re.findall(r'\w+', text)
        for word in words:
            if len(word) < 2: continue
            p_match = difflib.get_close_matches(word, self.projects, n=1, cutoff=0.8)
            if p_match: found_projects.append(p_match[0])
            t_match = difflib.get_close_matches(word, self.tags, n=1, cutoff=0.8)
            if t_match: found_tags.append(t_match[0])

        return {
            "projects": sorted(list(set(found_projects))),
            "categories": sorted(list(set(found_tags))),
            "keywords": list(set(words[:15]))
        }

# --- 3. Ultra-Simple LLM Call ---
def analyze_minimal(query):
    prompt = f"""
以下の質問を読み、関係する【プロジェクト名】や【タグ名】を、提示されたリストの中からすべて抜き出して答えなさい。

【プロジェクト名リスト】
{REAL_PROJECTS}

【タグ名リスト】
{REAL_TAGS}

質問: {query}
答え:
"""
    try:
        response = client.models.generate_content(model='gemma-3-1b-it', contents=prompt)
        return response.text
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return ""

if __name__ == "__main__":
    parser = RegexParser(REAL_PROJECTS, REAL_TAGS)
    test_query = "Ayato-AIではなくて秘密プロジェクト(Secret-Project-X)の議事録(Minutes)を出して"
    
    print(f"\nQuery: {test_query}")
    raw_text = analyze_minimal(test_query)
    print(f"\n[Step 1: RAW LLM OUTPUT]\n{raw_text}")
    
    final_result = parser.parse_raw_text(raw_text)
    print(f"\n[Step 2: REGEX/FUZZY PARSED RESULT]")
    print(json.dumps(final_result, indent=2, ensure_ascii=False))
    
    if "Secret-Project-X" in final_result["projects"]:
         print("\n✅ Verification SUCCESS: Target project identified.")
    else:
         print("\n❌ Verification FAILED.")
