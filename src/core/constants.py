import os
from enum import Enum
from pathlib import Path

from .platform_utils import get_local_app_data_path, get_roaming_app_data_path

# Standard Windows AppData Roots
APP_DATA_DIR = get_roaming_app_data_path()
LOCAL_DATA_DIR = get_local_app_data_path()

# Specific Paths
DEFAULT_DB_PATH = os.path.join(APP_DATA_DIR, "history.db")
DEFAULT_CONFIG_PATH = os.path.join(APP_DATA_DIR, "config.json")
DEFAULT_RECORDS_DIR = os.path.join(APP_DATA_DIR, "records")
LOGS_DIR = os.path.join(APP_DATA_DIR, "logs")

# Heavy Assets (Models) in Local AppData
MODELS_DIR = os.path.join(LOCAL_DATA_DIR, "models")
WHISPER_MODELS_DIR = os.path.join(MODELS_DIR, "whisper")

# Temp Directories
TEMP_DIR = os.path.join(LOCAL_DATA_DIR, "temp")
TEMP_CHUNKS_DIR = os.path.join(TEMP_DIR, "chunks")
TEMP_VIDEO_DIR = os.path.join(TEMP_DIR, "frames")
DEFAULT_KNOWLEDGE_DIR = str(Path.home() / "Documents" / "AyatoKnowledge")

# Recording Defaults
DEFAULT_SEGMENT_TIME = 30
DEFAULT_OVERLAP = 5
DEFAULT_SAMPLE_RATE = 16000

# Provider Defaults (Restricted to Local Privacy-First execution)
DEFAULT_PROVIDERS = {
    "ollama_local": {"api_key": "", "base_url": "http://localhost:11434"},
    "gemini_api": {"api_key": "", "base_url": None},
}
DEFAULT_ACTIVE_PROVIDER = "ollama_local"
DEFAULT_LLM_MODELS = {
    "ollama_local": ["gemma4:e2b"],
    "gemini_api": ["gemini-2.0-flash"],
}

DEFAULT_WHISPER_MODEL = "base"
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]


class AppEdition(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Legacy Edition Restrictions (Maintaining for UI compatibility)
EDITION_RESTRICTIONS = {
    AppEdition.FREE: {
        "allowed_providers": ["ollama_local", "gemini_api"],
        "max_transcript_chars": 50000,
        "db_type": "sqlite",
    },
    AppEdition.PRO: {
        "allowed_providers": ["ollama_local", "gemini_api"],
        "max_transcript_chars": 200000,
        "db_type": "sqlite",
    },
    AppEdition.ENTERPRISE: {
        "allowed_providers": ["ollama_local", "gemini_api"],
        "max_transcript_chars": 1000000,
        "db_type": "mysql",
    },
}
