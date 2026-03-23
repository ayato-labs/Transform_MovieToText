import logging
import queue
import threading
from collections import deque
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class _BaseRecorder:
    """
    Abstract base class for all audio recorders.
    Provides common buffering and chunking logic.
    """

    def __init__(self, output_dir="temp_chunks", segment_time=30, overlap=5, source="system"):
        self.output_dir = Path(output_dir)
        self.segment_time = segment_time
        self.overlap = max(0, overlap)
        self.source = source
        self.is_recording = False

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")

        self.chunk_queue = queue.Queue()

        self.sample_rate = 16000
        self.chunk_duration = self.segment_time + self.overlap
        self.max_buffer_samples = self.chunk_duration * self.sample_rate
        self.audio_buffer = deque()
        self.current_samples_count = 0
        self.buffer_lock = threading.Lock()

        self.chunk_index = 0
        self.last_save_time = 0
        self.recorder_thread = None

    def start(self):
        raise NotImplementedError

    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.recorder_thread:
            self.recorder_thread.join(timeout=2)
        logger.info(f"{self.__class__.__name__} stopped.")

    def _push_chunk(self):
        with self.buffer_lock:
            if not self.audio_buffer:
                return
            full_data = np.concatenate(list(self.audio_buffer))

            # Keep only the overlap part in the buffer for the next chunk
            overlap_samples = self.overlap * self.sample_rate
            if overlap_samples > 0 and len(full_data) > overlap_samples:
                # Re-buffer only the last 'overlap' seconds
                overlap_data = full_data[-overlap_samples:]
                self.audio_buffer.clear()
                self.audio_buffer.append(overlap_data)
                self.current_samples_count = len(overlap_data)
            else:
                self.audio_buffer.clear()
                self.current_samples_count = 0

        self.chunk_queue.put(full_data)
        logger.debug(f"Pushed numpy chunk {self.chunk_index} ({len(full_data)} samples, {len(full_data) / self.sample_rate:.1f}s)")
        self.chunk_index += 1

    def is_process_alive(self):
        return self.is_recording

    def get_recorded_chunks(self):
        return []

    def clear_chunks(self):
        for f in self.output_dir.glob("*.*"):
            try:
                f.unlink()
            except Exception as e:
                logger.debug(f"Failed to unlink {f}: {e}")
