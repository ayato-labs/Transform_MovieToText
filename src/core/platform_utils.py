import logging
import os
import sys

logger = logging.getLogger(__name__)


def is_android():
    """Returns True if running on Android."""
    # Specialization: Force False on Windows unless explicitly forced via env
    if sys.platform == "win32":
        return os.environ.get("FORCE_ANDROID_MODE") == "1"
    return sys.platform == "android"


def get_platform_name():
    if is_android():
        return "Android"
    return sys.platform


def get_roaming_app_data_path(app_name="TransformMovieToText"):
    """Returns path for settings/DBs (syncable across devices in domain)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, app_name)
    os.makedirs(path, exist_ok=True)
    return path


def get_local_app_data_path(app_name="TransformMovieToText"):
    """Returns path for heavy binary data (not synced, local to machine)."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, app_name)
    os.makedirs(path, exist_ok=True)
    return path


def get_app_data_path(app_name="TransformMovieToText"):
    """Legacy wrapper for compatibility, returns roaming path."""
    return get_roaming_app_data_path(app_name)


def get_log_path():
    """Returns the absolute path to the app's debug log file."""
    base_path = get_roaming_app_data_path()
    log_dir = os.path.join(base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "app_debug.log")
