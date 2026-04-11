import sys
from unittest.mock import MagicMock, patch

import pytest

from src.platforms.desktop.recorder.audio_recorder import AudioRecorder
from src.platforms.desktop.recorder.ffmpeg import FFmpegRecorder


def test_ffmpeg_recorder_command():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        recorder = FFmpegRecorder(mp3_path="test.mp3")
        recorder.start()

        # Wait a bit for thread to start and call popen
        import time

        for _ in range(10):
            if mock_popen.called:
                break
            time.sleep(0.1)

        # Check if FFmpeg was called with the right dual-output flags
        assert mock_popen.called
        args, kwargs = mock_popen.call_args
        command = args[0]

        assert "ffmpeg" in command
        assert "test.mp3" in command
        assert "-f" in command
        assert "f32le" in command  # For pipe output

        recorder.stop()
        mock_process.terminate.assert_called()


@pytest.mark.skipif(sys.platform != "win32", reason="pyaudiowpatch is Windows-only")
def test_audio_recorder_start_stop():
    with patch("src.platforms.desktop.recorder.audio_recorder.pyaudio.PyAudio") as mock_pa:
        mock_pa.return_value.get_default_input_device_info.return_value = {"name": "TestMic"}
        mock_stream = MagicMock()
        mock_pa.return_value.open.return_value = mock_stream

        recorder = AudioRecorder(mp3_path="test_mic.mp3")
        recorder.start()

        # AudioRecorder should initialize PyAudio
        mock_pa.assert_called()

        recorder.stop()
        mock_stream.stop_stream.assert_called()
        mock_stream.close.assert_called()
        mock_pa.return_value.terminate.assert_called()