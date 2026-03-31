import time
from unittest.mock import Mock, patch

import pytest

from src.controllers.transcription_ctrl import TranscriptionController
from src.core.config_manager import ConfigManager
from src.core.history_mgr import HistoryManager
from src.core.state import state
from src.core.whisper_transcriber import WhisperTranscriber

LONG_TEXT = (
    "This is a very long transcription result that definitely exceeds both the fifty "
    "character limit for titles and the one hundred character limit for AI category "
    "extraction. It is long enough to trigger all AI logic paths. "
    "This is added text to ensure it's well over the limit."
)


@pytest.fixture
def system_setup():
    """Setup a full controller-service-repo stack with in-memory DB."""
    mock_config = Mock(spec=ConfigManager)
    mock_config.get_force_gpu.return_value = False
    mock_config.get_active_provider.return_value = "ollama_local"
    mock_config.get_provider_config.return_value = {"api_key": "fake", "base_url": "fake"}
    mock_config.get_last_model.return_value = "fake-m"
    mock_config.get_visual_capture_enabled.return_value = False

    mock_transcriber = Mock(spec=WhisperTranscriber)
    mock_transcriber.transcribe.return_value = {
        "text": LONG_TEXT,
        "segments": [{"start": 0.0, "end": 1.0, "text": "Something long."}]
    }

    # Reset global state for each test
    state.set("is_processing", False)
    state.set("status_text", "")

    # In-memory history for system test integration
    history = HistoryManager(db_path=":memory:")
    # Both the controller creates its own service AND it uses history_mgr singleton.
    with patch("src.controllers.transcription_ctrl.history_mgr", history), \
         patch("src.core.transcription_service._history_mgr", history):
        ctrl = TranscriptionController(mock_config, mock_transcriber)
        yield ctrl, history


def test_system_file_transcription_flow(system_setup, tmp_path):
    """
    Test the complete flow from Controller call to State update and DB persistence.
    """
    ctrl, history = system_setup

    test_file = tmp_path / "test_video.mp4"
    test_file.write_text("fake video data")

    # Mock LLM calls
    mock_llm = Mock()
    mock_llm.generate_title.return_value = "System Title"
    mock_llm.extract_category.return_value = "System Category"

    with patch("src.core.transcription_service.LLMFactory.create_client", return_value=mock_llm):
        # Trigger via controller
        # Force history injection
        ctrl.service.history_mgr = history

        ctrl.start_file_transcription(str(test_file), "base-model")
        # Wait inside patch scope for async worker with polling
        timeout = 5
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            meetings = history.get_all_meetings()
            if meetings and meetings[0].get("category") == "System Category":
                break
            time.sleep(0.1)

        meetings = history.get_all_meetings()
        assert len(meetings) == 1
        assert meetings[0]["title"] == "System Title (test_video.mp4)"
        assert meetings[0]["transcript"] == LONG_TEXT
        assert meetings[0]["category"] == "System Category"


def test_system_live_recording_flow(system_setup):
    """
    Test live recording flow: Start -> State updates -> Stop -> Finalize -> State updates.
    """
    ctrl, history = system_setup

    # Mock recorders
    with (
        patch("src.recorder.visual_recorder.visual_recorder.start"),
        patch("src.recorder.visual_recorder.visual_recorder.stop"),
        patch("src.core.live_processor.LiveTranscriptionManager.start"),
        patch(
            "src.core.live_processor.LiveTranscriptionManager.stop",
            return_value=(
                LONG_TEXT,
                [{"text": "Something long"}],
            ),
        ),
    ):
        # Mock LLM for metadata extraction
        mock_llm = Mock()
        mock_llm.generate_title.return_value = "Live Session"
        mock_llm.extract_category.return_value = "Live"

        # Force history injection
        ctrl.service.history_mgr = history

        with patch("src.core.transcription_service.LLMFactory.create_client", return_value=mock_llm):
            # 1. Start
            ctrl.start_live_transcription("base-model", "System")
            assert state.get("is_recording") is True
            assert state.get("transcript_text") == ""
            m_id = state.get("current_meeting_id")
            assert m_id is not None

            # Artificial delay to mimic recording
            time.sleep(0.2)

            # simulate time passed
            from itertools import count

            t_gen = count(int(time.time() + 60))
            with patch("time.time", side_effect=lambda: next(t_gen)):
                ctrl.stop_live_transcription()

            # Finalization is async
            timeout = 5
            start_time = time.time()
            while state.get("is_recording") and time.time() - start_time < timeout:
                time.sleep(0.1)

            # Wait inside patch scope for async worker with polling
            timeout = 5
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                if state.get("category") == "Live":
                    break
                time.sleep(0.1)

            # 3. Verify final state
            assert state.get("is_recording") is False
            assert state.get("transcript_text") == LONG_TEXT
            assert state.get("category") == "Live"

            # 4. Verify DB persistence
            meeting = history.get_meeting(m_id)
            assert meeting is not None
            assert (
                meeting["transcript"]
                == (
                    "This is a very long transcription result that definitely exceeds both the fifty character limit for titles "
                    "and the one hundred character limit for AI category extraction. It is long enough to trigger all AI "
                    "logic paths. EXTRA TEXT FOR 100+."
                )
            )
