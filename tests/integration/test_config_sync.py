import pytest

from src.core.config_manager import ConfigManager


@pytest.fixture
def temp_config(tmp_path):
    """
    Creates a temporary config file for testing.
    """
    config_file = tmp_path / "test_config.json"
    mgr = ConfigManager(config_path=str(config_file))
    yield mgr


def test_config_persistence(temp_config):
    """
    Verify settings are saved to disk and can be reloaded.
    """
    # Set a custom value
    temp_config.set_whisper_model("medium")
    temp_config.set_force_gpu(True)
    temp_config.set_active_provider("ollama_local")

    # Create a new manager instance reading the same file
    new_mgr = ConfigManager(config_path=temp_config.config_path)

    assert new_mgr.get_whisper_model() == "medium"
    assert new_mgr.get_force_gpu() is True
    assert new_mgr.get_active_provider() == "ollama_local"


def test_provider_specific_config(temp_config):
    """
    Test setting and getting provider-specific settings.
    """
    full_conf = {"api_key": "test_key", "model": "gpt-4", "base_url": "http://localhost"}
    temp_config.set_provider_config("custom_provider", full_conf)

    retrieved = temp_config.get_provider_config("custom_provider")
    assert retrieved["api_key"] == "test_key"
    assert retrieved["model"] == "gpt-4"
