import logging
import os
import sys
import time

import numpy as np

# Add src to path
sys.path.append(os.getcwd())

from src.logger import setup_logger
from src.recorder.ffmpeg import FFmpegRecorder
from src.transcriber import WhisperTranscriber


def main():
    setup_logger()
    logger = logging.getLogger("SystemAudioTest")

    # 1. Initialize Recorder for System Audio (15 seconds)
    logger.info("Step 1: Initializing FFmpegRecorder for System Audio...")
    recorder = FFmpegRecorder(segment_time=15, source="system", mp3_path="tests/output/test_system.mp3")

    # 2. Start Recording
    logger.info("Step 2: Starting recording for 15 seconds (Please ensure audio is playing)...")
    recorder.start()

    # Wait for 17 seconds (buffer for FFmpeg startup)
    time.sleep(17)

    # 3. Stop and Get Chunk
    logger.info("Step 3: Stopping recording and retrieving audio data...")
    recorder.stop()

    if recorder.chunk_queue.empty():
        logger.error("No audio data captured! Check if Stereo Mix is enabled and audio is playing.")
        return

    audio_data = recorder.chunk_queue.get()
    logger.info(f"Captured {len(audio_data)} samples.")

    # Check volume
    rms = np.sqrt(np.mean(audio_data**2))
    logger.info(f"Audio volume (RMS): {rms:.6f}")
    if rms < 0.001:
        logger.warning("Volume is EXTREMELY low. Stereo Mix might not be picking up audio.")

    # 4. Transcribe using Optimized Settings
    logger.info("Step 4: Transcribing using Whisper (turbo, lang=ja, VAD=True)...")
    transcriber = WhisperTranscriber()

    result_text = transcriber.transcribe(audio_data, model_name="turbo", force_gpu=True, language="ja")

    logger.info("--- TRANSCRIPTION RESULT (VAD=True) ---")
    print("\n" + "=" * 20 + " VAD ON " + "=" * 20)
    print(f"[{result_text}]")
    print("=" * 48 + "\n")

    # 5. Try without VAD if empty
    if not result_text:
        logger.info("Step 5: Retrying WITHOUT VAD to see if any sound is captured...")
        # Deep access to model for raw call without VAD
        segments, info = transcriber.model.transcribe(audio_data, beam_size=5, language="ja", vad_filter=False)
        result_text_no_vad = "".join([s.text for s in segments]).strip()
        logger.info("--- TRANSCRIPTION RESULT (VAD=False) ---")
        print("\n" + "=" * 20 + " VAD OFF " + "=" * 20)
        print(f"[{result_text_no_vad}]")
        print("=" * 48 + "\n")

    logger.info("Diagnostics completed.")


if __name__ == "__main__":
    main()
