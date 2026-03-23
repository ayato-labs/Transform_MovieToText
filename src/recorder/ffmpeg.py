import logging
import re
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from .base import _BaseRecorder

logger = logging.getLogger(__name__)


class FFmpegRecorder(_BaseRecorder):
    """
    Records system audio using FFmpeg with DirectShow, piping raw PCM streams into memory.
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

    def _get_system_audio_device(self):
        """Aggressively discovers the system audio device name or GUID with encoding resilience."""
        try:
            cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            _, stderr_bytes = proc.communicate(timeout=5)

            # Keywords to look for (using both localized and common terms)
            # We want to AVOID 'Microphone' or 'マイク' when source is 'system'
            keywords = ["ステレオ", "ミキサー", "Stereo", "Mix", "Rec. Playback", "Virtual", "Wave", "Loopback"]
            avoid_keywords = ["Microphone", "マイク", "Array", "配列"]

            devices_found = []

            # Try multiple encodings to get a readable string
            for enc in ["cp932", "utf-8", "latin1"]:
                try:
                    text = stderr_bytes.decode(enc, errors="ignore")
                    lines = text.splitlines()
                    for i, line in enumerate(lines):
                        if "(audio)" in line:
                            # Try to extract the display name
                            name_match = re.search(r"\"(.*?)\"", line)
                            display_name = name_match.group(1) if name_match else ""

                            # Check next line for GUID
                            guid = ""
                            if i + 1 < len(lines) and "Alternative name" in lines[i + 1]:
                                guid_match = re.search(r"Alternative name \"(.*?)\"", lines[i + 1])
                                if guid_match:
                                    guid = guid_match.group(1)

                            if display_name or guid:
                                # Calculate score
                                score = 0
                                if display_name:
                                    score += sum(10 for kw in keywords if kw.lower() in display_name.lower())
                                    score -= sum(50 for kw in avoid_keywords if kw.lower() in display_name.lower())

                                devices_found.append({"name": display_name, "guid": guid, "score": score})
                except Exception:
                    continue

            # Sort by score descending
            devices_found.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"FFmpegRecorder: Found {len(devices_found)} audio devices.")
            for d in devices_found:
                logger.info(f"  Device: {d['name']} | GUID: {d['guid']} | Score: {d['score']}")

            if devices_found and devices_found[0]["score"] > 0:
                best = devices_found[0]
                target = best["guid"] if best["guid"] else best["name"]
                logger.info(f"FFmpegRecorder: Selected best matching device: [{target}] (Score: {best['score']})")
                return target

        except Exception as e:
            logger.error(f"FFmpegRecorder: Aggressive discovery failed: {e}")

        return "ステレオ ミキサー (Realtek(R) Audio)"  # Last resort

    def _record_loop(self):
        target_name = self._get_system_audio_device()
        # Ensure we wrap the target name in quotes if it's not already
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
                except Exception:
                    try:
                        self.process.kill()
                    except Exception as e:
                        logger.debug(f"FFmpeg process kill failed (already dead?): {e}")
                logger.info("FFmpeg process terminated.")
            if self.current_samples_count > 0:
                try:
                    self._push_chunk()
                except Exception as e:
                    logger.error(f"Failed to push final chunk: {e}")
