import logging
import os
import subprocess
import time

import numpy as np
import psutil
import torch
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Backend class for Whisper transcription logic.
    Handles hardware detection, model loading, and transcription.
    """

    # Modified for faster-whisper (CTranslate2 float16) approximate VRAM usage
    MODEL_REQUIREMENTS = {
        "tiny": 0.3,
        "base": 0.5,
        "small": 1.0,
        "medium": 2.5,
        "large-v3": 3.5,
        "turbo": 2.0,
    }

    def __init__(self):
        self.model = None
        self.current_model_name = None
        self._hardware_info = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.last_warning = ""
        logger.info(f"Initialized WhisperTranscriber on device: {self.device}")

    @staticmethod
    def _detect_vram_nvidia_smi():
        """Detects VRAM using nvidia-smi (driver-level, independent of PyTorch)."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                vram_mb = float(result.stdout.strip().split("\n")[0])
                return round(vram_mb / 1024, 1)
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
            logger.debug(f"nvidia-smi check failed: {e}")
        return 0.0

    def get_hardware_info(self):
        """Returns detected VRAM (via nvidia-smi) and total RAM in GB. Cached."""
        if self._hardware_info is not None:
            return self._hardware_info

        info = {"vram": 0.0, "ram": 0.0}

        # RAM detection
        ram_bytes = psutil.virtual_memory().total
        info["ram"] = round(ram_bytes / (1024**3), 1)

        # VRAM detection (nvidia-smi first, torch.cuda as fallback)
        info["vram"] = self._detect_vram_nvidia_smi()
        if info["vram"] == 0.0 and torch.cuda.is_available():
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            info["vram"] = round(vram_bytes / (1024**3), 1)

        logger.info(f"Hardware detected - RAM: {info['ram']}GB, VRAM: {info['vram']}GB")
        self._hardware_info = info
        return info

    def get_model_device(self, model_name, force_gpu=False):
        """Determines the best device (cuda or cpu) for a specific model."""
        self.last_warning = ""

        if not torch.cuda.is_available():
            return "cpu"

        if force_gpu:
            logger.info(f"GPU usage FORCED for model {model_name}.")
            return "cuda"

        req = self.MODEL_REQUIREMENTS.get(model_name, 1.0)
        vram = self.get_hardware_info()["vram"]

        if vram >= req:
            return "cuda"
        else:
            reason = f"VRAM不足 (必要: {req}GB / 使用可能: {vram}GB)。安全のためCPUに切り替えました。"
            self.last_warning = reason
            logger.warning(f"GPU safety triggered: {reason}")
            return "cpu"

    def can_run_on_gpu(self, model_name):
        """Checks if the GPU has enough VRAM for this model (independent of PyTorch CUDA)."""
        req = self.MODEL_REQUIREMENTS.get(model_name, 1.0)
        vram = self.get_hardware_info()["vram"]
        return vram >= req

    def load_model(self, model_name="base", force_gpu=False):
        """Loads or reloads the Faster Whisper model on the appropriate device."""
        device = self.get_model_device(model_name, force_gpu=force_gpu)
        compute_type = "float16" if device == "cuda" else "int8"

        if self.model is None or self.current_model_name != model_name:
            logger.info(f"Loading Faster Whisper model: {model_name} on {device} ({compute_type})...")
            # faster-whisper uses WhisperModel
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self.current_model_name = model_name
            logger.info(f"Model {model_name} loaded successfully on {device}.")
        return self.model

    def transcribe(self, path_or_io, model_name="base", force_gpu=False):
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

        logger.info(f"Starting faster-whisper transcription (Device: {self.model.model.device})")
        start_time = time.time()

        try:
            # faster-whisper returns a generator of segments
            segments, info = self.model.transcribe(input_source, beam_size=5)

            # Combine segments into a single string
            text_parts = [segment.text for segment in segments]
            full_text = "".join(text_parts).strip()

            duration = time.time() - start_time
            logger.info(f"Transcription completed in {duration:.2f}s (Detected lang: {info.language})")
            return full_text
        except Exception as e:
            logger.error(f"Error during faster-whisper transcription: {e}", exc_info=True)
            raise
