from unittest.mock import patch

from src.core.resource_advisor import ResourceAdvisor


def test_tier_mapping_entry():
    """Tests that low RAM results in an 'Entry' tier."""
    # RAM < 8GB or VRAM < 4GB
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 4 * 1024 * 1024 * 1024  # 4GB
        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "Entry"
        assert tier_info["whisper"] == "base"


def test_tier_mapping_small_gpu():
    """Tests that moderate hardware results in a 'SmallGPU' tier if VRAM is present."""
    # 8GB <= RAM < 16GB, VRAM >= 4GB
    with patch("psutil.virtual_memory") as mock_mem, patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs") as mock_specs:
        mock_mem.return_value.total = 12 * 1024 * 1024 * 1024  # 12GB
        mock_specs.return_value = (12.0, 4.0)

        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "SmallGPU"
        assert tier_info["whisper"] == "small"


def test_tier_mapping_monster():
    """Tests that very high-end hardware results in a 'Monster' tier."""
    # RAM >= 64GB, VRAM >= 22GB
    with patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs") as mock_specs:
        mock_specs.return_value = (64.0, 24.0)
        tier_info = ResourceAdvisor.get_best_match()
        assert tier_info["tier"] == "Monster"
        assert tier_info["whisper"] == "large-v3"


def test_ollama_tag_consistency():
    """Tests that the recommended Ollama tags are specific and memory-efficient."""
    tier_info = ResourceAdvisor.get_best_match()
    ollama_model = tier_info["ollama"]
    # Should include a specific tag for stability
    assert ":" in ollama_model
    if tier_info["tier"] == "Entry":
        assert "gemma3:1b" in ollama_model