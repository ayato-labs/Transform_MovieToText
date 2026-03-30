import gc
import logging
import os
import time

import torch

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
        from faster_whisper import WhisperModel

        if self.current_model_name == model_name and self.model is not None:
            logger.debug(f"WhisperTranscriber: Model {model_name} already loaded.")
            return

        logger.info(f"WhisperTranscriber: Loading model '{model_name}' (requested GPU: {force_gpu})...")
        start_time = time.time()

        # Proactive Memory Cleanup
        self.unload_model()

        # Decide device and compute_type with Hardware Priority
        # Tier 1: GPU Native (Standardized to int8_float16 for best efficiency/accuracy ratio)
        if force_gpu and torch.cuda.is_available():
            device = "cuda"
            compute_type = "int8_float16"
            logger.info(f"WhisperTranscriber: Loading Priority 1 (GPU {compute_type}).")
        else:
            # Fallback or CPU-forced
            device = "cpu"
            compute_type = "int8"
            if force_gpu:
                logger.warning("WhisperTranscriber: GPU requested but unavailable. Falling back to CPU.")
            else:
                logger.info(f"WhisperTranscriber: Loading Priority 3 (CPU {compute_type}).")

        try:
            # Load Attempt
            logger.info(f"WhisperTranscriber: Attempting load on {device} with {compute_type}...")
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=self.cache_dir)
            self.current_model_name = model_name
            duration = time.time() - start_time
            logger.info(f"WhisperTranscriber: SUCCESSFULLY LOADED using {device} ({compute_type}) in {duration:.2f}s")
        except Exception as e:
            # Detailed Error for GPU Failure
            if device == "cuda":
                logger.error(f"WhisperTranscriber: GPU Priority 1 failed: {e}")
                logger.info("WhisperTranscriber: Attempting Priority 2 (GPU with limited offload/int8)...")
                try:
                    # Tier 2: Try even lighter GPU (int8) if int8_float16 failed
                    self._clear_memory()
                    self.model = WhisperModel(model_name, device=device, compute_type="int8", download_root=self.cache_dir)
                    self.current_model_name = model_name
                    logger.info(f"WhisperTranscriber: SUCCESS on Priority 2 (GPU int8) after {time.time() - start_time:.2f}s")
                    return
                except Exception as retry_e:
                    logger.error(f"WhisperTranscriber: GPU Priority 1 & 2 failed: {retry_e}")
                    raise RuntimeError(
                        f"GPU稼働失敗: {e}. GPUメモリ不足、またはライブラリ不足です。モデルサイズを下げるか、CPUに切り替えてください。"
                    ) from retry_e

            logger.error(f"WhisperTranscriber: General load failure for '{model_name}': {e}")
            raise

            logger.error(f"WhisperTranscriber: Failed to load model '{model_name}': {e}")
            raise

    def unload_model(self):
        """Forcefully clears Python and CUDA memory, unloading the current model."""
        if hasattr(self, "model") and self.model is not None:
            logger.info(f"WhisperTranscriber: Unloading model '{self.current_model_name}' to free memory...")
            del self.model
            self.model = None
            self.current_model_name = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("WhisperTranscriber: Memory and CUDA cache cleared.")

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
