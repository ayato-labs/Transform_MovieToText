import logging
import os
import sys
import io
from src.core.query_analyzer import QueryAnalyzer
from src.core.history_mgr import history_mgr

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_full_flow():
    print("="*60)
    print("   FINAL RAG FLOW VERIFICATION")
    print("="*60)
    
    # 1. Prepare system data
    all_projects = history_mgr.get_projects()
    all_categories = history_mgr.get_categories()
    
    print(f"System Projects: {all_projects}")
    print(f"System Categories: {all_categories}")
    
    analyzer = QueryAnalyzer(all_projects, all_categories)
    
    # 2. Test Query (Matched to an existing project)
    query = "WBSの経済ニュースについて教えて"
    print(f"\nUser Query: {query}")
    
    intent = analyzer.analyze(query)
    print(f"Extracted Intent: {intent}")
    
    # 3. Perform Filtered Search
    search_keywords = " ".join(intent["keywords"]) if intent["keywords"] else query
    results = history_mgr.get_meetings_filtered(
        project_names=intent["projects"],
        categories=intent["categories"],
        search_query=search_keywords,
        limit=5
    )
    
    print(f"\nSearch Results Found: {len(results)}")
    for r in results:
        print(f"- [{r.get('timestamp')}] {r.get('title')} | Project: {r.get('project_name')} | Tag: {r.get('category')}")

    if intent["projects"] or intent["categories"]:
        print("\n✅ Verification: Metadata was successfully extracted and used in search.")
    else:
        print("\n⚠️ Note: No specific metadata extracted for this query (fallback mode).")

if __name__ == "__main__":
    verify_full_flow()
