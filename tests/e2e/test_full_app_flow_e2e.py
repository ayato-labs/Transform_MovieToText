import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.config_manager import ConfigManager
from src.core.history_mgr import HistoryManager
from src.core.transcription_service import TranscriptionService
from src.core.whisper_transcriber import WhisperTranscriber


@pytest.fixture
def mock_managers():
    """Returns mocked config and in-memory history manager."""
    config_mgr = MagicMock(spec=ConfigManager)
    config_mgr.get_force_gpu.return_value = False

    # In-memory history manager
    history_mgr = HistoryManager(db_path=":memory:")
    return config_mgr, history_mgr


def test_full_file_transcription_flow(mock_managers):
    """
    Simulates the full user flow:
    File Select -> Transcribe -> Save to History -> Generate Title.
    """
    config_mgr, history_mgr = mock_managers

    # 1. Mock dependencies
    long_text = (
        "This is a very long transcription result that definitely exceeds both the fifty character limit for titles "
        "and the one hundred character limit for AI category extraction. It is long enough to trigger all AI logic paths. "
        "This is additional text to ensure we are well over the two hundred character threshold for testing purposes."
    )
    mock_transcriber = MagicMock(spec=WhisperTranscriber)
    mock_transcriber.transcribe.return_value = {"text": long_text, "segments": [{"start": 0.0, "end": 1.0, "text": "Something very long indeed."}]}

    # Mock LLM for title generation
    with patch("src.core.transcription_service.LLMFactory.create_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.generate_title.return_value = "Generated AI Title"
        mock_client.extract_category.return_value = "AI Technology"
        mock_factory.return_value = mock_client

        # 2. Setup Service - INJECT history_mgr to ensure consistency
        service = TranscriptionService(config_mgr, mock_transcriber, history_mgr=history_mgr)

        # 3. Simulate file transcription
        # We mock os.path.exists to 'find' the dummy file
        with (
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
            patch("src.core.transcription_service.WhisperTranscriber", return_value=mock_transcriber),
        ):
            result = service.transcribe_file_sync(file_path="dummy_audio.mp3", model_name="tiny", project_name="E2EProject", category="E2E")

            # Wait inside patch scope for async worker with polling
            timeout = 5
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                saved = history_mgr.get_meetings_filtered(project_names=["E2EProject"])
                if saved and saved[0].get("category") == "AI Technology":
                    break
                time.sleep(0.1)

            # 4. Verify Result
            assert "meeting_id" in result
            assert result["transcript"] == long_text

            # 5. Check Database Persistence
            saved = history_mgr.get_meetings_filtered(project_names=["E2EProject"])
            assert len(saved) == 1
            assert saved[0]["title"] == "Generated AI Title"
            assert saved[0]["category"] == "AI Technology"  # Overwritten by AI
            assert saved[0]["model_info"] == "tiny"
