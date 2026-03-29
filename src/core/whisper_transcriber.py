import gc
import logging
import os

import torch
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Handles Whisper model operations including resource-safe loading and transcription.
    """

    # Estimated VRAM requirements in GB for int8_float16 (Standardized for safety)
    MODEL_REQUIREMENTS = {
        "tiny": 0.5,
        "base": 0.5,
        "small": 1.0,
        "medium": 2.5,
        "large-v2": 4.5,  # int8_float16 fits in ~4GB broadly, but 4.5 for buffer
        "large-v3": 4.5,
    }

    def __init__(self, cache_dir: str | None = None):
        self.model = None
        self.current_model_name = None
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), "data", "models", "whisper")
        os.makedirs(self.cache_dir, exist_ok=True)

    def load_model(self, model_name: str, force_gpu: bool = False):
        """
        Loads the Whisper model with explicit memory management and quantization fallbacks.
        """
        if self.current_model_name == model_name and self.model is not None:
            return

        logger.info(f"WhisperTranscriber: Resource-safe loading model '{model_name}' (GPU: {force_gpu})...")

        # 1. Proactive Memory Cleanup
        self._clear_memory()

        device = "cuda" if force_gpu and torch.cuda.is_available() else "cpu"
        # DEFAULT: Use int8_float16 for best performance/VRAM ratio on GPU
        compute_type = "int8_float16" if device == "cuda" else "int8"

        # 2. VRAM Safety Pre-check
        if device == "cuda":
            hw = self.get_hardware_info()
            required = self.MODEL_REQUIREMENTS.get(model_name, 5.0)
            if hw["vram"] < (required - 0.5):  # Allow a small margin
                logger.warning(f"WhisperTranscriber: VRAM ({hw['vram']}GB) is likely insufficient for '{model_name}' ({required}GB).")
                # We still try, but with a warning. If it's truly impossible, catch below.

        try:
            # 3. Initial Load Attempt (Preferred: int8_float16)
            logger.info(f"WhisperTranscriber: Loading '{model_name}' on {device} with {compute_type}...")
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=self.cache_dir)
            self.current_model_name = model_name
            logger.info(f"WhisperTranscriber: Successfully loaded '{model_name}'")
        except Exception as e:
            # 4. Crisis Fallback: Strict int8 (Smallest footprint)
            err_str = str(e).lower()
            if "out of memory" in err_str or "mkl_malloc" in err_str or "cuda error" in err_str:
                logger.warning("WhisperTranscriber: OOM/Allocation error. Retrying with ultra-light int8...")
                self._clear_memory()
                try:
                    self.model = WhisperModel(model_name, device=device, compute_type="int8", download_root=self.cache_dir)
                    self.current_model_name = model_name
                    logger.info(f"WhisperTranscriber: Loaded '{model_name}' using strict int8.")
                    return
                except Exception as retry_e:
                    self._clear_memory()
                    logger.error(f"WhisperTranscriber: All GPU load attempts failed: {retry_e}")
                    raise RuntimeError(f"VRAM不足: {model_name} をロードできません。モデルを下げるかCPUを使用してください。") from retry_e

            logger.error(f"WhisperTranscriber: Failed to load model '{model_name}': {e}")
            raise

    def _clear_memory(self):
        """Forcefully clears Python and CUDA memory."""
        if hasattr(self, "model") and self.model is not None:
            del self.model
            self.model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def transcribe(self, audio_path: str, model_name: str, force_gpu: bool = False, language: str | None = None, progress_callback=None) -> str:
        """
        Transcribes audio file to text.
        """
        if self.model is None or self.current_model_name != model_name:
            self.load_model(model_name, force_gpu=force_gpu)

        logger.info(f"WhisperTranscriber: Starting transcription of {audio_path}...")

        segments, info = self.model.transcribe(audio_path, beam_size=5, language=language)

        full_text = []
        # Note: segments is a generator
        for segment in segments:
            full_text.append(segment.text)
            if progress_callback:
                # Approximate progress (since we don't know total duration easily here)
                progress_callback(segment.end / info.duration if info.duration > 0 else 0)

        return "".join(full_text).strip()

    def get_hardware_info(self) -> dict:
        """
        Detects system RAM and GPU VRAM for model suitability.
        """
        import psutil

        ram = round(psutil.virtual_memory().total / (1024**3), 1)
        vram = 0.0
        device = "cpu"

        if torch.cuda.is_available():
            try:
                device_id = torch.cuda.current_device()
                vram_bytes = torch.cuda.get_device_properties(device_id).total_memory
                vram = round(vram_bytes / (1024**3), 1)
                device = torch.cuda.get_device_name(device_id)
            except Exception as e:
                logger.warning(f"Failed to detect VRAM details: {e}")

        return {"ram": ram, "vram": vram, "device": device}

    def can_run_on_gpu(self, model_name: str) -> bool:
        """
        Checks if a model can fit in available VRAM.
        """
        hw = self.get_hardware_info()
        req = self.MODEL_REQUIREMENTS.get(model_name, 5.0)
        return hw["vram"] >= req
