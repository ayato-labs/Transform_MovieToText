import importlib
import logging
import subprocess
import sys
import threading

from src.core.resource_advisor import ResourceAdvisor
from src.utils.setup_helper import SetupHelper

logger = logging.getLogger(__name__)

# List of heavy dependencies that should be handled in the background
HEAVY_DEPS = ["faster-whisper", "opencv-python", "scipy"]


class SetupManager:
    def __init__(self):
        self._is_ready = False
        self._missing_deps = []
        self._on_status_change = None
        self._on_complete = None
        self._is_running = False
        self._target_model = None

    def _get_target_model(self):
        if not self._target_model:
            rec = ResourceAdvisor.get_best_match()
            self._target_model = rec["ollama"]
        return self._target_model

    def check_env(self):
        """Check for missing heavy dependencies."""
        from src.utils.logger import setup_info
        setup_info("SetupManager: Checking environment dependencies...")
        
        self._missing_deps = []
        
        # CRITICAL: In a standalone EXE, we cannot (and should not) install Python dependencies via pip.
        # They are already bundled. We only check for them to report status.
        is_bundled = getattr(sys, 'frozen', False)
        
        for dep in HEAVY_DEPS:
            import_name = dep.replace("-", "_")
            try:
                importlib.import_module(import_name)
                setup_info(f"SetupManager: Found dependency {dep}")
            except ImportError:
                setup_info(f"SetupManager: Missing dependency {dep}")
                # Only mark as missing if NOT bundled. If bundled and missing, it's a build error, not a setup task.
                if not is_bundled:
                    self._missing_deps.append(dep)

        target_model = self._get_target_model()
        ollama_installed = SetupHelper.is_ollama_installed()
        has_target_model = SetupHelper.has_model(target_model)
        
        setup_info(f"SetupManager: Bundled={is_bundled}, Missing={self._missing_deps}, Ollama={ollama_installed}, Model({target_model})={has_target_model}")
        
        # Ready if no missing installable deps, ollama is there, and model is pulled
        self._is_ready = (len(self._missing_deps) == 0) and ollama_installed and has_target_model
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

        # 1. Handle External Binaries (Ollama)
        ollama_installed = SetupHelper.is_ollama_installed()
        ollama_running = SetupHelper.is_ollama_running()

        if not ollama_installed:
            setup_info("SetupManager: Ollama not found. Attempting installation...")
            if self._on_status_change:
                self._on_status_change("AI Engine missing. Installing Ollama (Remote)...")

            success = SetupHelper.install_ollama_remote()
            if not success:
                setup_error("Ollama installation failed.")
                if self._on_status_change:
                    self._on_status_change("Ollama Setup Failed. Please install manually.")
                return
            # Give it a moment to initialize after install
            import time
            time.sleep(2)
        elif not ollama_running:
            setup_info("SetupManager: Ollama is installed but not running. Attempting to start...")
            if self._on_status_change:
                self._on_status_change("AI Engine is sleeping. Waking up...")
            
            SetupHelper.start_ollama_background()
            # Give it a moment to wake up
            import time
            time.sleep(3)

        # 2. Handle Heavy Python Dependencies
        # CRITICAL: Never attempt to install dependencies in a bundled EXE.
        # Even if missing_deps is truthy (e.g. ['']), we MUST skip this in production.
        is_bundled = getattr(sys, 'frozen', False)
        
        should_install_python_deps = False
        if missing_deps and not is_bundled:
            # Filter out any accidentally empty dependencies
            missing_deps = [d for d in missing_deps if d.strip()]
            if missing_deps:
                should_install_python_deps = True

        if should_install_python_deps:
            try:
                # Try UV first
                setup_info("Checking if 'uv' is available...")
                subprocess.run(["uv", "--version"], capture_output=True, check=True, shell=True)
                cmd = ["uv", "pip", "install"] + missing_deps
                setup_info(f"Using 'uv' for installation: {' '.join(cmd)}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                setup_info("'uv' not found or failed to run. Falling back to 'pip'.")
                cmd = [sys.executable, "-m", "pip", "install"] + missing_deps
                setup_info(f"Using 'pip' for installation: {' '.join(cmd)}")

            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, bufsize=1, universal_newlines=True
                )

                setup_info(f">>> INSTALLATION PROCESS STARTED (Command: {' '.join(cmd)}) <<<")

                # Real-time streaming to terminal and UI
                for line in process.stdout:
                    line_strip = line.strip()
                    if line_strip:
                        # Log internally
                        setup_info(f"Install progress: {line_strip}")
                        
                        # Print directly to system terminal for immediate feedback
                        sys.stdout.write(f"  [SETUP] {line_strip}\n")
                        sys.stdout.flush()

                        if self._on_status_change:
                            # Truncate for UI status bar
                            status = line_strip[:40] + "..." if len(line_strip) > 40 else line_strip
                            self._on_status_change(status)

                process.wait()

                if process.returncode != 0:
                    setup_error(f"Installation failed with exit code {process.returncode}")
                    if self._on_status_change:
                        self._on_status_change("Setup failed (see terminal).")
                    return
                
                setup_info(">>> PYTHON INSTALLATION SUCCESSFUL! <<<")
            except Exception as e:
                setup_error(f"Unexpected error during pip installation: {e}", exc_info=True)
                if self._on_status_change:
                    self._on_status_change(f"Fatal Setup Error: {str(e)}")
                return
        else:
            setup_info(">>> NO PYTHON DEPENDENCIES TO INSTALL (SKIPPED OR BUNDLED) <<<")

        # 3. Handle Primary Model Pull (Final Step)
        try:
            target_model = self._get_target_model()
            if not SetupHelper.has_model(target_model):
                from src.core.event_bus import EVENT_TRANSCRIPTION_PROGRESS, event_bus
                
                def _on_pull_progress(status_text, progress):
                    if self._on_status_change:
                        self._on_status_change(status_text)
                    # Also publish to event bus for global listeners (like progress bars)
                    event_bus.publish(EVENT_TRANSCRIPTION_PROGRESS, progress)
                
                setup_info(f"Constructing AI Brain: Streaming pull for {target_model}...")
                success = SetupHelper.pull_model_streaming(target_model, _on_pull_progress)
                
                if success:
                    setup_info(f"Successfully pulled {target_model}")
                else:
                    setup_error(f"Failed to pull {target_model}")
                    if self._on_status_change:
                        self._on_status_change(f"Failed to pull AI model: {target_model}")
                    return

            self._is_ready = True
            if self._on_complete:
                self._on_complete()

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
