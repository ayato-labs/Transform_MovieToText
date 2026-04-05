import importlib
import subprocess
import threading
import logging
import sys

logger = logging.getLogger(__name__)

# List of heavy dependencies that should be handled in the background
HEAVY_DEPS = ["faster-whisper", "torch", "torchvision", "torchaudio", "opencv-python"]

class SetupManager:
    def __init__(self):
        self._is_ready = False
        self._missing_deps = []
        self._on_status_change = None
        self._on_complete = None
        self._is_running = False

    def check_env(self):
        """Check for missing heavy dependencies."""
        self._missing_deps = []
        for dep in HEAVY_DEPS:
            import_name = dep.replace("-", "_")
            try:
                importlib.import_module(import_name)
            except ImportError:
                self._missing_deps.append(dep)
        
        self._is_ready = len(self._missing_deps) == 0
        return self._is_ready, self._missing_deps

    def start_background_setup(self, on_status_change=None, on_complete=None):
        """Initiates setup in a background thread."""
        if self._is_running:
            return
        
        self._on_status_change = on_status_change
        self._on_complete = on_complete
        
        ready, missing = self.check_env()
        if ready:
            if self._on_complete:
                self._on_complete()
            return

        self._is_running = True
        threading.Thread(target=self._run_install_thread, args=(missing,), daemon=True).start()

    def _run_install_thread(self, missing_deps):
        from src.utils.logger import setup_error, setup_info
        
        setup_info(f"--- STARTING SETUP: Missing {missing_deps} ---")
        if self._on_status_change:
            self._on_status_change(f"Preparing to install {len(missing_deps)} components...")

        use_pip = False
        try:
            # Try UV first
            setup_info("Checking if 'uv' is available...")
            subprocess.run(["uv", "--version"], capture_output=True, check=True, shell=True)
            cmd = ["uv", "pip", "install"] + missing_deps
            setup_info(f"Using 'uv' for installation: {' '.join(cmd)}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            setup_info("'uv' not found or failed to run. Falling back to 'pip'.")
            use_pip = True
            cmd = [sys.executable, "-m", "pip", "install"] + missing_deps
            setup_info(f"Using 'pip' for installation: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                bufsize=1,
                universal_newlines=True
            )

            setup_info(">>> INSTALLATION PROCESS STARTED (Streaming logs below) <<<")
            
            # Real-time streaming to terminal and UI
            for line in process.stdout:
                line_strip = line.strip()
                if line_strip:
                    # Print directly to system terminal for immediate feedback
                    sys.stdout.write(f"  [SETUP] {line_strip}\n")
                    sys.stdout.flush()
                    
                    if self._on_status_change:
                        # Truncate for UI status bar
                        status = line_strip[:40] + "..." if len(line_strip) > 40 else line_strip
                        self._on_status_change(status)

            process.wait()

            if process.returncode == 0:
                setup_info(">>> INSTALLATION SUCCESSFUL! <<<")
                self._is_ready = True
                if self._on_complete:
                    self._on_complete()
            else:
                setup_error(f"Installation failed with exit code {process.returncode}")
                if self._on_status_change:
                    self._on_status_change("Setup failed (see terminal).")
        
        except Exception as e:
            setup_error(f"Unexpected error during setup: {e}", exc_info=True)
            if self._on_status_change:
                self._on_status_change(f"Fatal Setup Error: {str(e)}")
        finally:
            self._is_running = False
            setup_info("--- SETUP THREAD TERMINATED ---")

    @property
    def is_working(self):
        return self._is_running

    @property
    def is_fully_ready(self):
        return self._is_ready

# Singleton instance
setup_manager = SetupManager()
