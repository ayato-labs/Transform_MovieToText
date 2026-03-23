from unittest.mock import MagicMock, patch

from src.recorder.audio_recorder import AudioRecorder
from src.recorder.ffmpeg import FFmpegRecorder


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


def test_audio_recorder_mp3_logic():
    with patch("soundcard.default_microphone") as mock_mic, patch("subprocess.Popen") as mock_popen, patch("threading.Thread"):
        mock_mic.return_value.name = "TestMic"
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        recorder = AudioRecorder(mp3_path="test_mic.mp3")
        recorder.start()

        # AudioRecorder should start a background FFmpeg process for MP3
        mock_popen.assert_called()
        command = mock_popen.call_args[0][0]
        assert "test_mic.mp3" in command
        assert "audio=TestMic" in command

        recorder.stop()
        mock_process.terminate.assert_called()
