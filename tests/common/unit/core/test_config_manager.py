from unittest.mock import patch

from src.core.config_manager import ConfigManager


def test_config_manager_save_load(tmp_path):
    with patch("os.getenv", return_value=None):
        config_file = tmp_path / "test_config.json"
        mgr = ConfigManager(config_path=str(config_file))

        # Initial state for gemini
        gemini_config = mgr.get_provider_config("gemini")
        assert gemini_config.get("api_key", "") == ""

        # Set and save
        mgr.set_provider_config("gemini", {"api_key": "test_key"})
        mgr.set_last_model("gemini-1.5-flash", "gemini")

        # Reload from new instance
        mgr2 = ConfigManager(config_path=str(config_file))
        reloaded_config = mgr2.get_provider_config("gemini")
        assert reloaded_config.get("api_key") == "test_key"
        assert mgr2.get_last_model("gemini") == "gemini-1.5-flash"


def test_config_manager_invalid_json(tmp_path):
    with patch("os.getenv", return_value=None):
        config_file = tmp_path / "invalid.json"
        config_file.write_text("invalid json content")

        mgr = ConfigManager(config_path=str(config_file))
        # Should handle error and return empty dict/settings
        gemini_config = mgr.get_provider_config("gemini")
        assert gemini_config.get("api_key", "") == ""