import logging
import os

logger = logging.getLogger(__name__)

def is_android():
    """Returns True if running on Android."""
    return sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ

def get_platform_name():
    if is_android():
        return "Android"
    return sys.platform

def get_app_data_path(app_name="MovieToText"):
    """Returns a safe path for storing app data depending on the platform."""
    if is_android():
        # On Android, we typically use the private app directory
        # Flet handles some of this, but for SQLite we need a stable path
        return "/data/data/com.example.movietotext/files" 
    
    # Windows/others
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, app_name)
