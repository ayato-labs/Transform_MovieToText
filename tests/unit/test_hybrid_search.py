import os
import sys
import unittest

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.history_mgr import HistoryManager


class TestHistoryHybridSearch(unittest.TestCase):
    """
    Test Suite for Hybrid RAG: Keyword (FTS5) + Meta-Scoring.
    """

    def setUp(self):
        # Use a temporary database for testing
        self.db_path = "tests/test_history.db"
        self.mgr = HistoryManager(self.db_path)

        # Insert test data
        self.mgr.add_meeting(title="Project Gravity", transcript="Launch at Tokyo Tower", audio_path="none", project_name="Gravity")
        self.mgr.add_meeting(title="Weekly Sync", transcript="Discussing Gravity with team", audio_path="none")
        self.mgr.update_minutes(1, minutes="This is the launch summary of Project Gravity")

    def tearDown(self):
        # Correctly close it if needed, but HistoryManager uses closing() internally
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_search_hybrid_title_boost(self):
        # Case: Searching "Gravity" should prioritize the title match 100%
        results = self.mgr.search_hybrid("Gravity")
        self.assertGreater(len(results), 0)

        # Verify the first result is the meeting with "Gravity" in title
        self.assertEqual(results[0]["title"], "Project Gravity")
        self.assertEqual(results[0]["_search_type"], "keyword")
        self.assertIn("Project Gravity", results[0]["title"])

    def test_search_hybrid_summary_context(self):
        # Case: Searching "launch" which is in summary
        results = self.mgr.search_hybrid("launch")
        self.assertGreater(len(results), 0)
        # Verify it caught the summary context
        self.assertIn("launch", (results[0]["minutes"] or "").lower() or (results[0]["transcript"] or "").lower())


if __name__ == "__main__":
    unittest.main()
