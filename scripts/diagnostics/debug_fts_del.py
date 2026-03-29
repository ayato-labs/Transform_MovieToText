import os
import sqlite3

db_path = "debug_fts_del.db"
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE meetings (id INTEGER PRIMARY KEY, title TEXT, transcript TEXT, project_name TEXT, category TEXT, minutes_model TEXT)")
conn.execute(
    "CREATE VIRTUAL TABLE meetings_fts USING fts5(title, transcript, project_name, category, minutes_model, content='meetings', content_rowid='id')"
)

# Triggers
conn.execute("""
    CREATE TRIGGER meetings_ai AFTER INSERT ON meetings BEGIN
        INSERT INTO meetings_fts(rowid, title, transcript, project_name, category, minutes_model)
        VALUES (new.id, new.title, new.transcript, new.project_name, new.category, new.minutes_model);
    END;
""")
conn.execute("""
    CREATE TRIGGER meetings_ad AFTER DELETE ON meetings BEGIN
        INSERT INTO meetings_fts(meetings_fts, rowid, title, transcript, project_name, category, minutes_model)
        VALUES('delete', old.id, old.title, old.transcript, old.project_name, old.category, old.minutes_model);
    END;
""")

# Insert
conn.execute(
    "INSERT INTO meetings (title, transcript, project_name, category, minutes_model) VALUES (?, ?, ?, ?, ?)", ("Secret", "Banana", "X", "Y", "")
)
conn.commit()

# Check search before delete
res = conn.execute("SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?", ("Banana",)).fetchall()
print(f"Search before delete: {res}")

# Delete
conn.execute("DELETE FROM meetings WHERE title=?", ("Secret",))
conn.commit()

# Check search after delete
res = conn.execute("SELECT rowid FROM meetings_fts WHERE meetings_fts MATCH ?", ("Banana",)).fetchall()
print(f"Search after delete: {res}")

conn.close()
os.remove(db_path)
