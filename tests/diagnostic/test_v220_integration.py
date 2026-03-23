from unittest.mock import MagicMock, patch

import pytest

from src.controllers.transcription_ctrl import TranscriptionController
from src.core.history_mgr import HistoryManager
from src.core.state import state


@pytest.fixture
def clean_env(tmp_path):
    # Setup temp DB
    db_file = tmp_path / "v220_test.db"
    history_mgr = HistoryManager(db_path=str(db_file))

    # Setup temp records DIR
    records_dir = tmp_path / "data/records"
    records_dir.mkdir(parents=True, exist_ok=True)

    # Mock transcriber
    transcriber = MagicMock()
    transcriber.get_hardware_info.return_value = {"device": "cpu"}
    transcriber.MODEL_REQUIREMENTS = {"base": 1.0}

    # Controller
    config_mgr = MagicMock()
    ctrl = TranscriptionController(config_mgr, transcriber)

    # Patch the global history_mgr inside controllers
    with patch("src.controllers.transcription_ctrl.history_mgr", history_mgr):
        with patch("os.getcwd", return_value=str(tmp_path)):
            yield ctrl, history_mgr, tmp_path


def test_comprehensive_workflow_v220(clean_env):
    ctrl, history_mgr, root_dir = clean_env

    # 1. Setup metadata in state
    state.set("project_name", "TestProject")
    state.set("category", "Integration, Test")

    # 2. Mock live manager to simulate recording
    mock_live = MagicMock()
    mock_live.stop.return_value = "This is a comprehensive test transcript."
    # The start_live_recording creates the path. Let's trace it.

    with patch("src.controllers.transcription_ctrl.LiveTranscriptionManager", return_value=mock_live):
        ctrl.start_live_recording("base", "system")
        assert state.get("is_recording") is True

        # Verify folder creation
        project_folder = root_dir / "data/records/TestProject"
        assert project_folder.exists()

        # Verify mp3 path in state
        mp3_path = state.get("current_mp3_path")
        assert "TestProject" in mp3_path
        mock_live.mp3_path = mp3_path

        # 3. Stop recording (triggers DB save)
        # Note: _stop_worker runs in a thread, but for testing we can call its logic or wait.
        # Here we simulation stop_live_recording's inner worker.
        full_text = mock_live.stop()
        history_mgr.add_meeting(
            title="Comprehensive Test",
            transcript=full_text,
            audio_path=mp3_path,
            project_name=state.get("project_name"),
            category=state.get("category"),
        )

    # 4. Verify Final State in DB
    meetings = history_mgr.get_all_meetings()
    assert len(meetings) == 1
    m = meetings[0]
    assert m["project_name"] == "TestProject"
    assert m["category"] == "Integration, Test"

    # 5. Verify Discovery (FTS5 Search)
    search_results = history_mgr.search_meetings("Integration")
    assert len(search_results) == 1
    assert search_results[0]["project_name"] == "TestProject"

    search_results_none = history_mgr.search_meetings("UnknownWord")
    assert len(search_results_none) == 0


def test_sanitization_v220(clean_env):
    ctrl, history_mgr, root_dir = clean_env
    # Attempt directory traversal
    state.set("project_name", "../../etc/passwd")

    mock_live = MagicMock()
    mock_live.stop.return_value = ".."
    with patch("src.controllers.transcription_ctrl.LiveTranscriptionManager", return_value=mock_live):
        ctrl.start_live_recording("base", "system")
        mp3_path = state.get("current_mp3_path")

        # Path should be inside data/records and sanitized
        # Convert to forward slashes for cross-platform checking
        normalized_path = mp3_path.replace("\\", "/")
        assert "data/records" in normalized_path
        assert ".." not in normalized_path
        # "../../etc/passwd" becomes "____etc_passwd" (safe)
        assert "____etc_passwd" in normalized_path

    # Check invalid FTS query
    res = history_mgr.search_meetings(' " * ')  # Should not crash
    assert isinstance(res, list)
