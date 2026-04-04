import logging
import queue
import threading
import time
import traceback

import numpy as np

from src.core.event_bus import EVENT_TRANSCRIPTION_SEGMENT, event_bus
from src.core.whisper_transcriber import WhisperTranscriber
from src.platforms.desktop.recorder.factory import create_recorder

logger = logging.getLogger(__name__)


class LiveTranscriptionManager:
    """
    Orchestrates live loopback recording and background transcription.
    Handles the lifecycle of audio chunks as numpy arrays.

    Updated to remove WAV/BytesIO overhead, processing numpy arrays directly.
    """

    def __init__(
        self, transcriber: WhisperTranscriber, model_name="base", force_gpu=False, on_text_added=None, source="system", mp3_path=None, language="ja"
    ):
        self.transcriber = transcriber
        self.model_name = model_name
        self.force_gpu = force_gpu
        self.language = language
        self.on_text_added = on_text_added  # Callback function(text)
        self.mp3_path = mp3_path
        # Reduced segment_time for better responsiveness
        self.recorder = create_recorder(segment_time=10, overlap=3, source=source, mp3_path=self.mp3_path)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self.full_transcript = ""
        self.all_segments = []

        # Statistics
        self.chunks_processed = 0
        self.total_errors = 0
        self.start_time = 0

    def start(self):
        """Starts both recording and the background processing thread."""
        self.full_transcript = ""
        self.stop_event.clear()
        self.chunks_processed = 0
        self.total_errors = 0
        self.start_time = time.time()

        self.recorder.start()

        self.worker_thread = threading.Thread(target=self._process_chunks_loop, daemon=True, name="LiveTranscriptionWorker")
        self.worker_thread.start()
        logger.info("Live transcription manager started.")

    def stop(self):
        """Stops recording and waits for processing to finish."""
        self.recorder.stop()
        self.stop_event.set()

        if self.worker_thread:
            # 3s is enough since we flush the buffer on stop now.
            # This prevents UI hang if the worker doesn't finish immediately.
            self.worker_thread.join(timeout=3)

        duration = time.time() - self.start_time
        logger.info(
            f"Live transcription stopped. Summary: {self.chunks_processed} chunks processed, {self.total_errors} errors, Duration: {duration:.1f}s"
        )
        return self.full_transcript, self.all_segments

    def _process_chunks_loop(self):
        """Background thread loop that checks for new chunks via queue."""
        while not self.stop_event.is_set() or not self.recorder.chunk_queue.empty():
            try:
                # Wait for next chunk with timeout to check stop_event
                audio_data = self.recorder.chunk_queue.get(timeout=1)
                if audio_data is None:
                    break

                self._handle_audio_data(audio_data)
                self.recorder.chunk_queue.task_done()
            except queue.Empty:
                # Normal timeout waiting for data
                if self.stop_event.is_set() and self.recorder.chunk_queue.empty():
                    break
                continue
            except Exception as e:
                self.total_errors += 1
                logger.error(f"Error in transcription loop: {e}\n{traceback.format_exc()}")
                if self.stop_event.is_set() and self.recorder.chunk_queue.empty():
                    break
                continue

        logger.info("Live transcription worker loop finished.")

    def _handle_audio_data(self, audio_data):
        """Transcribes numpy audio data directly."""
        try:
            # audio_data is a numpy float32 array
            duration = len(audio_data) / 16000
            logger.info(f"Processing in-memory numpy chunk (Source: {self.recorder.source}, Samples: {len(audio_data)}, Duration: {duration:.1f}s)")

            if duration < 0.1:
                logger.warning("Chunk too short, skipping.")
                return

            # Pass numpy array directly to transcriber
            peak = np.abs(audio_data).max()
            rms = np.sqrt(np.mean(audio_data**2))
            logger.info(f"Chunk Stats - Peak: {peak:.6f}, RMS: {rms:.6f}, Duration: {duration:.1f}s")

            # Strict silence suppression
            if peak < 0.01 or rms < 0.001:
                logger.debug(f"Chunk is too quiet (Peak: {peak:.4f}, RMS: {rms:.4f}), skipping transcription.")
                return

            result = self.transcriber.transcribe(audio_data, model_name=self.model_name, force_gpu=self.force_gpu, language=self.language)
            text = result["text"]
            segments = result["segments"]

            if text:
                logger.info(f"Transcribed chunk: {text[:50]}...")

                # Session-relative offset
                offset = time.time() - self.start_time - duration
                if offset < 0:
                    offset = 0

                # Adjust segment timestamps to be session-relative
                for seg in segments:
                    seg["start"] = round(seg["start"] + offset, 2)
                    seg["end"] = round(seg["end"] + offset, 2)

                    self.all_segments.append(seg)
                    # Publish each segment individually for granular UI updates
                    event_bus.publish(EVENT_TRANSCRIPTION_SEGMENT, seg)

                self.full_transcript += text + " "
                if self.on_text_added:
                    self.on_text_added(text)
            else:
                logger.info("Transcription result: [EMPTY/SILENCE]")

            self.chunks_processed += 1

        except Exception as e:
            self.total_errors += 1
            logger.error(f"Error processing live audio chunk: {e}\n{traceback.format_exc()}")
