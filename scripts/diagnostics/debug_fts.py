import os
import sqlite3

db_path = "debug_fts.db"
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE meetings (id INTEGER PRIMARY KEY, title TEXT, transcript TEXT, project_name TEXT, category TEXT, minutes_model TEXT)")
conn.execute(
    "CREATE VIRTUAL TABLE meetings_fts USING fts5(title, transcript, project_name, category, minutes_model, content='meetings', content_rowid='id')"
)

# Trigger
conn.execute("""
    CREATE TRIGGER meetings_ai AFTER INSERT ON meetings BEGIN
        INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model)
        VALUES (new.id, new.title, new.transcript, new.project_name, new.category, new.minutes_model);
    END;
""")

# Insert
conn.execute(
    "INSERT INTO meetings (title, transcript, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?)",
    ("Test", "I like Banana", "Project X", "General", "gpt-4"),
)
conn.commit()

# Check FTS content
row = conn.execute("SELECT * FROM meetings_fts").fetchone()
print(f"FTS content: {row}")

# Search
res = conn.execute("SELECT * FROM meetings WHERE id IN (SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?)", ("Banana",)).fetchall()
print(f"Search result for 'Banana': {res}")

conn.close()
os.remove(db_path)
