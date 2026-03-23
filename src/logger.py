import datetime
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to terminal output."""

    # ANSI escape sequences for colors
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    CYAN = "\x1b[36;20m"
    RESET = "\x1b[0m"

    FORMAT = "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"

    FORMATS = {
        logging.DEBUG: CYAN + FORMAT + RESET,
        logging.INFO: GREY + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger():
    """
    Sets up a robust rotating file logger and colorized terminal output.
    This should be called as early as possible.
    """
    log_file = "app.log"
    max_size = 10 * 1024 * 1024  # 10MB
    backup_count = 5

    # Check if DEBUG mode is enabled via environment variable
    debug_mode = os.environ.get("APP_DEBUG", "0") == "1"
    log_level = logging.DEBUG if debug_mode else logging.INFO

    try:
        # Standard format for file logging (No colors)
        file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s (%(filename)s:%(lineno)d): %(message)s")

        # File Handler (Rotating)
        file_handler = RotatingFileHandler(log_file, maxBytes=max_size, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(file_formatter)

        # Stream Handler (Console) - Using Custom Color Formatter
        stream_handler = logging.StreamHandler(sys.stdout)
        # Only use colors if we are in a terminal that supports it
        if sys.stdout.isatty():
            stream_handler.setFormatter(ColorFormatter())
        else:
            stream_handler.setFormatter(file_formatter)

        # Root Logger setup
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clean existing handlers to avoid duplicates during re-init
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"--- 🚀 APP START at {now} ---")
        logging.info("Traceability: Module names and line numbers are now included in all logs.")

    except Exception as e:
        # Fallback for lock contention or permission issues
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"Could not initialize RotatingFileHandler: {e}. Falling back to basic logging.")


if __name__ == "__main__":
    setup_logger()
    logging.debug("This is a debug message (Cyan)")
    logging.info("This is an info message (Grey)")
    logging.warning("This is a warning message (Yellow)")
    logging.error("This is an error message (Red)")
    logging.critical("This is a critical message (Bold Red)")
