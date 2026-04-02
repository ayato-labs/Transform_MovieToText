import logging
from unittest.mock import MagicMock

import pytest

from src.controllers.history_ctrl import HistoryController
from src.core.history_mgr import HistoryManager
from src.core.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_history.db"
    return HistoryManager(db_path=str(db_file))


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get_force_gpu.return_value = False
    config.get_active_provider.return_value = "gemini"
    config.get_provider_config.return_value = {"api_key": "test_key"}
    config.get_last_model.return_value = "gemini-1.5-pro"
    return config


@pytest.fixture
def mock_transcriber():
    return MagicMock()


@pytest.fixture
def transcription_service(mock_config, mock_transcriber):
    return TranscriptionService(mock_config, mock_transcriber)


@pytest.fixture
def history_controller():
    return HistoryController()


def test_visual_context_persistence(temp_db):
    """Unit test for HistoryManager visual context methods."""
    meeting_id = temp_db.add_meeting(title="Visual Test", transcript="...", audio_path="...")

    # Add visual context
    temp_db.add_visual_context(meeting_id=meeting_id, timestamp_sec=10.5, image_path="/path/to/image1.jpg", description="Slide 1")
    temp_db.add_visual_context(meeting_id=meeting_id, timestamp_sec=20.0, image_path="/path/to/image2.jpg")

    # Retrieve and verify
    contexts = temp_db.get_visual_context(meeting_id)
    assert len(contexts) == 2
    assert contexts[0]["timestamp"] == 10.5
    assert contexts[0]["image_path"] == "/path/to/image1.jpg"
    assert contexts[1]["timestamp"] == 20.0


def test_delete_meeting_with_dependencies(temp_db):
    """Verify that deleting a meeting also cleans up FTS and Visual Context (Cascade)."""
    meeting_id = temp_db.add_meeting(title="Delete Test", transcript="Keyword: Avocado", audio_path="...")
    temp_db.add_visual_context(meeting_id, 5.0, "img.jpg")

    assert len(temp_db.search_meetings("Avocado")) == 1
    assert len(temp_db.get_visual_context(meeting_id)) == 1

    temp_db.delete_meeting(meeting_id)

    assert len(temp_db.get_all_meetings()) == 0
    assert len(temp_db.search_meetings("Avocado")) == 0
    assert len(temp_db.get_visual_context(meeting_id)) == 0


def test_generate_minutes_for_meeting_logic(transcription_service, temp_db, monkeypatch):
    """Integration test: Service -> LLM Client -> History Updates."""
    # Setup global history_mgr used in Service to use our temp_db
    monkeypatch.setattr("src.core.transcription_service._history_mgr", temp_db)
    transcription_service.history_mgr = temp_db

    meeting_id = temp_db.add_meeting(
        title="Minutes Test", transcript="Long enough transcript to pass the 50 char limit check..................", audio_path="..."
    )

    # Mock LLM Client
    mock_client = MagicMock()
    mock_client.transform.return_value = "Prompt with context"
    mock_client.generate_minutes.return_value = "AI Generated Summary"

    with monkeypatch.context() as m:
        m.setattr("src.llm.factory.LLMFactory.create_client", lambda *args, **kwargs: mock_client)

        minutes = transcription_service.generate_minutes_for_meeting(
            meeting_id, "Long enough transcript to pass the 50 char limit check.................."
        )

        assert minutes == "AI Generated Summary"
        # Verify DB updated
        meeting = temp_db.get_meeting(meeting_id)
        assert meeting["minutes"] == "AI Generated Summary"
        assert meeting["minutes_model"] == "gemini-1.5-pro"


def test_history_controller_bridge(history_controller, temp_db, monkeypatch):
    """Verify Controller correctly retrieves combined details."""
    monkeypatch.setattr("src.controllers.history_ctrl.history_mgr", temp_db)

    meeting_id = temp_db.add_meeting(title="Controller Test", transcript="...", audio_path="...")
    temp_db.add_visual_context(meeting_id, 1.0, "p1.jpg")

    details = history_controller.get_meeting_details(meeting_id)
    assert details["meeting"]["title"] == "Controller Test"
    assert len(details["visual_contexts"]) == 1
    assert details["visual_contexts"][0]["image_path"] == "p1.jpg"
