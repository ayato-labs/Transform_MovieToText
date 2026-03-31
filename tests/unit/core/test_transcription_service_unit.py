from unittest.mock import ANY, Mock, patch

import pytest

from src.core.config_manager import ConfigManager
from src.core.history_mgr import HistoryManager
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber
from tests.unit.llm.fake_llm_client import FakeLLMClient


@pytest.fixture
def mock_config():
    config = Mock(spec=ConfigManager)
    config.get_force_gpu.return_value = False
    config.get_active_provider.return_value = "ollama_local"
    config.get_provider_config.return_value = {"api_key": "fake", "base_url": "http://fb"}
    config.get_last_model.return_value = "m-1"
    config.get_visual_capture_enabled.return_value = False
    return config


@pytest.fixture
def mock_transcriber():
    transcriber = Mock(spec=WhisperTranscriber)
    long_text = "This is a very long transcription result that definitely exceeds both the fifty character limit for titles and the one hundred character limit for AI category extraction. It is long enough to trigger all AI logic paths. This is additional text to ensure we are well over the two hundred and fifty character threshold for robust testing purposes."
    transcriber.transcribe.return_value = {"text": long_text, "segments": [{"start": 0.0, "end": 1.0, "text": "Something very long indeed."}]}
    return transcriber


@pytest.fixture
def fake_history():
    """History manager with in-memory DB for pure unit testing."""
    return HistoryManager(db_path=":memory:")


@pytest.fixture
def service(mock_config, mock_transcriber, fake_history):
    with patch("src.core.transcription_service._history_mgr", fake_history):
        svc = TranscriptionService(mock_config, mock_transcriber)
        yield svc


def test_transcribe_file_sync_logic(service, mock_transcriber, tmp_path):
    """Verify the orchestration logic of transcribe_file_sync."""
    fake_file = tmp_path / "test.mp3"
    fake_file.write_text("audio data")

    # Mock LLM calls to use FakeLLMClient instead of MagicMock
    fake_llm = FakeLLMClient()

    with (
        patch("src.core.transcription_service.LLMFactory.create_client", return_value=fake_llm),
        patch("src.core.event_bus.event_bus.publish") as mock_publish,
    ):
        result = service.transcribe_file_sync(str(fake_file), model_name="base", project_name="TestProj")

        assert result["transcript"] == "This is a sufficiently long transcription result that exceeds the fifty character limit for AI processing."
        assert result["meeting_id"] is not None

        # Verify FakeLLM was used correctly
        title_call = next(c for c in fake_llm.recorded_calls if c["method"] == "generate_title")
        assert "This is a very long" in title_call["transcript"]

        # Verify events were published
        mock_publish.assert_any_call("status_update", "文字起こし実行中...")
        mock_publish.assert_any_call("transcription_finished", ANY)


def test_generate_minutes_for_meeting_unit(service, fake_history):
    """Test generating minutes using the FakeLLM (no MagicMock)."""
    m_id = fake_history.add_meeting("T", "Some transcription text that is long enough to pass validation.", "a.mp3")

    fake_llm = FakeLLMClient()

    with patch("src.llm.factory.LLMFactory.create_client", return_value=fake_llm):
        minutes = service.generate_minutes_for_meeting(m_id, "Some transcription text that is long enough to pass validation.")

        assert "偽の議事録" in minutes

        # Verify DB updated
        meeting = fake_history.get_meeting(m_id)
        assert meeting["minutes"] == minutes
        assert meeting["minutes_model"] == service.config_mgr.get_last_model()


def test_stop_live_recording_early_cancellation(service):
    """Verify that stopping before live_mgr is ready handles cancellation cleanly."""
    service.live_mgr = None  # Not started

    finalize_mock = Mock()
    service.stop_live_recording(finalize_callback=finalize_mock)

    assert service._cancel_event.is_set()
    finalize_mock.assert_called_with("", "")
