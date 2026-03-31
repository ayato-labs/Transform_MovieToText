# Paths
DEFAULT_DB_PATH = "data/history.db"
DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_RECORDS_DIR = "data/history"
TEMP_DIR = "data/temp"
TEMP_CHUNKS_DIR = "data/temp/chunks"
TEMP_VIDEO_DIR = "data/temp/frames"

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
DEFAULT_LLM_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
    "ollama_local": ["gemma3:1b", "gemma3:4b", "gemma3:12b", "llama3.2", "mistral-nemo", "phi4"],
    "ollama_cloud": ["gemma3:4b", "gemma3:27b", "llama3.3", "mistral-large"],
}
DEFAULT_WHISPER_MODEL = "base"
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# Embedding Defaults (Privacy-First: FastEmbed is the non-negotiable default)
DEFAULT_EMBEDDING_PROVIDER = "local"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
