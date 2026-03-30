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
    transcriber = MagicMock(spec=WhisperTranscriber)
    transcriber.transcribe_numpy.return_value = "This is the transcript."
    
    # Mock LLM for title generation
    with patch("src.llm.factory.LLMFactory.create_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.generate_title.return_value = "Generated AI Title"
        mock_client.extract_category.return_value = "AI Technology"
        mock_factory.return_value = mock_client
        
        # 2. Setup Service
        service = TranscriptionService(config_mgr, transcriber)
        
        # 3. Simulate file transcription
        # We mock os.path.exists to 'find' the dummy file
        with patch("os.path.exists", return_value=True), \
             patch("src.core.transcription_service.history_mgr", history_mgr), \
             patch("src.core.transcription_service.WhisperTranscriber", return_value=transcriber):
            
            # We don't want to actually load audio from disk
            with patch("src.core.whisper_transcriber.WhisperTranscriber.transcribe_file", return_value="Transcription result"):
                
                result = service.transcribe_file_sync(
                    file_path="dummy_audio.mp3",
                    model_name="tiny",
                    project_name="E2EProject",
                    category="E2E"
                )
                
                # 4. Verify Result
                assert "meeting_id" in result
                assert result["transcript"] == "Transcription result"
                
                # 5. Check Database Persistence
                saved = history_mgr.get_meetings_filtered(project_filter="E2EProject")
                assert len(saved) == 1
                assert "Generated AI Title" in saved[0]["title"]
                assert saved[0]["project_name"] == "E2EProject"
                assert saved[0]["category"] == "AI Technology" # Overwritten by AI
                assert saved[0]["model_info"] == "tiny"
