import logging
import os
import time

import numpy as np
from faster_whisper import WhisperModel

from .core.constants import DEFAULT_WHISPER_MODEL

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Handles transcription using faster-whisper.
    Supports both file-based and in-memory (numpy) audio.
    """

    MODEL_REQUIREMENTS = {
        "tiny": 0.5,
        "base": 1.0,
        "small": 2.0,
        "medium": 5.0,
        "large-v3": 10.0,
        "turbo": 6.0,
    }

    def __init__(self):
        self.model = None
        self.current_model_name = None
        self.last_warning = None

    def load_model(self, model_name=DEFAULT_WHISPER_MODEL, force_gpu=False):
        """Loads or switches the Whisper model."""
        device = "cuda" if force_gpu else "auto"
        # For 'turbo' model, we usually use float16 on GPU, int8 on CPU
        compute_type = "float16" if device == "cuda" else "int8"

        if self.model is None or self.current_model_name != model_name:
            logger.info(f"Loading Faster Whisper model: {model_name} on {device} ({compute_type})...")
            # faster-whisper uses WhisperModel
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self.current_model_name = model_name
            logger.info(f"Model {model_name} loaded successfully on {device}.")
        return self.model

    def get_hardware_info(self):
        """Returns detected hardware info for GPU support and RAM."""
        import psutil
        import torch

        cuda_available = torch.cuda.is_available()
        gpu_name = "None"
        vram_gb = 0

        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = round(vram_bytes / (1024**3), 1)

        ram_bytes = psutil.virtual_memory().total
        ram_gb = round(ram_bytes / (1024**3), 1)

        return {
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "vram": vram_gb,
            "ram": ram_gb,
            "compute_type": "float16" if cuda_available else "int8",
        }

    def can_run_on_gpu(self, model_name: str) -> bool:
        """Checks if the given model can run on the detected GPU VRAM."""
        hw = self.get_hardware_info()
        if not hw["cuda_available"]:
            return False

        req = self.MODEL_REQUIREMENTS.get(model_name, 10.0)  # Default to 10GB if unknown
        return hw["vram"] >= req

    def transcribe(self, path_or_io, model_name="base", force_gpu=False, language="ja", vad_filter=True, **kwargs):
        """
        Transcribes the file or BytesIO at the given path/object.
        Ensures the correct model is loaded.
        """
        if isinstance(path_or_io, str):
            if not os.path.exists(path_or_io):
                raise FileNotFoundError(f"Transcription file not found: {path_or_io}")
            file_size = os.path.getsize(path_or_io)
            if file_size == 0:
                raise ValueError(f"Transcription file is empty (0 bytes): {path_or_io}")
            input_source = path_or_io
        elif isinstance(path_or_io, np.ndarray):
            # Input is directly a numpy array (from live recorder)
            input_source = path_or_io
        else:
            # Assume it's a file-like object (BytesIO)
            input_source = path_or_io

        self.load_model(model_name, force_gpu=force_gpu)

        logger.info(f"Starting faster-whisper transcription (Device: {self.model.model.device}, Lang: {language})")
        start_time = time.time()

        try:
            # Remove initial_prompt entirely. It is a primary cause of hallucinations in Whisper.
            initial_prompt = None

            logger.info("Starting Whisper transcription with strict hallucination suppression.")
            segments, info = self.model.transcribe(
                input_source,
                beam_size=5,
                language=language,
                initial_prompt=initial_prompt,
                vad_filter=vad_filter,
                vad_parameters=dict(threshold=0.3, min_silence_duration_ms=1000, speech_pad_ms=200),
                condition_on_previous_text=False,  # CRUCIAL: Prevents repetitive looping hallucinations
                **kwargs,
            )

            # Convert segments to list to trigger actual transcription and check VAD
            segments_list = list(segments)

            # Log VAD info if available
            # info.duration is the original audio duration
            if hasattr(info, "duration_after_vad"):
                logger.info(f"VAD filter: {info.duration:.2f}s -> {info.duration_after_vad:.2f}s")

            result_text = "".join([s.text for s in segments_list]).strip()

            duration = time.time() - start_time
            logger.info(f"Transcription completed in {duration:.2f}s (Detected lang: {info.language}, Prob: {info.language_probability:.2f})")
            return result_text
        except Exception as e:
            logger.error(f"Error during faster-whisper transcription: {e}", exc_info=True)
            raise
