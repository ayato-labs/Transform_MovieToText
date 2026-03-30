import os
import sys
import unittest
from unittest.mock import patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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
        self.assertEqual(res["tier"], "Entry")
        self.assertEqual(res["ollama"], "llama3.2")

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_small_gpu_tier(self, mock_specs):
        # SmallGPU: RAM 8GB, VRAM 4GB
        mock_specs.return_value = (8.0, 4.0)
        res = ResourceAdvisor.get_best_match()
        self.assertEqual(res["tier"], "SmallGPU")
        self.assertEqual(res["ollama"], "phi3.5")

    @patch("src.core.resource_advisor.ResourceAdvisor.get_system_specs")
    def test_monster_tier(self, mock_specs):
        # Monster: RAM 64GB, VRAM 24GB
        mock_specs.return_value = (64.0, 24.0)
        res = ResourceAdvisor.get_best_match()
        self.assertEqual(res["tier"], "Monster")
        self.assertEqual(res["ollama"], "llama3.1:70b")


if __name__ == "__main__":
    unittest.main()
