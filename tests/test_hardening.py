import os
import sqlite3
import time
from unittest.mock import MagicMock, patch

from src.core.history_mgr import HistoryManager
from src.recorder import FFmpegRecorder


def test_history_mgr_db_locked():
    """Tests HistoryManager behavior when the DB is locked."""
    db_path = "lock_test.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Cleanup warning (test DB): {e}")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY)")
        conn.execute("BEGIN EXCLUSIVE")

        mgr = HistoryManager(db_path=db_path, timeout=0.1)
        res = mgr.add_meeting("Title", "Transcript", "audio.mp3")
        assert res is None
    finally:
        conn.close()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"Cleanup warning (lock_test.db): {e}")


def test_recorder_io_error_on_start():
    """Tests FFmpegRecorder when directory creation fails."""
    with patch("src.recorder.Path.mkdir") as mock_mkdir:
        mock_mkdir.side_effect = OSError("Permission Denied")

        recorder = FFmpegRecorder(mp3_path="error_test/audio.mp3")
        recorder.start()
        recorder.stop()


def test_recorder_ffmpeg_startup_failure():
    """Tests FFmpegRecorder when the ffmpeg command itself fails to launch."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.side_effect = FileNotFoundError("ffmpeg not found")

        recorder = FFmpegRecorder()
        recorder.start()
        time.sleep(0.5)
        assert not recorder.is_recording


def test_recorder_cleanup_on_exception():
    """Ensures FFmpeg process is terminated even if an exception occurs in the loop."""
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdout.read.return_value = b"\x00" * 4096

        # Set segment_time very low to trigger _push_chunk quickly
        recorder = FFmpegRecorder(segment_time=0.1)
        recorder.is_recording = True
        recorder.process = mock_process
        recorder.last_save_time = time.time() - 0.2  # Force immediate push

        with patch.object(recorder, "_push_chunk", side_effect=Exception("Sudden Crash")):
            # We don't use pytest.raises here because _record_loop catches all exceptions
            recorder._record_loop()

        assert mock_process.terminate.called or mock_process.kill.called
        assert not recorder.is_recording


def test_history_mgr_scaling():
    """Tests performance and stability with many records."""
    db_path = "scaling_test_v4.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Cleanup warning (test DB): {e}")

    mgr = HistoryManager(db_path=db_path)
    for i in range(100):
        mgr.add_meeting(f"Meeting {i}", "A" * 1000, f"path/to/{i}.mp3")

    start_time = time.time()
    meetings = mgr.get_all_meetings()
    duration = time.time() - start_time

    assert len(meetings) == 100
    assert duration < 1.0

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Cleanup warning (test DB): {e}")
