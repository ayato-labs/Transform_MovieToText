import logging
import os
import warnings

import flet as ft

# Suppress HuggingFace and Requests warnings before other imports
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

logger = logging.getLogger(__name__)

try:
    from requests.exceptions import RequestsDependencyWarning

    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    logger.debug("RequestsDependencyWarning not available, skipping filter.")

from src.core.platform_utils import get_log_path, is_android


def main(page: ft.Page):
    """
    Platform-specific delegation.
    Detects if running on Android or Desktop and launches the appropriate FletApp.
    """
    if is_android():
        logger.info("Main: Android detected. Launching AndroidApp.")
        from src.platforms.android.app import AndroidApp

        AndroidApp(page)
    else:
        logger.info("Main: Desktop detected. Launching DesktopApp.")
        from src.platforms.desktop.app import DesktopApp

        DesktopApp(page)


def init_logging():
    log_file = get_log_path()
    # Basic config for stdout
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Add FileHandler for persistent logs on Android
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")

    # Global exception handler
    import sys

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


if __name__ == "__main__":
    init_logging()
    ft.app(target=main)
