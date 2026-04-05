import logging
import os
import sys

import flet as ft

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logger  # noqa: E402
from src.app import main as app_main  # noqa: E402


def main(page: ft.Page):
    # Diagnostic log to verify if we even get here
    logging.info("main: Entered flet main function.")
    try:
        # Delegate to the platform-aware main in src.app
        app_main(page)
    except Exception as e:
        logging.error(f"CRITICAL: Failed to launch application: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Initialize professional logging
    setup_logger()
    
    # Launch Flet app
    # On desktop, this opens a window. On Android, this connects to the Flet view.
    ft.app(target=main)


def start_app_for_android():
    """
    Entry point for Chaquopy/Android if they don't call __main__.
    """
    setup_logger()
    ft.app(target=main)
