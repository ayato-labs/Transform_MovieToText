import pytest

from src.core.db.connection import DatabaseConnection
from src.core.db.repositories import MeetingRepository, VisualContextRepository


@pytest.fixture
def db_conn():
    """In-memory database connection for testing."""
    # Use ":memory:" for pure unit testing without side effects.
    # Note: sqlite3 is already imported in the repo files.
    return DatabaseConnection(":memory:")



@pytest.fixture
def meeting_repo(db_conn):
    repo = MeetingRepository(db_conn)
    repo.init_db()
    return repo


@pytest.fixture
def visual_repo(db_conn):
    repo = VisualContextRepository(db_conn)
    repo.init_db()
    return repo


def test_meeting_repository_add_get(meeting_repo):
    """Test basic Add and Get operations."""
    m_id = meeting_repo.add(title="Test Meeting", transcript="Hello World", audio_path="test.mp3", project_name="UnitTests", category="Dev")
    assert m_id > 0

    meeting = meeting_repo.get(m_id)
    assert meeting["title"] == "Test Meeting"
    assert meeting["transcript"] == "Hello World"
    assert meeting["project_name"] == "UnitTests"
    assert meeting["category"] == "Dev"


def test_meeting_repository_update(meeting_repo):
    """Test Update operation including FTS sync."""
    m_id = meeting_repo.add(title="Old Title", transcript="Old content", audio_path="old.mp3")

    meeting_repo.update(m_id, title="New Title", category="Refactored")

    updated = meeting_repo.get(m_id)
    assert updated["title"] == "New Title"
    assert updated["category"] == "Refactored"

    # Verify FTS search reflects updates
    results = meeting_repo.search_filtered(search_query="Refactored")
    assert len(results) == 1
    assert results[0]["id"] == m_id


def test_meeting_repository_search_fts(meeting_repo):
    """Test full-text search integration."""
    meeting_repo.add("Alpha", "The quick brown fox", "a.mp3")
    meeting_repo.add("Beta", "Jumps over the lazy dog", "b.mp3")

    # Search by keyword
    results = meeting_repo.search_filtered(search_query="fox")
    assert len(results) == 1
    assert results[0]["title"] == "Alpha"

    # Search by keyword in different field
    results = meeting_repo.search_filtered(search_query="Beta")
    assert len(results) == 1
    assert results[0]["transcript"] == "Jumps over the lazy dog"


def test_visual_context_repository(meeting_repo, visual_repo):
    """Test VisualContextRepository operations."""
    m_id = meeting_repo.add("Visual Meeting", "...", "v.mp3")

    visual_repo.add(m_id, 10.5, "path/to/frame.jpg", description="Screenshot 1")
    visual_repo.add(m_id, 20.0, "path/to/second.jpg", description="Screenshot 2")

    contexts = visual_repo.get_by_meeting(m_id)
    assert len(contexts) == 2
    assert contexts[0]["timestamp"] == 10.5
    assert contexts[1]["description"] == "Screenshot 2"


def test_meeting_delete_cascades(meeting_repo, visual_repo):
    """Verify that deleting a meeting cleans up visual context (if implemented with constraints)."""
    m_id = meeting_repo.add("Delete Me", "...", "d.mp3")
    visual_repo.add(m_id, 1.0, "img.jpg")

    meeting_repo.delete(m_id)

    assert meeting_repo.get(m_id) is None
    # Visual context table has FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
    assert len(visual_repo.get_by_meeting(m_id)) == 0


def test_json_segments_storage(meeting_repo):
    """Verify transcript segments are stored as JSON strings and retrieved as dicts."""
    segments = [{"start": 0.0, "end": 1.0, "text": "Hello"}]
    m_id = meeting_repo.add("Segments Test", "Hello", "s.mp3", transcript_segments=segments)

    meeting = meeting_repo.get(m_id)
    assert isinstance(meeting["transcript_segments"], list)
    assert meeting["transcript_segments"][0]["text"] == "Hello"

    # Test update segments
    new_segments = [{"start": 1.0, "end": 2.0, "text": "World"}]
    meeting_repo.update(m_id, transcript_segments=new_segments)
    updated = meeting_repo.get(m_id)
    assert updated["transcript_segments"][0]["text"] == "World"
