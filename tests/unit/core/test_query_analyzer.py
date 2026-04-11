import pytest
from src.core.query_analyzer import QueryAnalyzer
from tests.fixtures.fake_llm import FakeLLMClient

@pytest.fixture
def sample_metadata():
    return {
        "projects": ["Ayato-AI", "Project-X", "Internal-Dev"],
        "categories": ["Minutes", "Strategy", "Bug-Report", "Marketing-Promotion"]
    }

def test_query_analyzer_reconciliation_exact_match(sample_metadata):
    # Setup Fake LLM that returns a specific project name
    fake_client = FakeLLMClient(responses={
        "質問:": "関係するのは Ayato-AI です。"
    })
    
    analyzer = QueryAnalyzer(
        projects=sample_metadata["projects"],
        categories=sample_metadata["categories"],
        client=fake_client,
        model="fake-model"
    )
    
    result = analyzer.analyze("Ayato-AIの進捗はどうですか？")
    
    assert "Ayato-AI" in result["projects"]
    assert any("進捗" in k for k in result["keywords"])

def test_query_analyzer_synonym_match(sample_metadata):
    # '要約' should be normalized to 'Minutes' based on SYNONYMS dict in QueryAnalyzer
    fake_client = FakeLLMClient(responses={
        "質問:": "要約を見せてください。"
    })
    
    analyzer = QueryAnalyzer(
        projects=sample_metadata["projects"],
        categories=sample_metadata["categories"],
        client=fake_client,
        model="fake-model"
    )
    
    result = analyzer.analyze("昨日の会議の要約は？")
    
    assert "Minutes" in result["categories"]

def test_query_analyzer_fuzzy_match(sample_metadata):
    # Test close match (e.g., 'Ayato' matches 'Ayato-AI' with cutoff 0.7)
    fake_client = FakeLLMClient(responses={
        "質問:": "アヤトの件です。" 
    })
    
    analyzer = QueryAnalyzer(
        projects=sample_metadata["projects"],
        categories=sample_metadata["categories"],
        client=fake_client,
        model="fake-model"
    )
    
    # 'アヤト' is in synonyms mapping to 'Ayato-AI'
    result = analyzer.analyze("あやとのプロジェクトについて")
    
    assert "Ayato-AI" in result["projects"]

def test_query_analyzer_keyword_exclusion(sample_metadata):
    # Metadata should be excluded from keywords
    fake_client = FakeLLMClient() # Default responses
    
    analyzer = QueryAnalyzer(
        projects=sample_metadata["projects"],
        categories=sample_metadata["categories"],
        client=fake_client,
        model="fake-model"
    )
    
    result = analyzer.analyze("Project-X の バグ について教えて")
    
    # 'Project-X' is a project, 'バグ' maps to 'Bug-Report' category.
    # They should not be in keywords.
    assert "Project-X" in result["projects"]
    assert "Bug-Report" in result["categories"]
    assert "Project-X" not in result["keywords"]
    assert "バグ" not in result["keywords"]

def test_query_analyzer_no_llm_fallback(sample_metadata):
    # Test case where client initialization failed
    analyzer = QueryAnalyzer(
        projects=sample_metadata["projects"],
        categories=sample_metadata["categories"],
        client=None
    )
    
    result = analyzer.analyze("テストクエリ")
    
    assert result["projects"] == []
    assert result["categories"] == []
    assert "テストクエリ" in result["keywords"]
