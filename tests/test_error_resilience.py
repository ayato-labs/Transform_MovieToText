import sqlite3

import pytest

from src.core.history_mgr import HistoryError, HistoryManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_resilience.db"
    return str(db_file)


def test_database_lock_resilience(temp_db):
    """Tests if HistoryManager handles a locked database correctly (timeout/raise)."""
    mgr = HistoryManager(db_path=temp_db, timeout=1.0)

    # 1. Manually lock the DB in another connection
    conn = sqlite3.connect(temp_db)
    conn.execute("BEGIN EXCLUSIVE")

    # 2. Try to add a meeting from the manager while DB is locked
    with pytest.raises(HistoryError):
        mgr.add_meeting("Locked Meeting", "Transcript", "path/to/audio")

    conn.rollback()
    conn.close()

    # 3. Verify it works after lock is released
    mid = mgr.add_meeting("Unlocked Meeting", "Transcript", "path/to/audio")
    assert mid is not None


def test_whisper_invalid_model_handling():
    """Tests if WhisperTranscriber raises clear errors for non-existent models."""
    from src.transcriber import WhisperTranscriber

    transcriber = WhisperTranscriber()

    with pytest.raises(ValueError):  # faster-whisper raises ValueError for unknown sizes
        transcriber.load_model("totally-invalid-model-name")


def test_config_manager_file_corruption(tmp_path):
    """Tests how ConfigManager handles a corrupted config file."""
    from src.config_manager import ConfigManager

    config_file = tmp_path / "corrupted_config.json"
    with open(config_file, "w") as f:
        f.write("{ invalid json [")

    # Should fallback to defaults or raise informative error
    mgr = ConfigManager(config_path=str(config_file))
    assert mgr.get_whisper_model() is not None  # Should be default
