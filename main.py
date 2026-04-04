import logging
import traceback

from src.utils.logger import setup_logger

# Initialize logger as the very first thing (Highest Priority)
setup_logger()
logging.info("--- Python Startup: Logger Initialized ---")

import flet as ft  # noqa: E402

from src.app import FletApp  # noqa: E402

# No longer need separate setup_logging here as it's done via src.logger


def main(page: ft.Page):
    # Diagnostic log to verify if we even get here
    logging.info("main: Entered flet main function.")
    try:
        FletApp(page)
    except Exception as e:
        logging.error(f"Flet App initialization failed: {e}")
        logging.error(traceback.format_exc())
        raise


def start_app_for_android():
    """Entry point for Android/Chaquopy."""
    import threading
    logging.info("Starting Flet app via Android thread...")
    # Start Flet in a separate thread to not block Java main thread
    threading.Thread(target=lambda: ft.app(target=main, port=8551, view=ft.AppView.WEB_BROWSER), daemon=True).start()


if __name__ == "__main__":
    logging.info("Starting main process...")
    ft.app(target=main)
