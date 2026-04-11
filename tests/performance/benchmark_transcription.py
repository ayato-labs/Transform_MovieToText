import logging
import time

# Ensure project root is in sys.path
import numpy as np
import psutil
import torch

from src.core.whisper_transcriber import WhisperTranscriber

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def benchmark_whisper_performance():
    """
    Benchmarks RAM and VRAM usage during the transcription of a synthetic audio buffer.
    Ensures that the 'Luxurious Quality' bar is maintained by preventing resource leaks.
    """
    logger.info("--- Whisper Performance Benchmark ---")
    transcriber = WhisperTranscriber()

    # 1. Baseline Resource Usage
    ram_baseline = psutil.virtual_memory().used / (1024**2)
    vram_baseline = 0.0
    if torch.cuda.is_available():
        vram_baseline = torch.cuda.memory_allocated(0) / (1024**2)

    logger.info(f"Baseline - RAM: {ram_baseline:.2f}MB, VRAM: {vram_baseline:.2f}MB")

    # 2. Loading Model (Base)
    start_load = time.time()
    transcriber.load_model("base")
    load_duration = time.time() - start_load

    ram_after_load = psutil.virtual_memory().used / (1024**2)
    vram_after_load = 0.0
    if torch.cuda.is_available():
        vram_after_load = torch.cuda.memory_allocated(0) / (1024**2)

    logger.info(f"Model Load (base) - Duration: {load_duration:.2f}s")
    logger.info(
        f"Post-Load - RAM: {ram_after_load:.2f}MB (+{ram_after_load - ram_baseline:.2f}MB), "
        f"VRAM: {vram_after_load:.2f}MB (+{vram_after_load - vram_baseline:.2f}MB)"
    )

    # 3. Transcription Benchmark
    # Create 30 seconds of synthetic audio (silence + noise) at 16kHz
    sample_rate = 16000
    duration_sec = 30
    audio_data = np.random.uniform(-1, 1, sample_rate * duration_sec).astype(np.float32)

    start_transcribe = time.time()
    _ = transcriber.transcribe(audio_data, model_name="base")
    transcribe_duration = time.time() - start_transcribe

    logger.info(f"Transcription (30s synthetic) - Duration: {transcribe_duration:.2f}s")

    # Check for leaks
    ram_final = psutil.virtual_memory().used / (1024**2)
    logger.info(f"Final - RAM: {ram_final:.2f}MB (Net Change: {ram_final - ram_baseline:.2f}MB)")


if __name__ == "__main__":
    benchmark_whisper_performance()