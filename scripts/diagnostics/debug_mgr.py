import os

from src.core.history_mgr import HistoryManager

db_path = "debug_mgr.db"
if os.path.exists(db_path):
    os.remove(db_path)

mgr = HistoryManager(db_path=db_path)

# Add
mid = mgr.add_meeting(title="Secret", transcript="Banana", audio_path="x.mp3")
print(f"Added meeting mid={mid}")

# Search
results = mgr.search_meetings("Banana")
print(f"Search result: {results}")

# Delete
mgr.delete_meeting(mid)
print(f"Deleted meeting mid={mid}")

# Search again
results_after = mgr.search_meetings("Banana")
print(f"Search result after delete: {results_after}")

os.remove(db_path)
