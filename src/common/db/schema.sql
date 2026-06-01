-- Meetings table: Store core transcription and metadata
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    transcript TEXT,
    transcript_segments TEXT,
    minutes TEXT,
    minutes_model TEXT,
    audio_path TEXT,
    model_info TEXT,
    project_name TEXT,
    category TEXT
);

-- Visual Context table: Store frame metadata linked to meetings
CREATE TABLE IF NOT EXISTS visual_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    timestamp REAL,
    image_path TEXT,
    description TEXT,
    ocr_text TEXT,
    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);

-- Full Text Search table (FTS5)
-- Using 'trigram' tokenizer for high-performance substring/partial matching (similar to LIKE but indexed)
CREATE VIRTUAL TABLE IF NOT EXISTS meetings_fts USING fts5(
    title, transcript, minutes, project_name, category, minutes_model,
    tokenize='trigram'
);
