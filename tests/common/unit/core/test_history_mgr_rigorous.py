import logging

import pytest

from src.core.history_mgr import HistoryError, HistoryManager

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_history.db"
    mgr = HistoryManager(db_path=str(db_file))
    yield mgr


def test_add_and_get_meeting_rigorous(temp_db):
    """Verifies that all fields are correctly saved and retrieved."""
    meeting_id = temp_db.add_meeting(
        title="Rigorous Test",
        transcript="Detailed content for testing.",
        audio_path="/path/to/audio.mp3",
        model_info="turbo",
        project_name="Deep-Test",
        category="Testing",
    )

    meeting = temp_db.get_meeting(meeting_id)
    assert meeting is not None
    assert meeting["title"] == "Rigorous Test"
    assert meeting["project_name"] == "Deep-Test"
    assert meeting["category"] == "Testing"
    assert meeting["audio_path"] == "/path/to/audio.mp3"
    assert meeting["model_info"] == "turbo"
    assert "timestamp" in meeting


def test_get_meeting_nonexistent(temp_db):
    """Verifies retrieval of non-existent meeting returns None."""
    assert temp_db.get_meeting(99999) is None


def test_delete_meeting_and_fts_sync(temp_db):
    """Verifies that deleting a meeting also removes it from FTS index."""
    mid = temp_db.add_meeting(title="Secret", transcript="Banana", audio_path="x.mp3")
    assert len(temp_db.search_meetings("Banana")) == 1

    temp_db.delete_meeting(mid)
    assert temp_db.get_meeting(mid) is None
    assert len(temp_db.search_meetings("Banana")) == 0


def test_history_mgr_initialization_error(tmp_path):
    """Verifies that bad DB paths raise appropriate errors."""
    # Using a directory name as a file path usually causes an OperationalError in SQLite
    bad_path = tmp_path / "a_directory"
    bad_path.mkdir()

    with pytest.raises(HistoryError) as excinfo:
        # HistoryManager calls _init_db in __init__
        HistoryManager(db_path=str(bad_path))
    assert "Database initialization failed" in str(excinfo.value)


def test_update_minutes_rigorous(temp_db):
    mid = temp_db.add_meeting(title="Meeting", transcript="..", audio_path="..")
    temp_db.update_minutes(mid, "The summary", model_name="gpt-4")

    m = temp_db.get_meeting(mid)
    assert m["minutes"] == "The summary"
    assert m["minutes_model"] == "gpt-4"


@pytest.mark.parametrize(
    "query,expected_count",
    [
        ("Banana", 1),
        ("Apple", 1),
        ("Fruit", 0),  # Not in text
        ("", 2),  # Empty query now returns all meetings
    ],
)
def test_search_advanced(temp_db, query, expected_count):
    temp_db.add_meeting(title="A", transcript="I like Banana", audio_path="1")
    temp_db.add_meeting(title="B", transcript="Red Apple", audio_path="2")

    # DEBUG: Check FTS content
    with temp_db._get_connection() as conn:
        rows = conn.execute("SELECT rowid, * FROM meetings_fts").fetchall()
        logger.debug("\n[DEBUG] FTS Table Content (%d rows):", len(rows))
        for r in rows:
            logger.debug("  %s", dict(r))

    results = temp_db.search_meetings(query)
    logger.debug("[DEBUG] Search for '%s' returned %d results", query, len(results))
    assert len(results) == expected_count