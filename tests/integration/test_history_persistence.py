import os
import shutil
import pytest
from src.core.history_mgr import HistoryManager

@pytest.fixture
def temp_db(tmp_path):
    """
    Creates a temporary database for testing.
    """
    db_file = tmp_path / "test_history.db"
    mgr = HistoryManager(db_path=str(db_file))
    yield mgr
    # Cleanup is handled by tmp_path fixture

def test_add_and_get_meeting(temp_db):
    """
    Test basic CRUD operations on meetings.
    """
    title = "Test Meeting"
    transcript = "This is a test transcript."
    audio_path = "tests/fixtures/dummy.mp3"
    
    meeting_id = temp_db.add_meeting(
        title=title,
        transcript=transcript,
        audio_path=audio_path,
        project_name="UnitTesting"
    )
    
    assert meeting_id > 0
    
    meeting = temp_db.get_meeting(meeting_id)
    assert meeting is not None
    assert meeting["title"] == title
    assert meeting["transcript"] == transcript
    assert meeting["project_name"] == "UnitTesting"

def test_search_meetings(temp_db):
    """
    Test FTS5 search functionality.
    """
    temp_db.add_meeting("Weekly sync", "We discussed the budget and roadmap.", "path1")
    temp_db.add_meeting("Design Review", "Focused on the UI and layout.", "path2")
    
    # Search for 'budget'
    results = temp_db.search_meetings("budget")
    assert len(results) == 1
    assert results[0]["title"] == "Weekly sync"
    
    # Search for 'UI'
    results = temp_db.search_meetings("UI")
    assert len(results) == 1
    assert results[0]["title"] == "Design Review"

def test_update_minutes(temp_db):
    """
    Test updating minutes field and FTS synchronization.
    """
    meeting_id = temp_db.add_meeting("Intro", "Hello world", "path")
    
    temp_db.update_minutes(meeting_id, "Summary: Hello was said.", model_name="gemini-pro")
    
    meeting = temp_db.get_meeting(meeting_id)
    assert meeting["minutes"] == "Summary: Hello was said."
    assert meeting["minutes_model"] == "gemini-pro"
    
    # Verify FTS also finds it
    results = temp_db.search_meetings("Summary")
    assert len(results) == 1
