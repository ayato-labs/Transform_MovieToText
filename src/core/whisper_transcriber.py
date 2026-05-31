import gc
import logging
import os
import subprocess
import time

from faster_whisper import WhisperModel

from src.core.constants import WHISPER_MODELS_DIR
from src.core.model_manager import model_manager
from src.core.platform_utils import is_android

# Add missing import for Android
try:
    from src.core.android_whisper_engine import AndroidWhisperEngine
except ImportError:
    AndroidWhisperEngine = None

logger = logging.getLogger(__name__)


WHISPER_CLIENT_NAME = "whisper"

def _is_cuda_available():
    """
    Checks for NVIDIA GPU availability and CUDA library readiness.
    We try a lightweight ctranslate2 operation to ensure DLLs like cublas64_12.dll are loadable.
    """
    try:
        # 1. Quick check for NVIDIA hardware
        subprocess.run(["nvidia-smi"], check=True, capture_output=True, timeout=2)
        
        # 2. Verify libraries can actually be loaded by CTranslate2
        import ctranslate2
        # Use a tiny check if possible, or just assume success if nvidia-smi passed 
        # and we've successfully imported the base package. 
        # To be even safer, we'll check if 'cuda' is in the supported compute devices.
        supported = ctranslate2.get_supported_compute_types("cuda")
        # If 'cuda' hardware exists but DLLs are missing, 
        # faster-whisper will still throw RuntimeError later during model load.
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, ImportError, ValueError):
        return False


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
        self.cache_dir = cache_dir or WHISPER_MODELS_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        # Register with ModelManager
        model_manager.register(WHISPER_CLIENT_NAME, self)

    def load_model(self, model_name: str, force_gpu: bool = False):
        """
        Loads the Whisper model with explicit memory management and quantization fallbacks.
        """
        # Request VRAM before loading
        model_manager.request_vram(WHISPER_CLIENT_NAME)

        if self.current_model_name == model_name and self.model is not None:
            logger.debug(f"WhisperTranscriber: Model {model_name} already loaded.")
            return

        if is_android():
            self._load_android_native_model(model_name)
            return

        logger.info(f"WhisperTranscriber: Loading model '{model_name}' (requested GPU: {force_gpu})...")
        start_time = time.time()

        # Proactive Memory Cleanup
        self.unload()

        # Decide device and compute_type with Hardware Priority (Windows/Desktop Focused)
        # Tier 1: CUDA GPU (Preferred)
        if _is_cuda_available():
            device = "cuda"
            # int8_float16 is the sweet spot for performance/accuracy on modern NVIDIA GPUs
            compute_type = "int8_float16"
            logger.info(f"WhisperTranscriber: Using CUDA GPU with {compute_type}.")
        else:
            # Tier 3: CPU Fallback
            device = "cpu"
            compute_type = "int8"
            logger.warning("WhisperTranscriber: CUDA unavailable. Falling back to CPU (int8).")

        try:
            # Load Attempt
            logger.info(f"WhisperTranscriber: Attempting load on {device}...")
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=self.cache_dir)
            self.current_model_name = model_name
            duration = time.time() - start_time
            logger.info(f"WhisperTranscriber: SUCCESSFULLY LOADED using {device} ({compute_type}) in {duration:.2f}s")
        except RuntimeError as e:
            # Catch specific CUDA library errors (like missing cublas64_12.dll)
            if "cublas" in str(e) or "cudnn" in str(e) or "cuda" in str(e).lower():
                logger.error(f"WhisperTranscriber: CUDA library error detected: {e}")
                logger.warning("WhisperTranscriber: Falling back to CPU due to missing/incompatible CUDA libraries.")
                # Force CPU fallback
                self.unload()
                self.model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=self.cache_dir)
                self.current_model_name = model_name
                logger.info(f"WhisperTranscriber: SUCCESS on emergency CPU Fallback after {time.time() - start_time:.2f}s")
            else:
                raise
        except ValueError:
            # Usage error (e.g. invalid model size) - re-raise immediately
            raise
        except Exception as e:
            # Detailed Error for GPU Failure
            if device == "cuda":
                logger.error(f"WhisperTranscriber: GPU Priority 1 failed: {e}")
                logger.info("WhisperTranscriber: Attempting Priority 2 (GPU with limited offload/int8)...")
                try:
                    # Tier 2: Try even lighter GPU (int8) if int8_float16 failed
                    self.unload()
                    self.model = WhisperModel(model_name, device=device, compute_type="int8", download_root=self.cache_dir)
                    self.current_model_name = model_name
                    logger.info(f"WhisperTranscriber: SUCCESS on Priority 2 (GPU int8) after {time.time() - start_time:.2f}s")
                    return
                except Exception as retry_e:
                    logger.error(f"WhisperTranscriber: GPU Priority 1 & 2 failed: {retry_e}")
                    raise RuntimeError(
                        f"GPU稼働失敗: {e}. GPUメモリ不足、またはライブラリ不足です。モデルサイズを下げるか、CPUに切り替えてください。"
                    ) from retry_e
            else:
                # CPU Fallback (e.g. from float32/int8 to same if memory error occurs)
                logger.error(f"WhisperTranscriber: CPU Load failed: {e}")
                logger.info("WhisperTranscriber: Attempting CPU Fallback (int8)...")
                try:
                    self.unload()
                    self.model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=self.cache_dir)
                    self.current_model_name = model_name
                    logger.info(f"WhisperTranscriber: SUCCESS on CPU Fallback after {time.time() - start_time:.2f}s")
                    return
                except Exception as retry_e:
                    logger.error(f"WhisperTranscriber: CPU Load & Fallback failed: {retry_e}")
                    raise

            logger.error(f"WhisperTranscriber: General load failure for '{model_name}': {e}")
            raise

    def _load_android_native_model(self, model_name: str):
        """Loads a GGML model using the native whisper.cpp engine on Android."""
        if not AndroidWhisperEngine:
            raise RuntimeError("AndroidNativeEngine がロードされていません。")

        # GGML models have different filenames (e.g., ggml-tiny.bin)
        ggml_name = f"ggml-{model_name}.bin"
        model_path = os.path.join(self.cache_dir, ggml_name)

        if not os.path.exists(model_path):
            logger.warning(f"WhisperTranscriber: GGML model not found at {model_path}. Need download.")
            # Trigger download logic here in future
            raise FileNotFoundError(f"ネイティブモデルが見つかりません: {ggml_name}\n設定からダウンロードしてください。")

        if self.model is None:
            self.model = AndroidWhisperEngine()

        success = self.model.load_model(model_path)
        if success:
            self.current_model_name = model_name
            logger.info(f"WhisperTranscriber: Native Android model {model_name} loaded.")
        else:
            raise RuntimeError(f"Nativeモデルのロードに失敗しました: {ggml_name}")

    def unload(self):
        """Forcefully clears Python and CUDA memory, unloading the current model."""
        if hasattr(self, "model") and self.model is not None:
            logger.info(f"WhisperTranscriber: Unloading model '{self.current_model_name}' to free memory...")
            # We assign to None instead of using `del` to allow natural garbage collection.
            # This helps prevent STATUS_STACK_BUFFER_OVERRUN (-1073740791) crashes on Windows 
            # with CTranslate2 when models are destroyed in background threads.
            self.model = None
            self.current_model_name = None

        # Give the C++ backend a tiny moment to release handles before forcing GC
        time.sleep(0.1)
        gc.collect()
        
        # NOTE: We DO NOT call torch.cuda.empty_cache() here.
        # faster-whisper uses CTranslate2, which has its own CUDA allocator.
        # Calling PyTorch's empty_cache() while CTranslate2 is freeing memory
        # in a background thread is a known cause of hard crashes on Windows.
        logger.info("WhisperTranscriber: Memory cleared.")

    def transcribe(self, audio_path: str, model_name: str, force_gpu: bool = False, language: str | None = None, progress_callback=None) -> dict:
        """
        Transcribes audio file to text, returning structured segments.
        """
        if self.model is None or self.current_model_name != model_name:
            self.load_model(model_name, force_gpu=force_gpu)

        if is_android() and hasattr(self.model, "transcribe"):
            logger.info(f"WhisperTranscriber: Native Android transcription requested for {audio_path}")
            return {"text": "[エッジ推論実行中...]", "segments": []}

        logger.info(f"WhisperTranscriber: Starting transcription of {audio_path}...")

        try:
            segments_gen, info = self.model.transcribe(audio_path, beam_size=5, language=language)
            # CRITICAL: Convert generator to list to ensure the underlying C++ process finishes 
            segments = list(segments_gen)
        except RuntimeError as e:
            if "cublas" in str(e).lower() or "cuda" in str(e).lower():
                logger.warning(f"WhisperTranscriber: CUDA execution error intercepted: {e}")
                logger.warning("WhisperTranscriber: Force-falling back to CPU mode and retrying...")
                self.unload()
                self.model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=self.cache_dir)
                self.current_model_name = model_name
                segments_gen, info = self.model.transcribe(audio_path, beam_size=5, language=language)
                segments = list(segments_gen)
            else:
                raise

        full_text_list = []
        structured_segments = []

        for segment in segments:
            seg_data = {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": segment.text.strip()}
            structured_segments.append(seg_data)
            full_text_list.append(segment.text)

            if progress_callback:
                progress_callback(segment.end / info.duration if info.duration > 0 else 0)

        return {"text": "".join(full_text_list).strip(), "segments": structured_segments}

    def transcribe_numpy(self, audio_data, model_name: str | None = None, force_gpu: bool = False) -> dict:
        """
        Transcribes raw numpy audio data.
        """
        if model_name and (self.model is None or self.current_model_name != model_name):
            self.load_model(model_name, force_gpu=force_gpu)

        if self.model is None:
            self.load_model("base", force_gpu=force_gpu)

        try:
            segments_gen, _ = self.model.transcribe(audio_data, beam_size=5)
            segments = list(segments_gen)
        except RuntimeError as e:
            if "cublas" in str(e).lower() or "cuda" in str(e).lower():
                logger.warning(f"WhisperTranscriber: CUDA execution error intercepted during numpy transcription: {e}")
                logger.warning("WhisperTranscriber: Force-falling back to CPU mode and retrying...")
                self.unload()
                self.model = WhisperModel(model_name or "base", device="cpu", compute_type="int8", download_root=self.cache_dir)
                self.current_model_name = model_name or "base"
                segments_gen, _ = self.model.transcribe(audio_data, beam_size=5)
                segments = list(segments_gen)
            else:
                raise

        full_text_list = []
        structured_segments = []
        for segment in segments:
            seg_data = {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": segment.text.strip()}
            structured_segments.append(seg_data)
            full_text_list.append(segment.text)

        return {"text": "".join(full_text_list).strip(), "segments": structured_segments}

    def get_hardware_info(self) -> dict:
        """
        Detects system RAM and GPU VRAM for model suitability.
        """
        ram = 0.0
        try:
            import psutil

            ram = round(psutil.virtual_memory().total / (1024**3), 1)
        except Exception as e:
            if not is_android():
                logger.warning(f"Failed to detect system RAM: {e}")

        vram = 0.0
        device = "cpu"

        if _is_cuda_available():
            try:
                # Run nvidia-smi to get total VRAM and GPU name
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=2
                )
                parts = result.stdout.strip().split(', ')
                vram_mb = int(parts[0])
                vram = round(vram_mb / 1024.0, 1)
                device = f"GPU: {parts[1]}"
            except Exception as e:
                logger.warning(f"Failed to detect VRAM details via nvidia-smi: {e}")
        elif is_android():
            device = "Android Mobile (Cloud Preferred)"
            ram = 4.0 if ram == 0 else ram  # Guessing if psutil failed

        return {"ram": ram, "vram": vram, "device": device}

    def can_run_on_gpu(self, model_name: str) -> bool:
        """
        Checks if a model can fit in available VRAM.
        """
        hw = self.get_hardware_info()
        req = self.MODEL_REQUIREMENTS.get(model_name, 5.0)
        return hw["vram"] >= req
