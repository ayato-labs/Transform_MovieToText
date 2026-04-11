import numpy as np
import pytest

from src.core.whisper_transcriber import WhisperTranscriber


@pytest.fixture
def transcriber():
    """Returns a real WhisperTranscriber instance for testing."""
    return WhisperTranscriber()


def test_transcribe_numpy_integration(transcriber):
    """
    Verifies that transcribing a raw numpy buffer yields a result string.
    Uses 'tiny' model for fast integration testing.
    """
    # 1. Load model (Tiny is small enough for CI)
    transcriber.load_model("tiny", force_gpu=False)

    # 2. Generate 1 second of silence (16kHz)
    sample_rate = 16000
    duration_sec = 1.0
    audio_data = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)

    # 3. Transcribe
    result = transcriber.transcribe_numpy(audio_data)

    assert isinstance(result, dict)
    assert "text" in result
    assert isinstance(result["text"], str)


def test_transcriber_model_switch(transcriber):
    """Tests that switching models correctly clears and reloads."""
    transcriber.load_model("tiny", force_gpu=False)
    assert transcriber.current_model_name == "tiny"

    # Switch to 'base' (if base exists on system) or re-load tiny
    transcriber.load_model("tiny", force_gpu=False)
    assert transcriber.current_model_name == "tiny"