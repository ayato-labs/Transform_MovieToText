"""
Full Pipeline PoC with Structured Logging (Loguru).
Extracts audio from MP4 and runs Speaker Diarization using sherpa-onnx and CAM++.
"""

import os
import subprocess
import sys
import wave
import json
import shutil
from datetime import datetime
from loguru import logger
import numpy as np

# Add project root to sys.path to import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.model_manager import ModelManager

# --- Logging Configuration ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Define log file paths
RECENT_LOG_BASE = os.path.join(LOG_DIR, "execution_{}.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

def setup_logger():
    """
    Sets up Loguru for JSON structured logging and file rotation.
    """
    logger.remove()  # Remove default handler

    # 1. Console Handler (Readable format)
    logger.add(sys.stderr, level="DEBUG", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

    # 2. JSON File Handler (Serialized for traceability)
    # Use rotation to keep only recent files logic below
    logger.add(os.path.join(LOG_DIR, "current.json"), 
               serialize=True, 
               level="DEBUG", 
               rotation="1 day")

    # 3. Error Log Isolation
    logger.add(ERROR_LOG, 
               level="ERROR", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", 
               filter=lambda record: record["level"].name == "ERROR")

def rotate_logs():
    """
    Maintains only the last 2 execution logs.
    """
    log_files = sorted([f for f in os.listdir(LOG_DIR) if f.startswith("execution_") and f.endswith(".log")], reverse=True)
    
    # Simple strategy: rename current to prev, and remove old ones
    if len(log_files) >= 2:
        for f in log_files[1:]: # Keep only the newest
            os.remove(os.path.join(LOG_DIR, f))

def extract_audio(video_path, output_wav):
    """
    Extracts 16kHz mono audio from video using FFmpeg.
    """
    logger.info(f"Starting audio extraction from: {video_path}")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        raise FileNotFoundError(f"Video file not found: {video_path}")

    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", "600",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        output_wav
    ]
    
    logger.debug(f"Executing command: {' '.join(command)}")
    
    try:
        process = subprocess.run(command, check=True, capture_output=True)
        # Decode as bytes and ignore errors to avoid UnicodeDecodeError with Japanese paths
        stdout = process.stdout.decode('utf-8', errors='ignore')
        logger.debug(f"FFmpeg stdout: {stdout}")
        logger.info(f"Audio successfully extracted to: {output_wav}")
        return True
    except subprocess.CalledProcessError as e:
        logger.exception("FFmpeg extraction failed.")
        stderr = e.stderr.decode('utf-8', errors='ignore')
        logger.error(f"FFmpeg stderr: {stderr}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during extraction: {e}")
        raise

def run_diarization(wav_path, seg_model, emb_model):
    """
    Runs sherpa-onnx diarization.
    """
    logger.info("Initializing Speaker Diarization process.")
    
    try:
        import sherpa_onnx
        logger.debug("Successfully imported sherpa_onnx.")
    except ImportError:
        logger.error("sherpa-onnx is not installed in the current environment.")
        print("Error: sherpa-onnx not installed. Run 'pip install sherpa-onnx'")
        return

    logger.debug(f"Model Paths - Seg: {seg_model}, Emb: {emb_model}")

    try:
        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=seg_model,
                ),
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=emb_model,
            ),
            clustering=sherpa_onnx.FastClusteringConfig(
                threshold=0.5,
            ),
        )

        if not config.validate():
            logger.error("Configuration validation failed. Check model file existence.")
            return

        logger.info("Loading Diarization models into memory.")
        sd = sherpa_onnx.OfflineSpeakerDiarization(config)

        logger.info(f"Reading audio file: {wav_path}")
        with wave.open(wav_path, "rb") as f:
            if f.getnchannels() != 1 or f.getframerate() != 16000:
                logger.error(f"Invalid audio format: Channels={f.getnchannels()}, Rate={f.getframerate()}")
                return
            
            samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            logger.debug(f"Audio samples loaded. Count: {len(samples)}")

        logger.info("Starting Diarization inference...")
        start_time = datetime.now()
        result = sd.process(samples)
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Inference completed in {duration:.2f} seconds.")

        # In sherpa-onnx Python API, sort_by_start_time() returns the list of segments
        segments = result.sort_by_start_time()

        print("\n--- Diarization Results ---")
        for s in segments:
            logger.info(f"Segment: Speaker {s.speaker} from {s.start:.2f}s to {s.end:.2f}s")
            print(f"[{s.start:6.2f}s -> {s.end:6.2f}s] Speaker {s.speaker}")

    except Exception as e:
        logger.exception(f"An error occurred during diarization: {e}")
        raise

def main():
    # Setup
    setup_logger()
    
    # Start of a new execution log file for rotation logic
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    execution_log = RECENT_LOG_BASE.format(timestamp)
    logger.add(execution_log, level="INFO", format="{time} | {level} | {message}")
    
    rotate_logs()
    
    logger.info("--- Starting Verification Pipeline ---")
    
    # Initialize ModelManager to ensure AI models are available
    model_dir = "models"
    mm = ModelManager(model_dir)
    mm.ensure_models()

    video_input = r"G:\マイドライブ\自己投資\非属人のYouTube運営についての無料セミナー.mp4"
    temp_wav = "temp_test_audio.wav"
    seg_model_path = os.path.join(model_dir, "sherpa-onnx-pyannote-segmentation-3-0", "model.onnx")
    emb_model_path = os.path.join(model_dir, "3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx")

    try:
        # 1. Extraction
        extract_audio(video_input, temp_wav)
        
        # 2. Check models
        if os.path.exists(seg_model_path) and os.path.exists(emb_model_path):
            run_diarization(temp_wav, seg_model_path, emb_model_path)
        else:
            logger.warning(f"Diarization skipped: Model files not found in 'models/'.")
            print(f"\nExtraction successful. Download ONNX models to 'models/' to proceed.")
            
    except Exception as e:
        logger.critical(f"Pipeline failed with critical error: {e}")
    finally:
        if os.path.exists(temp_wav):
            logger.debug(f"Cleaning up temporary file: {temp_wav}")
            os.remove(temp_wav)
        logger.info("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    main()
