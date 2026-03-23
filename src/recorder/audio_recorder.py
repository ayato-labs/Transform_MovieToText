import logging
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import soundcard as sc

from .base import _BaseRecorder

logger = logging.getLogger(__name__)


class AudioRecorder(_BaseRecorder):
    """Recorder using python-soundcard for microphone capture."""

    def __init__(self, output_dir="temp_chunks", segment_time=30, overlap=5, source="microphone", mp3_path=None):
        super().__init__(output_dir, segment_time, overlap, source)
        self.mp3_path = mp3_path
        self.mp3_process = None
        if self.mp3_path:
            try:
                Path(self.mp3_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory for MP3: {e}")

    def start(self):
        if self.is_recording:
            return

        try:
            device = sc.default_microphone()
        except Exception as e:
            logger.error(f"Failed to find audio device: {e}")
            raise RuntimeError("マイクが見つかりませんでした。")

        self.is_recording = True

        if self.mp3_path:
            try:
                command = ["ffmpeg", "-y", "-f", "dshow", "-i", f"audio={device.name}", "-ac", "1", "-ab", "64k", self.mp3_path]
                self.mp3_process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
                logger.info(f"Background MP3 recording started: {self.mp3_path}")
            except Exception as e:
                logger.error(f"Failed to start background MP3 recording: {e}")

        logger.info(f"AudioRecorder started (source={self.source})")
        self.recorder_thread = threading.Thread(target=self._record_loop, daemon=True, name="SoundCardRecorderThread")
        self.recorder_thread.start()

    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.mp3_process:
            self.mp3_process.terminate()
            try:
                self.mp3_process.wait(timeout=2)
            except Exception as e:
                logger.debug(f"MP3 process wait failed: {e}")
        if self.recorder_thread:
            self.recorder_thread.join(timeout=2)
        logger.info(f"{self.__class__.__name__} stopped.")

    def _record_loop(self):
        try:
            device = sc.default_microphone()
            logger.info(f"Recording started on device: {device.name}")

            self.last_save_time = time.time()
            self.chunk_index = 0
            block_size = 1024

            with device.recorder(samplerate=self.sample_rate) as recorder:
                while self.is_recording:
                    data = recorder.record(numframes=block_size)

                    if data.ndim > 1 and data.shape[1] > 1:
                        data = np.mean(data, axis=1)
                    else:
                        data = data.flatten()

                    data = data.astype(np.float32)

                    with self.buffer_lock:
                        self.audio_buffer.append(data)
                        self.current_samples_count += len(data)

                        while self.current_samples_count > self.max_buffer_samples and self.audio_buffer:
                            removed = self.audio_buffer.popleft()
                            self.current_samples_count -= len(removed)

                    now = time.time()
                    if now - self.last_save_time >= self.segment_time:
                        self._push_chunk()
                        self.last_save_time = now

        except Exception as e:
            logger.error(f"Recording crash: {e}", exc_info=True)
            self.is_recording = False
        finally:
            if self.current_samples_count > 0:
                self._push_chunk()
