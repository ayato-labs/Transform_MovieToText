import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.event_bus import EVENT_TRANSCRIPTION_FINISHED, event_bus
from src.core.history_mgr import HistoryManager
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber


@pytest.fixture
def test_env(tmp_path):
    """Wait, this is an integration test, I'll use real components with mocks for hardware/LLM."""
    mock_config = Mock()
    mock_config.get_force_gpu.return_value = False
    mock_config.get_active_provider.return_value = "ollama_local"
    mock_config.get_provider_config.return_value = {"api_key": "fake", "base_url": "fake"}
    mock_config.get_last_model.return_value = "fake-m"

    long_text = "This is a very long transcription result that definitely exceeds both the fifty character limit for titles and the one hundred character limit for AI category extraction. It is long enough to trigger all AI logic paths. EXTRA CONTENT FOR 200 PLUS CHARACTERS."
    mock_transcriber = MagicMock(spec=WhisperTranscriber)
    mock_transcriber.transcribe.return_value = {"text": long_text, "segments": [{"start": 0.0, "end": 1.0, "text": "Something long."}]}

    # Use real in-memory history
    history_mgr = HistoryManager(db_path=":memory:")
    service = TranscriptionService(mock_config, mock_transcriber, history_mgr=history_mgr)
    # Patch the singleton inside the service/controller to use our test instance
    with patch("src.core.transcription_service._history_mgr", history_mgr), patch("src.controllers.transcription_ctrl.history_mgr", history_mgr):
        yield service, history_mgr, event_bus


def test_full_transcription_workflow_with_events(test_env, tmp_path):
    """
    Test the flow: Service calls -> Event Bus publishes -> Subscribed callback invoked -> DB updated.
    """
    service, history, bus = test_env

    fake_file = tmp_path / "video.mp4"
    fake_file.write_text("dummy video")

    events_received = []

    def on_finished(data):
        events_received.append(data)

    # Subscribe to the finished event
    bus.add_handler(EVENT_TRANSCRIPTION_FINISHED, on_finished)

    # Use MagicMock for LLM as allowed in integration tests
    mock_llm = MagicMock()
    mock_llm.generate_title.return_value = "Generated Title"
    mock_llm.extract_category.return_value = "Integrated"

    # Use LLMFactory.create_client as the patch target since it's imported into transcription_service
    with patch("src.core.transcription_service.LLMFactory.create_client", return_value=mock_llm):
        result = service.transcribe_file_sync(file_path=str(fake_file), model_name="base", project_name="Integrated")
        # Wait inside patch scope
        time.sleep(1.5)

        # 1. Verify Event Bus published
        assert len(events_received) == 1
        assert events_received[0]["text"] == long_text

        # 2. Verify DB through HistoryManager
        meeting_id = result["meeting_id"]
        meeting = history.get_meeting(meeting_id)
        assert meeting["title"] == "Generated Title (video.mp4)"
        assert meeting["category"] == "Integrated"


def test_live_recording_integration_abort(test_env):
    """Test that start_live_recording initializes the session correctly even if stopped quickly."""
    service, history, bus = test_env

    # Mock visual recorder to avoid threading issues in tests
    with patch("src.recorder.visual_recorder.visual_recorder.start"), patch("src.core.live_processor.LiveTranscriptionManager.start"):
        meeting_id = service.start_live_recording(model_name="m", source="System", project_name="IntegrationProject")

        assert meeting_id is not None
        assert service._current_meeting_id == meeting_id

        # Finalize (abort early)
        with patch("src.core.live_processor.LiveTranscriptionManager.stop", return_value=("", [])):
            service.stop_live_recording()
            # Stop logic is async in TranscriptionService, wait or join if needed
            # In unit/integration tests, we might want to check the status after a small delay
            time.sleep(0.1)

            # Since it was empty/short, it should have been deleted
            assert history.get_meeting(meeting_id) is None
