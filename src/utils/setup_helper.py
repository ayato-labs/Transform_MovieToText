import logging
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class SetupHelper:
    """
    Handles system environment checks and dependency management (Ollama).
    """

    OLLAMA_PORT = 11434
    DEFAULT_MODEL = "gemma4:e2b"

    @staticmethod
    def is_ollama_running() -> bool:
        """Checks if Ollama API server is reachable."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.connect(("127.0.0.1", SetupHelper.OLLAMA_PORT))
                return True
            except (TimeoutError, ConnectionRefusedError):
                return False

    @staticmethod
    def is_ollama_installed() -> bool:
        """Checks if ollama executable is in the PATH."""
        return shutil.which("ollama") is not None

    @staticmethod
    def has_model(model_name: str = DEFAULT_MODEL) -> bool:
        """Checks if a specific model is already pulled in Ollama."""
        if not SetupHelper.is_ollama_running():
            logger.debug("SetupHelper: Ollama is not running, skipping has_model check.")
            return False
        try:
            # Force local host for CLI check
            env = os.environ.copy()
            # Ensure host is set to loopback
            env["OLLAMA_HOST"] = "127.0.0.1:11434"
            logger.debug(f"SetupHelper: Checking if model '{model_name}' is installed...")
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True, env=env)
            found = model_name in result.stdout
            logger.debug(f"SetupHelper: Model '{model_name}' found={found}")
            return found
        except Exception as e:
            logger.error(f"SetupHelper: has_model check failed (Ollama command error): {e}")
            return False

    @staticmethod
    def get_bundled_installer_path() -> Path | None:
        """Locates the bundled OllamaSetup.exe if running from PyInstaller bundle."""
        # For PyInstaller/One-file bundle
        base_path = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parents[2]

        path = base_path / "assets" / "dependencies" / "OllamaSetup.exe"
        return path if path.exists() else None

    @staticmethod
    def install_ollama_remote() -> bool:
        """Installs Ollama using the official PowerShell one-liner."""
        try:
            cmd = 'powershell -Command "irm https://ollama.com/install.ps1 | iex"'
            logger.info(f"Executing remote Ollama installation: {cmd}")
            # Run with shell=True to allow the pipe and iex to work
            subprocess.run(cmd, shell=True, check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to install Ollama via PowerShell: {e}")
            return False

    @staticmethod
    def pull_model_background(model_name: str = DEFAULT_MODEL):
        """Pulls the model in a non-blocking way."""

        def _target():
            try:
                logger.info(f"Starting background pull for {model_name}...")
                env = os.environ.copy()
                env["OLLAMA_HOST"] = "127.0.0.1:11434"
                subprocess.run(["ollama", "pull", model_name], check=True, env=env)
                logger.info(f"Successfully pulled {model_name}")
            except Exception as e:
                logger.error(f"Failed to pull {model_name}: {e}")

        import threading

        threading.Thread(target=_target, daemon=True).start()

    @staticmethod
    def pull_model_streaming(model_name: str, progress_callback: callable):
        """
        Pulls a model using the Ollama SDK and reports progress via callback.
        callback(status_text, progress_float)
        """
        import ollama
        try:
            logger.info(f"Streaming pull for {model_name} started.")
            # Ensure environment is set for the current process as well for the SDK
            os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"
            for part in ollama.pull(model_name, stream=True):
                status = part.get("status", "")
                completed = part.get("completed")
                total = part.get("total")
                
                # Use 0 if None to avoid comparison errors
                completed_val = completed if completed is not None else 0
                total_val = total if total is not None else 0
                
                progress = 0.0
                if total_val > 0:
                    progress = completed_val / total_val
                
                # Human readable status
                if total_val > 0:
                    status_text = f"Downloading {model_name}: {status} ({completed_val/(1024**2):.1f}/{total_val/(1024**2):.1f} MB)"
                else:
                    status_text = f"Ollama: {status}"
                
                progress_callback(status_text, progress)
            
            logger.info(f"Streaming pull for {model_name} completed.")
            return True
        except Exception as e:
            logger.error(f"Streaming pull failed: {e}")
            progress_callback(f"Pull failed: {e}", 0.0)
            return False
