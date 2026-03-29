from unittest.mock import MagicMock

from src.core.whisper_transcriber import WhisperTranscriber


def test_whisper_load_model_fallback(mocker):
    """
    Test that WhisperTranscriber falls back to int8_float16 on memory failure.
    """
    # Mock WhisperModel to fail first then succeed on retry
    mock_model_class = mocker.patch("src.core.whisper_transcriber.WhisperModel")

    # First call raises MKL memory error
    mock_model_class.side_effect = [
        Exception("mkl_malloc: memory allocation failed"),
        MagicMock(),  # Second call (fallback) succeeds
    ]

    transcriber = WhisperTranscriber()
    # Should not raise exception because of fallback
    transcriber.load_model("tiny", force_gpu=False)

    assert mock_model_class.call_count == 2
    # Verify second call used the fallback compute_type
    assert mock_model_class.call_args_list[1].kwargs["compute_type"] == "int8_float16"
