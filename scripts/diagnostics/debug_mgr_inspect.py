import os
import sqlite3

from src.core.history_mgr import HistoryManager

db_path = "debug_mgr_inspect.db"
if os.path.exists(db_path):
    os.remove(db_path)

mgr = HistoryManager(db_path=db_path)

# Add
mid = mgr.add_meeting(title="Secret", transcript="Banana", audio_path="x.mp3")
print(f"Added meeting mid={mid}")

# Inspect raw tables
conn = sqlite3.connect(db_path)
m_row = conn.execute("SELECT * FROM meetings").fetchone()
print(f"Meetings row: {m_row}")
fts_row = conn.execute("SELECT rowid, * FROM meetings_fts").fetchone()
print(f"FTS row: {fts_row}")

# Search
results = mgr.search_meetings("Banana")
print(f"Search result: {results}")

conn.close()
os.remove(db_path)
