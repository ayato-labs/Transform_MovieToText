import logging
import queue
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np
import soundcard as sc

logger = logging.getLogger(__name__)


def create_recorder(output_dir="temp_chunks", segment_time=30, overlap=5, source="system", mp3_path=None):
    """Factory to return the appropriate recorder based on source."""
    if source == "system":
        return FFmpegRecorder(output_dir, segment_time, overlap, source, mp3_path=mp3_path)
    else:
        return AudioRecorder(output_dir, segment_time, overlap, source, mp3_path=mp3_path)


class _BaseRecorder:
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


class FFmpegRecorder(_BaseRecorder):
    """
    Records system audio using FFmpeg with DirectShow, piping raw PCM streams into memory.
    This restores system audio stability on Windows while maintaining the no-disk-IO architecture.
    """

    def __init__(self, output_dir="temp_chunks", segment_time=30, overlap=5, source="system", mp3_path=None):
        super().__init__(output_dir, segment_time, overlap, source)
        self.process = None
        self.mp3_path = mp3_path
        if self.mp3_path:
            try:
                Path(self.mp3_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory for MP3: {e}")

    def start(self):
        if self.is_recording:
            return
        logger.info(f"FFmpegRecorder started (source={self.source}, mp3_path={self.mp3_path})")
        self.is_recording = True
        self.recorder_thread = threading.Thread(target=self._record_loop, daemon=True, name="FFmpegRecorderThread")
        self.recorder_thread.start()

    def _record_loop(self):
        # Dynamically discover the Stereo Mix device name using soundcard
        all_mics = sc.all_microphones()
        target_name = None
        for m in all_mics:
            if any(kw in m.name for kw in ["ステレオ ミキサー", "Stereo Mix"]):
                target_name = m.name
                break

        if not target_name:
            # Fallback to a common name if not found via soundcard
            target_name = "ステレオ ミキサー (Realtek(R) Audio)"
            logger.warning(f"Stereo Mix not found via soundcard. Falling back to: {target_name}")
        else:
            logger.info(f"Discovered system audio device: {target_name}")

        device_arg = f"audio={target_name}"

        command = ["ffmpeg", "-y", "-f", "dshow", "-i", device_arg, "-ac", "1", "-ar", str(self.sample_rate), "-f", "f32le", "-"]

        if self.mp3_path:
            command.extend(["-f", "mp3", "-ac", "1", "-ab", "64k", self.mp3_path])

        logger.info(f"Starting FFmpeg with command: {' '.join(command)}")

        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024 * 64)
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            self.is_recording = False
            return

        # Thread to log stderr
        def _log_stderr(pipe):
            with pipe:
                for line in pipe:
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    if "Error" in line_str or "fail" in line_str.lower():
                        logger.error(f"FFmpeg: {line_str}")
                    else:
                        logger.debug(f"FFmpeg: {line_str}")

        threading.Thread(target=_log_stderr, args=(self.process.stderr,), daemon=True).start()

        self.last_save_time = time.time()
        self.chunk_index = 0

        try:
            while self.is_recording:
                # Read 1024 float32 samples at a time (4KB)
                raw_data = self.process.stdout.read(4096)
                if not raw_data:
                    logger.warning("FFmpeg stdout closed prematurely.")
                    break

                data = np.frombuffer(raw_data, dtype=np.float32)

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
            logger.error(f"FFmpeg recording crash: {e}", exc_info=True)
        finally:
            self.is_recording = False
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except Exception as e:
                    try:
                        self.process.kill()
                    except Exception as e2:
                        logger.debug(f"Process kill failed: {e2}")
                logger.info("FFmpeg process terminated.")
            if self.current_samples_count > 0:
                try:
                    self._push_chunk()
                except Exception as e:
                    logger.error(f"Failed to push final chunk: {e}")


class AudioRecorder(_BaseRecorder):
    """Refactored AudioRecorder using python-soundcard for microphone capture."""

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

        # Start background MP3 recording if path provided
        if self.mp3_path:
            try:
                # Use FFmpeg to record from the same default microphone
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
