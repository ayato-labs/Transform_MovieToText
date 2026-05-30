import unittest
from unittest.mock import patch

# Ensure src is in path
from src.core.resource_advisor import ResourceAdvisor


class TestResourceAdvisor(unittest.TestCase):
    """
    Test Suite for ResourceAdvisor static hardware mapping.
    Ensures that correct tiers are selected for given RAM/VRAM.
    """

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_entry_tier(self, mock_specs):
        # Entry: RAM 8GB, VRAM 0GB
        mock_specs.return_value = (8.0, 0.0)
        res = ResourceAdvisor.get_best_match()
        assert res["tier"] == "Entry"
        assert res["ollama"] == "gemma3:2b"

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_standard_tier(self, mock_specs):
        # Standard: RAM 16GB, VRAM 8GB
        mock_specs.return_value = (16.0, 8.0)
        res = ResourceAdvisor.get_best_match()
        assert res["tier"] == "Standard"
        assert res["ollama"] == "gemma3:4b"

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_monster_tier(self, mock_specs):
        # Monster: RAM 64GB, VRAM 24GB
        mock_specs.return_value = (64.0, 24.0)
        res = ResourceAdvisor.get_best_match()
        assert res["tier"] == "Monster"
        assert res["ollama"] == "gemma3:4b"


if __name__ == "__main__":
    unittest.main()
