import logging
import sys
import threading
import time
from pathlib import Path

import numpy as np

try:
    if sys.platform == "win32":
        import pyaudiowpatch as pyaudio
    else:
        import pyaudio
except ImportError:
    pyaudio = None

from .base import _BaseRecorder

logger = logging.getLogger(__name__)


class AudioRecorder(_BaseRecorder):
    """Recorder using pyaudiowpatch for microphone capture."""

    def __init__(self, output_dir=None, segment_time=30, overlap=5, source="microphone", mp3_path=None):
        super().__init__(output_dir, segment_time, overlap, source)
        self.mp3_path = mp3_path
        self._pa = None
        self._stream = None
        self.stop_event = threading.Event()

        if self.mp3_path:
            try:
                Path(self.mp3_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory for MP3: {e}")

    def start(self):
        if self.is_recording:
            return

        self.is_recording = True
        self.stop_event.clear()
        logger.info(f"AudioRecorder started (source={self.source})")
        self.recorder_thread = threading.Thread(target=self._record_loop, daemon=True, name="AudioRecorderThread")
        self.recorder_thread.start()

    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.stop_event.set()
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        logger.info(f"{self.__class__.__name__} stopped.")

    def _record_loop(self):
        try:
            self._pa = pyaudio.PyAudio()
            # Use default input device
            device_info = self._pa.get_default_input_device_info()
            logger.info(f"Recording started on device: {device_info['name']}")

            self.last_save_time = time.time()
            self.chunk_index = 0

            # 16kHz, Mono, Int16 (Whisper standard)
            self._stream = self._pa.open(format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=1024)

            while self.is_recording and not self.stop_event.is_set():
                try:
                    raw_bytes = self._stream.read(1024, exception_on_overflow=False)
                    data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

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
                    logger.warning(f"Stream read error: {e}")
                    continue

        except Exception as e:
            logger.error(f"Recording crash: {e}", exc_info=True)
            self.is_recording = False
        finally:
            if self.current_samples_count > 0:
                self._push_chunk()
