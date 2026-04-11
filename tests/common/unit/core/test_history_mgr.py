import logging

import pytest

from src.core.history_mgr import HistoryManager

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_history.db"
    mgr = HistoryManager(db_path=str(db_file))
    yield mgr
    # Connection is handled by HistoryManager (context manager style or persistent)
    # Since HistoryManager currently doesn't have a close() method, we just let it be.


def test_add_and_get_meeting(temp_db):
    meeting_id = temp_db.add_meeting(
        title="Test Meeting",
        transcript="Hello world, we are talking about AI and Python.",
        audio_path="test.mp3",
        model_info="base",
        project_name="AI Research",
        category="AI, Development",
    )
    logger.debug(f"DEBUG: Created meeting ID: {meeting_id}")
    assert meeting_id > 0

    meetings = temp_db.get_all_meetings()
    assert len(meetings) == 1
    m = meetings[0]
    logger.debug(f"DEBUG: Retrieved meeting: {m}")
    assert m["title"] == "Test Meeting"
    assert m["project_name"] == "AI Research"
    assert m["category"] == "AI, Development"
    assert "minutes_model" in m


def test_search_fts5(temp_db):
    temp_db.add_meeting(title="Secret Meeting", transcript="The keyword is Banana", project_name="Cookbook", audio_path="a.mp3")

    # Verify row counts directly
    import sqlite3

    conn = sqlite3.connect(temp_db.db_path)
    f_count = conn.execute("SELECT COUNT(*) FROM meetings_fts").fetchone()[0]
    conn.close()
    assert f_count == 1, "FTS5 table should have 1 entry"

    # Search by transcript
    results = temp_db.search_meetings("Banana")
    assert len(results) == 1
    assert results[0]["title"] == "Secret Meeting"


def test_get_projects(temp_db):
    temp_db.add_meeting(title="M1", transcript="..", audio_path="..", project_name="Project X")
    temp_db.add_meeting(title="M2", transcript="..", audio_path="..", project_name="Project Y")
    temp_db.add_meeting(title="M3", transcript="..", audio_path="..", project_name="Project X")  # Duplicate

    projects = temp_db.get_projects()
    assert len(projects) == 2
    assert "Project X" in projects
    assert "Project Y" in projects


def test_update_minutes(temp_db):
    meeting_id = temp_db.add_meeting(title="Test Meeting", transcript="Hello world", audio_path="test.mp3")
    temp_db.update_minutes(meeting_id, "Summary of meeting", model_name="gemini-pro")

    meeting = temp_db.get_meeting(meeting_id)
    assert meeting["minutes"] == "Summary of meeting"
    assert meeting["minutes_model"] == "gemini-pro"


def test_delete_meeting(temp_db):
    meeting_id = temp_db.add_meeting(title="To be deleted", transcript="...", audio_path="...")
    assert len(temp_db.get_all_meetings()) == 1

    temp_db.delete_meeting(meeting_id)
    assert len(temp_db.get_all_meetings()) == 0


def test_get_single_meeting(temp_db):
    meeting_id = temp_db.add_meeting(title="Single", transcript="...", audio_path="...")
    meeting = temp_db.get_meeting(meeting_id)
    assert meeting["title"] == "Single"
    assert temp_db.get_meeting(999) is None