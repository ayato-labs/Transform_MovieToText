import logging
import threading
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import pyautogui
except Exception as e:
    # Handle headless environments (Linux CI without DISPLAY)
    logger.warning(f"pyautogui could not be imported. Screen capture disabled: {e}")
    pyautogui = None

from src.core.history_mgr import history_mgr


class VisualRecorder:
    """
    Asynchronous screen capture recorder.
    Detects significant changes in the screen to avoid redundant saves.
    """

    def __init__(self, output_dir="data/records", capture_interval=5.0, diff_threshold=0.01):
        self.output_dir = Path(output_dir)
        self.capture_interval = capture_interval
        self.diff_threshold = diff_threshold  # Percentage of pixels changed
        self.is_recording = False
        self.recorder_thread = None
        self.meeting_id = None
        self.last_frame = None
        self.start_time = 0

    def start(self, meeting_id):
        """Starts the visual recording for a specific meeting."""
        if self.is_recording:
            return

        self.meeting_id = meeting_id
        self.is_recording = True
        self.start_time = time.time()
        self.last_frame = None

        # Ensure meeting-specific directory exists
        self.meeting_dir = self.output_dir / str(meeting_id) / "images"
        self.meeting_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"VisualRecorder started for meeting {meeting_id}")
        self.recorder_thread = threading.Thread(target=self._capture_loop, daemon=True, name="VisualCaptureThread")
        self.recorder_thread.start()

    def stop(self):
        """Stops the visual recording."""
        if not self.is_recording:
            return
        self.is_recording = False
        if self.recorder_thread:
            self.recorder_thread.join(timeout=2)
        logger.info("VisualRecorder stopped.")

    def _capture_loop(self):
        """Background loop for capturing and comparing frames."""
        if pyautogui is None:
            logger.warning("VisualRecorder: pyautogui is not available (headless environment). Recording disabled.")
            self.is_recording = False
            return

        try:
            while self.is_recording:
                loop_start = time.time()

                # 1. Capture screen
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # 2. Check for changes
                if self._has_changed(frame):
                    timestamp_sec = round(time.time() - self.start_time, 2)
                    self._save_frame(frame, timestamp_sec)
                    self.last_frame = frame

                # 3. Wait for interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.capture_interval - elapsed)
                time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"VisualRecorder crash: {e}", exc_info=True)
            self.is_recording = False

    def _has_changed(self, current_frame):
        """Compares current frame with the last saved frame using MSE or Absolute Diff."""
        if self.last_frame is None:
            return True

        # Resize for faster comparison
        prev_small = cv2.resize(self.last_frame, (320, 180))
        curr_small = cv2.resize(current_frame, (320, 180))

        # Calculate absolute difference
        diff = cv2.absdiff(prev_small, curr_small)
        non_zero_count = np.count_nonzero(diff)
        total_pixels = diff.shape[0] * diff.shape[1] * diff.shape[2]
        change_ratio = non_zero_count / total_pixels

        logger.debug(f"Screen change ratio: {change_ratio:.4f}")
        return change_ratio > self.diff_threshold

    def _save_frame(self, frame, timestamp_sec):
        """Saves the frame to disk and records metadata in DB."""
        if self.meeting_id is None:
            logger.warning("VisualRecorder: meeting_id is None, skipping frame save.")
            return

        filename = f"frame_{timestamp_sec:.2f}s.jpg"
        file_path = self.meeting_dir / filename

        # Save high-quality JPEG to save space vs PNG
        cv2.imwrite(str(file_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        # Store in database
        # Robust relative path calculation: resolve both paths to absolute before relative_to
        try:
            rel_path = file_path.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            # Fallback if somehow they are on different drives or not subpaths
            rel_path = file_path

        history_mgr.add_visual_context(meeting_id=self.meeting_id, timestamp_sec=timestamp_sec, image_path=str(rel_path))
        logger.info(f"Significant screen change detected. Saved {filename}")


# Optional: Add to recorder init or singleton
visual_recorder = VisualRecorder()
