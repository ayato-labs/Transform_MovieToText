import logging
import os
import sys

# SECURITY: Enforce 100% Local AI communication.
# Setting OLLAMA_HOST ensures both the CLI and SDK default to loopback.
os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"

import flet as ft

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import main as app_main  # noqa: E402
from src.core.migrator import migrate_legacy_data  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402


def main(page: ft.Page):
    # Diagnostic log to verify if we even get here
    logging.info("main: Entered flet main function.")
    try:
        # Delegate to the desktop main in src.app
        app_main(page)
    except Exception as e:
        logging.error(f"CRITICAL: Failed to launch application: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Initialize essential directories (AppData)
    from src.core.platform_utils import initialize_app_dirs
    initialize_app_dirs()

    # Initialize professional logging
    setup_logger()

    # Perform one-time migration to AppData if needed
    migrate_legacy_data()

    # Launch Flet app as a desktop window
    ft.app(target=main)
