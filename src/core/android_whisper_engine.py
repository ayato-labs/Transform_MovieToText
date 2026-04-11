import ctypes
import logging

logger = logging.getLogger(__name__)


class WhisperContext(ctypes.Structure):
    pass


class WhisperParams(ctypes.Structure):
    _fields_ = [
        ("strategy", ctypes.c_int),
        ("n_threads", ctypes.c_int),
        ("n_max_text_ctx", ctypes.c_int),
        ("offset_ms", ctypes.c_int),
        ("duration_ms", ctypes.c_int),
        ("translate", ctypes.c_bool),
        ("no_context", ctypes.c_bool),
        ("single_segment", ctypes.c_bool),
        ("print_special", ctypes.c_bool),
        ("print_progress", ctypes.c_bool),
        ("print_realtime", ctypes.c_bool),
        ("print_timestamps", ctypes.c_bool),
        ("token_timestamps", ctypes.c_bool),
        ("thold_pt", ctypes.c_float),
        ("thold_pt_ste", ctypes.c_float),
        ("entropy_thold", ctypes.c_float),
        ("logprob_thold", ctypes.c_float),
        ("language", ctypes.c_char_p),
        ("detect_language", ctypes.c_bool),
    ]


class AndroidWhisperEngine:
    """
    Python wrapper for whisper.cpp shared library on Android using ctypes.
    Expects libwhisper.so to be available in the app's native library path.
    """

    def __init__(self, lib_path: str = "libwhisper.so"):
        self.lib = None
        self.ctx = None
        self._load_library(lib_path)

    def _load_library(self, lib_path: str):
        try:
            # On Android, libraries in jniLibs are usually available by name
            self.lib = ctypes.CDLL(lib_path)

            # Define C-API function signatures
            self.lib.whisper_init_from_file.restype = ctypes.POINTER(WhisperContext)
            self.lib.whisper_init_from_file.argtypes = [ctypes.c_char_p]

            self.lib.whisper_full_default_params.restype = WhisperParams
            self.lib.whisper_full_default_params.argtypes = [ctypes.c_int]

            self.lib.whisper_full.restype = ctypes.c_int
            self.lib.whisper_full.argtypes = [ctypes.POINTER(WhisperContext), WhisperParams, ctypes.POINTER(ctypes.c_float), ctypes.c_int]

            self.lib.whisper_full_n_segments.restype = ctypes.c_int
            self.lib.whisper_full_n_segments.argtypes = [ctypes.POINTER(WhisperContext)]

            self.lib.whisper_full_get_segment_text.restype = ctypes.c_char_p
            self.lib.whisper_full_get_segment_text.argtypes = [ctypes.POINTER(WhisperContext), ctypes.c_int]

            self.lib.whisper_free.argtypes = [ctypes.POINTER(WhisperContext)]

            logger.info("AndroidWhisperEngine: Native library loaded successfully.")
        except Exception as e:
            logger.error(f"AndroidWhisperEngine: Failed to load native library '{lib_path}': {e}")
            self.lib = None

    def load_model(self, model_path: str) -> bool:
        if not self.lib:
            return False

        if self.ctx:
            self.lib.whisper_free(self.ctx)

        logger.info(f"AndroidWhisperEngine: Loading model from {model_path}...")
        self.ctx = self.lib.whisper_init_from_file(model_path.encode("utf-8"))

        if not self.ctx:
            logger.error("AndroidWhisperEngine: Failed to initialize whisper context.")
            return False
        return True

    def transcribe(self, audio_data: list[float], language: str = "ja") -> dict:
        if not self.ctx or not self.lib:
            return {"text": "", "error": "Engine not initialized"}

        # Convert to C-float array
        c_float_array = (ctypes.c_float * len(audio_data))(*audio_data)

        # Get default params (0 for WHISPER_STRATEGY_GREEDY)
        params = self.lib.whisper_full_default_params(0)
        params.language = language.encode("utf-8")
        params.n_threads = 4  # Optimized for mobile

        logger.info("AndroidWhisperEngine: Starting native transcription...")
        result = self.lib.whisper_full(self.ctx, params, c_float_array, len(audio_data))

        if result != 0:
            return {"text": "", "error": f"Transcription failed with code {result}"}

        # Extract segments
        n_segments = self.lib.whisper_full_n_segments(self.ctx)
        full_text = ""
        segments = []

        for i in range(n_segments):
            text = self.lib.whisper_full_get_segment_text(self.ctx, i).decode("utf-8")
            full_text += text
            segments.append({"text": text})

        return {"text": full_text.strip(), "segments": segments}

    def __del__(self):
        if self.ctx and self.lib:
            self.lib.whisper_free(self.ctx)
