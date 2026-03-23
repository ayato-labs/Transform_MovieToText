# Paths
DEFAULT_DB_PATH = "data/history.db"
DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_RECORDS_DIR = "data/records"
TEMP_CHUNKS_DIR = "temp_chunks"

# Recording Defaults
DEFAULT_SEGMENT_TIME = 30
DEFAULT_OVERLAP = 5
DEFAULT_SAMPLE_RATE = 16000

# Provider Defaults
DEFAULT_PROVIDERS = {
    "gemini": {"api_key": ""},
    "ollama_local": {"api_key": "", "base_url": "http://localhost:11434"},
    "ollama_cloud": {"api_key": "", "base_url": "https://ollama.com"},
}
DEFAULT_ACTIVE_PROVIDER = "gemini"
DEFAULT_WHISPER_MODEL = "base"
