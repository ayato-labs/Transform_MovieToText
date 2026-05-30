import unittest
from unittest.mock import patch

# Ensure src is in path
from src.core.resource_advisor import ResourceAdvisor


class TestResourceAdvisorLogic(unittest.TestCase):
    """
    Unit test for individual functions in ResourceAdvisor.
    Focus: Pure logic (mapping specs to tiers).
    """

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_get_best_match_logic(self, mock_specs):
        # Case 1: Minimal resources
        mock_specs.return_value = (4.0, 0.0)
        res = ResourceAdvisor.get_best_match()
        self.assertEqual(res["tier"], "Entry")
        self.assertEqual(res["ollama"], "gemma3:2b")

        # Case 2: Standard GPU
        mock_specs.return_value = (16.0, 8.0)
        res = ResourceAdvisor.get_best_match()
        self.assertEqual(res["tier"], "Standard")
        self.assertEqual(res["ollama"], "gemma3:4b")

        # Case 3: Monster
        mock_specs.return_value = (128.0, 48.0)
        res = ResourceAdvisor.get_best_match()
        self.assertEqual(res["tier"], "Monster")
        self.assertEqual(res["ollama"], "gemma3:4b")


if __name__ == "__main__":
    unittest.main()
