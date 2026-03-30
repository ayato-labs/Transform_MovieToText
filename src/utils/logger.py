import datetime
import logging
import os
import platform
import sys
from collections import deque
from logging.handlers import RotatingFileHandler

try:
    import colorlog
except ImportError:
    colorlog = None

# Global buffer for UI log viewing
LOG_BUFFER = deque(maxlen=200)


class DequeHandler(logging.Handler):
    """Custom handler to store logs in a memory buffer (deque)."""

    def emit(self, record):
        try:
            msg = self.format(record)
            LOG_BUFFER.append(msg)
        except Exception:
            self.handleError(record)


def get_system_info():
    """Captures basic system and hardware diagnostics."""
    info = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }

    # Use psutil for RAM info (consistent across OS, much faster than subprocess)
    try:
        import psutil

        ram_total = psutil.virtual_memory().total
        info["ram_gb"] = round(ram_total / (1024**3), 1)
    except Exception:
        info["ram_gb"] = "Unknown"

    # Try to detect GPU
    try:
        import subprocess

        gpu_cmd = "nvidia-smi --query-gpu=name --format=csv,noheader"
        gpu_info = subprocess.check_output(gpu_cmd, shell=True).decode().strip()
        info["gpu"] = gpu_info if gpu_info else "None detected"
    except Exception:
        info["gpu"] = "None detected or nvidia-smi missing"

    return info


def setup_logger():
    """
    Sets up a robust logging system with:
    - Dedicated 'logs' directory
    - Datetime-stamped log files
    - Shared memory buffer for UI
    - Professional colorized terminal output
    """
    # 1. Prepare directory
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. Daily/Run-based filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"app_{timestamp}.log")

    max_size = 10 * 1024 * 1024  # 10MB
    backup_count = 10

    # 3. Log Level
    debug_mode = os.environ.get("APP_DEBUG", "0") == "1"
    log_level = logging.DEBUG if debug_mode else logging.INFO

    try:
        # Formatters
        log_format = "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        file_formatter = logging.Formatter(log_format)

        # File Handler
        file_handler = RotatingFileHandler(log_file, maxBytes=max_size, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(file_formatter)

        # Stream Handler (Console)
        stream_handler = logging.StreamHandler(sys.stdout)
        if colorlog and sys.stdout.isatty():
            color_formatter = colorlog.ColoredFormatter(
                "%(log_color)s" + log_format,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                style="%",
            )
            stream_handler.setFormatter(color_formatter)
        else:
            stream_handler.setFormatter(file_formatter)

        # Memory Handler
        memory_handler = DequeHandler()
        memory_handler.setFormatter(file_formatter)

        # Root Logger setup
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clean existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)
        root_logger.addHandler(memory_handler)

        # Log system info immediately
        sys_info = get_system_info()
        logging.info(f"--- 🚀 APP START: {timestamp} ---")
        logging.info(f"OS: {sys_info['os']}")
        logging.info(f"Python: {sys_info['python']}")
        logging.info(f"Hardware: {sys_info['cpu_count']} CPUs, {sys_info['ram_gb']}GB RAM")
        logging.info(f"GPU: {sys_info['gpu']}")
        logging.info(f"Logging to: {log_file}")

    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"Could not initialize advanced logging: {e}. Falling back to basic.")


if __name__ == "__main__":
    setup_logger()
    logging.info("Advanced logging system test.")
