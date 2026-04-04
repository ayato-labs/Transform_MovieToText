import pytest

from src.core.history_mgr import HistoryManager


@pytest.fixture
def mock_history_mgr():
    # Ensure tables are created
    return HistoryManager(db_path=":memory:")


def test_add_and_get_meeting(mock_history_mgr):
    """Tests adding a meeting and retrieving it by ID."""
    meeting_id = mock_history_mgr.add_meeting(
        title="Test Meeting",
        transcript="This is a test transcript.",
        audio_path="test.mp3",
        model_info="base",
        project_name="TestProject",
        category="Test",
    )

    assert meeting_id > 0
    # Use get_meeting to be sure we are checking the one we just added
    meeting = mock_history_mgr.get_meeting(meeting_id)
    assert meeting["title"] == "Test Meeting"
    assert meeting["project_name"] == "TestProject"


def test_filtering_by_project(mock_history_mgr):
    """Tests filtering meetings by project name."""
    mock_history_mgr.add_meeting("M1", "T1", "A1", "m", "P1", "c")
    mock_history_mgr.add_meeting("M2", "T2", "A2", "m", "P2", "c")

    p1_meetings = mock_history_mgr.get_meetings_filtered(project_names=["P1"])
    assert len(p1_meetings) == 1
    assert p1_meetings[0]["title"] == "M1"


def test_delete_project_and_migrate(mock_history_mgr):
    """Tests project deletion with data migration to 'その他'."""
    mock_history_mgr.add_meeting("M1", "T1", "A1", "m", "ToDelete", "c")

    # Verify it exists
    assert len(mock_history_mgr.get_meetings_filtered(project_names=["ToDelete"])) == 1

    # Delete and migrate
    mock_history_mgr.delete_project("ToDelete")

    # Should be gone from 'ToDelete'
    assert len(mock_history_mgr.get_meetings_filtered(project_names=["ToDelete"])) == 0

    # Should be moved to 'その他'
    others = mock_history_mgr.get_meetings_filtered(project_names=["その他"])
    assert len(others) >= 1
    assert any(m["title"] == "M1" for m in others)
