import pytest

from src.core.history_mgr import HistoryManager


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
    assert meeting_id == 1

    meetings = temp_db.get_all_meetings()
    assert len(meetings) == 1
    assert meetings[0]["title"] == "Test Meeting"
    assert meetings[0]["project_name"] == "AI Research"
    assert meetings[0]["category"] == "AI, Development"


def test_search_fts5(temp_db):
    temp_db.add_meeting(title="Meeting A", transcript="Secret recipe", project_name="Cookbook", audio_path="a.mp3")
    temp_db.add_meeting(title="Meeting B", transcript="Rust vs Python", project_name="Dev", audio_path="b.mp3")
    temp_db.add_meeting(title="Meeting C", transcript="AI models", project_name="AI Research", category="AI", audio_path="c.mp3")

    # Search by transcript
    results = temp_db.search_meetings("Secret")
    assert len(results) == 1
    assert results[0]["title"] == "Meeting A"

    # Search by project_name
    results = temp_db.search_meetings("Dev")
    assert len(results) == 1
    assert results[0]["title"] == "Meeting B"

    # Search by category
    results = temp_db.search_meetings("AI")
    assert len(results) == 1
    assert results[0]["title"] == "Meeting C"


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
    temp_db.update_minutes(meeting_id, "Summary of meeting")
    meetings = temp_db.get_all_meetings()
    assert meetings[0]["minutes"] == "Summary of meeting"


def test_get_single_meeting(temp_db):
    meeting_id = temp_db.add_meeting(title="Single", transcript="...", audio_path="...")
    meeting = temp_db.get_meeting(meeting_id)
    assert meeting["title"] == "Single"
    assert temp_db.get_meeting(999) is None
