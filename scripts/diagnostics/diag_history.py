import os
import sqlite3

from src.core.history_mgr import HistoryManager


def diag():
    db_path = "diag_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        mgr = HistoryManager(db_path=db_path)
        print("Initialized HistoryManager.")

        # Test 1: Add and Search
        mgr.add_meeting(title="A", transcript="I like Banana", audio_path="1")
        mgr.add_meeting(title="B", transcript="Red Apple", audio_path="2")

        results = mgr.search_meetings("Banana")
        print(f"Search for 'Banana': Found {len(results)} results.")
        for r in results:
            print(f"  Result ID: {r['id']}, Title: {r['title']}")

        # Test 2: Double check FTS table
        with mgr._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT rowid, * FROM meetings_fts").fetchall()
            print(f"FTS Table Content ({len(rows)} rows):")
            for r in rows:
                print(f"  {dict(r)}")

        # Test 3: Search Apple
        results = mgr.search_meetings("Apple")
        print(f"Search for 'Apple': Found {len(results)} results.")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    diag()
