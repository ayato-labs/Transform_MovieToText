import os

from src.core.history_mgr import HistoryManager


def diag():
    db_path = "diag_test_v3.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        mgr = HistoryManager(db_path=db_path)
        print("Initialized HistoryManager.")

        # Check Triggers in SQLITE_MASTER
        with mgr._get_connection() as conn:
            triggers = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'").fetchall()
            print(f"Triggers Found: {[t['name'] for t in triggers]}")
            for t in triggers:
                print(f"Trigger {t['name']}:\n{t['sql']}")

        # Test Add
        mgr.add_meeting(title="A", transcript="Banana", audio_path="1")

        # Check FTS
        with mgr._get_connection() as conn:
            rows = conn.execute("SELECT rowid, * FROM meetings_fts").fetchall()
            print(f"FTS Table Count: {len(rows)}")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    diag()
