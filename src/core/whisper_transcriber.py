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
        if self.model is not None:
            del self.model
            self.model = None
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        device = "cuda" if force_gpu and torch.cuda.is_available() else "cpu"
        # Standard compute types based on device
        compute_type = "float16" if device == "cuda" else "int8"

        try:
            # 2. Initial Load Attempt
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=self.cache_dir)
            self.current_model_name = model_name
            logger.info(f"WhisperTranscriber: Successfully loaded '{model_name}' on {device}")
        except Exception as e:
            # 3. Robust Fallback: Quantization (mkl_malloc relief)
            if "mkl_malloc" in str(e) or "out of memory" in str(e).lower():
                logger.warning(f"WhisperTranscriber: Memory allocation failed for '{model_name}'. Retrying with int8_float16 fallback...")
                
                # Clear again before retry
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                try:
                    # Retry with more aggressive quantization
                    self.model = WhisperModel(model_name, device=device, compute_type="int8_float16", download_root=self.cache_dir)
                    self.current_model_name = model_name
                    logger.info(f"WhisperTranscriber: Loaded '{model_name}' using int8_float16 fallback.")
                    return
                except Exception as retry_e:
                    logger.error(f"WhisperTranscriber: Fallback failed: {retry_e}")
            
            logger.error(f"WhisperTranscriber: Failed to load model '{model_name}': {e}")
            raise RuntimeError(f"Whisper model load error: {e}")

    def transcribe(
        self, audio_path: str, model_name: str, force_gpu: bool = False, language: str | None = None, progress_callback=None
    ) -> str:
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
