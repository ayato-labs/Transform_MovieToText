from unittest.mock import patch

from src.core.resource_advisor import ResourceAdvisor


def test_tier_mapping_low_end():
    """Tests that low RAM results in a 'Low-End' tier."""
    # RAM < 8GB
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 4 * 1024 * 1024 * 1024  # 4GB
        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "Low-End"
        assert "tiny" in tier_info["whisper"]

def test_tier_mapping_mid_range():
    """Tests that moderate RAM results in a 'Mid-Range' tier."""
    # 8GB <= RAM < 16GB
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 12 * 1024 * 1024 * 1024  # 12GB
        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "Mid-Range"
        assert "base" in tier_info["whisper"]

def test_tier_mapping_high_end():
    """Tests that high RAM results in a 'High-End' tier."""
    # RAM >= 32GB
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 64 * 1024 * 1024 * 1024  # 64GB
        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "High-End"
        assert "large-v3" in tier_info["whisper"]

def test_ollama_tag_consistency():
    """Tests that the recommended Ollama tags are specific and memory-efficient."""
    tier_info = ResourceAdvisor.get_best_match()
    ollama_model = tier_info["ollama"]
    # Should include a specific tag for stability
    assert ":" in ollama_model
    if tier_info["tier"] == "Low-End":
        assert "instruct-q4" in ollama_model
