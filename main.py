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


if __name__ == "__main__":
    logging.info("Starting main process...")
    ft.app(target=main)
