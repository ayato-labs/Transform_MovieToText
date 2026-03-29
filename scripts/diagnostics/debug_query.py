import os
import sqlite3

db_path = "debug_query.db"
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE meetings (id INTEGER PRIMARY KEY, title TEXT, transcript TEXT, project_name TEXT, category TEXT, minutes_model TEXT)")
conn.execute(
    "CREATE VIRTUAL TABLE meetings_fts USING fts5(title, transcript, project_name, category, minutes_model, content='meetings', content_rowid='id')"
)

# Insert data (directly for speed)
conn.execute("INSERT INTO meetings (id, title, transcript, project_name, category, minutes_model) VALUES (1, 'Secret', 'Banana', 'X', 'Y', '')")
conn.execute(
    "INSERT INTO meetings_fts (rowid, title, transcript, project_name, category, minutes_model) VALUES (1, 'Secret', 'Banana', 'X', 'Y', '')"
)
conn.commit()

query = "Banana"
# The query from HistoryManager:
sql = "SELECT * FROM meetings WHERE id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?) ORDER BY id DESC"

res = conn.execute(sql, (query,)).fetchall()
print(f"Results for '{query}': {res}")

results_fts = conn.execute("SELECT * FROM meetings_fts WHERE meetings_fts MATCH ?", (query,)).fetchall()
print(f"FTS Results for '{query}': {results_fts}")

conn.close()
os.remove(db_path)
