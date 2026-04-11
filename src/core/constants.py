import os
from enum import Enum

from .platform_utils import get_app_data_path

# Root App Data
APP_DATA_DIR = get_app_data_path()

# Paths
DEFAULT_DB_PATH = os.path.join(APP_DATA_DIR, "history.db")
DEFAULT_CONFIG_PATH = os.path.join(APP_DATA_DIR, "config.json")
DEFAULT_RECORDS_DIR = os.path.join(APP_DATA_DIR, "history")
TEMP_DIR = os.path.join(APP_DATA_DIR, "temp")
TEMP_CHUNKS_DIR = os.path.join(APP_DATA_DIR, "temp", "chunks")
TEMP_VIDEO_DIR = os.path.join(APP_DATA_DIR, "temp", "frames")

# Recording Defaults
DEFAULT_SEGMENT_TIME = 30
DEFAULT_OVERLAP = 5
DEFAULT_SAMPLE_RATE = 16000

# Provider Defaults
DEFAULT_PROVIDERS = {
    "gemini": {"api_key": ""},
    "ayato_cloud": {"api_key": "", "base_url": "https://api.ayato-ai.com/v1"},  # Managed Gateway
    "ollama_local": {"api_key": "", "base_url": "http://localhost:11434"},
    "ollama_cloud": {"api_key": "", "base_url": "https://ollama.com"},
}
DEFAULT_ACTIVE_PROVIDER = "ollama_local"  # Default to Local for Privacy-First
DEFAULT_LLM_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
    "ayato_cloud": ["gemini-2.0-flash", "gemini-1.5-pro", "gemma3-27b"],  # Models provided via Gateway
    "ollama_local": ["gemma3:1b", "gemma3:4b", "gemma3:12b", "llama3.2", "mistral-nemo", "phi4"],
    "ollama_cloud": ["gemma3:4b", "gemma3:27b", "llama3.3", "mistral-large"],
}
DEFAULT_WHISPER_MODEL = "base"
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# Embedding Defaults (Privacy-First: FastEmbed is the non-negotiable default)
DEFAULT_EMBEDDING_PROVIDER = "local"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# --- Business Edition Management ---


class AppEdition(Enum):
    FREE = "free"  # Local SQLite, Gemma Local LLM only
    PRO = "pro"  # Local SQLite, All LLM APIs (Gemini, etc.)
    ENTERPRISE = "enterprise"  # MySQL, All LLM APIs, Custom Support


EDITION_RESTRICTIONS = {
    AppEdition.FREE: {
        "allowed_providers": ["ollama_local"],
        "allowed_models_prefix": "gemma",  # Only allow models starting with gemma
        "disallowed_keywords": ["cloud"],  # Explicitly block any model with 'cloud' in name
        "db_type": "sqlite",
    },
    AppEdition.PRO: {"allowed_providers": ["ayato_cloud", "gemini", "ollama_local", "ollama_cloud"], "allowed_models": "*", "db_type": "sqlite"},
    AppEdition.ENTERPRISE: {
        "allowed_providers": ["ayato_cloud", "gemini", "ollama_local", "ollama_cloud"],
        "allowed_models": "*",
        "db_type": "mysql",
    },
}
