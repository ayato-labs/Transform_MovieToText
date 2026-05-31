import datetime
import logging
import os
import platform
import sys
from collections import deque
from contextlib import suppress

from loguru import logger

# Global buffer for UI log viewing
LOG_BUFFER = deque(maxlen=200)

# Custom log level for setup-related info
# Standard logging INFO is 20, WARNING is 30.
# We'll map "SETUP" to 25.
LOG_LEVEL_SETUP = 25

class InterceptHandler(logging.Handler):
    """
    Default handler from loguru documentation for intercepting standard logging messages.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def get_system_info():
    """Captures basic system and hardware diagnostics."""
    info = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }

    try:
        import psutil
        ram_total = psutil.virtual_memory().total
        info["ram_gb"] = round(ram_total / (1024**3), 1)
    except Exception:
        info["ram_gb"] = "Unknown"

    try:
        import subprocess
        gpu_cmd = "nvidia-smi --query-gpu=name --format=csv,noheader"
        gpu_info = subprocess.check_output(gpu_cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        info["gpu"] = gpu_info if gpu_info else "None detected"
    except Exception:
        info["gpu"] = "None detected or nvidia-smi missing"

    return info

def setup_logger():
    """
    Sets up a robust logging system with Loguru:
    - Structured JSON logs for traceability
    - Retention of last 2 runs (rotation="startup")
    - Isolated error logging (error.log)
    - Interception of standard logging
    - UI buffer for Flet components
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 1. Reset default Loguru handler
    logger.remove()

    # 2. Add SETUP level to Loguru
    with suppress(ValueError):
        logger.level("SETUP", no=LOG_LEVEL_SETUP, color="<bold><cyan>")

    # 3. Console Handler (for humans, colored, not JSON)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    debug_mode = os.environ.get("APP_DEBUG", "0") == "1"
    console_level = "DEBUG" if debug_mode else "INFO"
    logger.add(sys.stdout, format=console_format, level=console_level, colorize=True)

    # 4. Main Application Log (JSON, last 2 runs)
    # Using {time} in filename creates a new file per run.
    # retention=2 keeps current + previous.
    app_log_path = os.path.join(log_dir, "app_{time}.json")
    logger.add(
        app_log_path,
        serialize=True,
        retention=2,
        level="DEBUG",
        encoding="utf-8"
    )

    # 5. Isolated Error Log (JSON, only ERROR and above)
    # We'll use a fixed name for error.log but rotate it to keep it clean.
    error_log_path = os.path.join(log_dir, "error.log")
    logger.add(
        error_log_path,
        serialize=True,
        level="ERROR",
        encoding="utf-8",
        rotation="10 MB",
        retention=5 # Keep some error history
    )

    # 6. UI Buffer Sink (for Flet UI)
    def ui_buffer_sink(message):
        # We store the formatted string (without colors) for the UI
        LOG_BUFFER.append(message.strip())

    logger.add(
        ui_buffer_sink, 
        format="{time:HH:mm:ss} | {level: <5} | {message}", 
        level="INFO"
    )

    # 7. Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Log initial system info
    sys_info = get_system_info()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"--- 🚀 APP START: {timestamp} ---")
    logger.info(f"OS: {sys_info['os']}")
    logger.info(f"Python: {sys_info['python']}")
    logger.info(f"Hardware: {sys_info['cpu_count']} CPUs, {sys_info['ram_gb']}GB RAM")
    logger.info(f"GPU: {sys_info['gpu']}")
    logger.info(f"Logging initialized. Main log: {app_log_path}, Error log: {error_log_path}")

    return logger

if __name__ == "__main__":
    setup_logger()
    logger.debug("Debug message")
    logger.info("Info message")
    logger.log("SETUP", "Setup message")
    logger.error("Error message")
