import logging
import subprocess
import sys
import threading
import time

import numpy as np

try:
    if sys.platform == "win32":
        import pyaudiowpatch as pyaudio
    else:
        import pyaudio
except ImportError:
    pyaudio = None
import scipy.signal

from .base import _BaseRecorder

logger = logging.getLogger(__name__)


class SoundCardRecorder(_BaseRecorder):
    """
    Captures system audio using pyaudiowpatch (WASAPI Loopback).
    This replaces the broken soundcard library approach.
    Captures at native device sample rate (typically 48000Hz)
    and resamples to 16000Hz for Whisper.
    """

    def __init__(self, output_dir=None, segment_time=30, overlap=5, source="system", mp3_path=None):
        super().__init__(output_dir, segment_time, overlap, source)
        self.mp3_path = mp3_path
        self.ffmpeg_proc = None
        self.stop_event = threading.Event()
        self._pa = None
        self._stream = None
        self._resampler = None
        self._native_sr = None
        self._channels = None

    def start(self):
        if self.is_recording:
            return
        logger.info(f"SoundCardRecorder started (source={self.source}, mp3_path={self.mp3_path})")
        self.is_recording = True
        self.stop_event.clear()

        self.recorder_thread = threading.Thread(target=self._record_loop, daemon=True, name="SoundCardRecorderThread")
        self.recorder_thread.start()

    def _record_loop(self):
        try:
            # 1. Initialize PyAudio and find WASAPI loopback device
            self._pa = pyaudio.PyAudio()

            try:
                wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                logger.error("WASAPI is not available on this system.")
                self.is_recording = False
                return

            default_speakers = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            logger.info(f"SoundCardRecorder: Default speaker: {default_speakers['name']}")

            if not default_speakers["isLoopbackDevice"]:
                for loopback in self._pa.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
                else:
                    logger.error("SoundCardRecorder: No WASAPI loopback device found.")
                    self.is_recording = False
                    return

            logger.info(f"SoundCardRecorder: Capturing from [{default_speakers['name']}]")

            self._native_sr = int(default_speakers["defaultSampleRate"])
            self._channels = default_speakers["maxInputChannels"]

            if self._native_sr != self.sample_rate:
                logger.info(f"SoundCardRecorder: Resampling {self._native_sr}Hz -> {self.sample_rate}Hz using scipy")

            # 3. Setup FFmpeg for MP3 encoding if needed
            if self.mp3_path:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "s16le",
                    "-ar",
                    str(self._native_sr),
                    "-ac",
                    str(self._channels),
                    "-i",
                    "pipe:0",
                    "-ac",
                    "1",
                    "-ab",
                    "64k",
                    self.mp3_path,
                ]
                try:
                    self.ffmpeg_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    logger.info("SoundCardRecorder: FFmpeg MP3 encoder initialized.")
                except (FileNotFoundError, OSError):
                    logger.warning("SoundCardRecorder: FFmpeg not found. MP3 recording will be skipped, but transcription will continue.")
                    self.ffmpeg_proc = None

            # 4. Open audio stream
            chunk_frames = int(self._native_sr * 0.1)  # 0.1s chunks

            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._native_sr,
                frames_per_buffer=chunk_frames,
                input=True,
                input_device_index=default_speakers["index"],
            )

            # 5. Main capture loop
            self.last_save_time = time.time()
            while self.is_recording and not self.stop_event.is_set():
                try:
                    raw_bytes = self._stream.read(chunk_frames, exception_on_overflow=False)
                except Exception as e:
                    logger.warning(f"Stream read error: {e}")
                    continue

                # Convert raw PCM bytes to numpy
                audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)

                # Feed raw bytes to FFmpeg for MP3 encoding
                if self.ffmpeg_proc and self.ffmpeg_proc.stdin:
                    try:
                        self.ffmpeg_proc.stdin.write(raw_bytes)
                        self.ffmpeg_proc.stdin.flush()
                    except (BrokenPipeError, OSError) as e:
                        # Errno 22 usually means FFmpeg crashed or closed the pipe.
                        logger.warning(f"SoundCardRecorder: FFmpeg MP3 pipe broke ({e}). MP3 saving is aborted, but transcription continues.")
                        try:
                            self.ffmpeg_proc.stdin.close()
                        except Exception:
                            pass
                        self.ffmpeg_proc = None

                # Convert to mono float32
                if self._channels > 1:
                    audio_int16 = audio_int16.reshape(-1, self._channels)
                    audio_mono = audio_int16.mean(axis=1)
                else:
                    audio_mono = audio_int16.astype(np.float32)

                audio_float = (audio_mono / 32768.0).astype(np.float32)

                # Resample to 16kHz for Whisper using scipy
                if self._native_sr != self.sample_rate:
                    target_length = int(len(audio_float) * self.sample_rate / self._native_sr)
                    audio_float = scipy.signal.resample(audio_float, target_length).astype(np.float32)

                # Feed to buffer for transcription
                with self.buffer_lock:
                    self.audio_buffer.append(audio_float)
                    self.current_samples_count += len(audio_float)

                    while self.current_samples_count > self.max_buffer_samples and self.audio_buffer:
                        removed = self.audio_buffer.popleft()
                        self.current_samples_count -= len(removed)

                # Check chunking timing
                now = time.time()
                if now - self.last_save_time >= self.segment_time:
                    self._push_chunk()
                    self.last_save_time = now

            # --- FLUSH REMAINING BUFFER ON STOP ---
            logger.info("SoundCardRecorder: Stop signal received. Flushing remaining buffer...")
            if self.current_samples_count > 0:
                self._push_chunk()

        except Exception as e:
            logger.error(f"SoundCardRecorder crash: {e}", exc_info=True)
        finally:
            self.is_recording = False
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    logger.exception("SoundCardRecorder: Stream close failed during cleanup")
            if self._pa:
                try:
                    self._pa.terminate()
                except Exception:
                    logger.exception("SoundCardRecorder: Failed to terminate PyAudio")
            if self.ffmpeg_proc:
                try:
                    self.ffmpeg_proc.stdin.close()
                    self.ffmpeg_proc.wait(timeout=2)
                except Exception:
                    logger.exception("SoundCardRecorder: FFmpeg cleanup failed")
                logger.info("FFmpeg MP3 encoder terminated.")
            logger.info("SoundCardRecorder loop finished.")

    def stop(self):
        self.stop_event.set()
        super().stop()
