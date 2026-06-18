import json
import logging
import os

from .constants import DEFAULT_CONFIG_PATH

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration, persisting to AppData.
    Replaces .env dependency with hardcoded defaults and UI-managed settings.
    """
    
    # Hardcoded defaults (ADR-0008)
    DEFAULT_CONFIG = {
        "active_provider": "ollama_local",
        "whisper_model": "base",
        "llm_model": "gemma4:e2b",
        "llm_temperature": 0.3,
        "visual_capture_enabled": False,
        "local_smart_enabled": False,
        "force_gpu": False,
        "audio_source": "system",
        "knowledge_dir": "",
        "providers": {
            "ollama_local": {
                "base_url": "http://localhost:11434",
                "api_key": ""
            },
            "gemini_api": {
                "base_url": None,
                "api_key": ""
            }
        },
        "last_models": {
            "ollama_local": "gemma4:e2b",
            "gemini_api": "gemini-2.0-flash"
        }
    }

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.config = self.load_config()
        self._ensure_defaults()

    def load_config(self):
        """Loads config from file or returns defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    user_config = json.load(f)
                    logger.debug(f"Loaded config from {self.config_path}")
                    return user_config
            except Exception as e:
                logger.error(f"Error loading config from {self.config_path}: {e}")
        
        logger.info("No config file found. Using defaults.")
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Persists config to AppData."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.debug(f"Config saved to {self.config_path}")
        except Exception:
            logger.exception(f"Error saving config to {self.config_path}")

    def _ensure_defaults(self):
        """Deep merges defaults into loaded config to ensure all keys exist."""
        def merge(target, default):
            for key, val in default.items():
                if key not in target:
                    target[key] = val
                elif isinstance(val, dict) and isinstance(target[key], dict):
                    merge(target[key], val)
        
        merge(self.config, self.DEFAULT_CONFIG)

    # Provider Management
    def get_active_provider(self):
        return self.config.get("active_provider", "ollama_local")

    def set_active_provider(self, provider_name):
        if provider_name in ["ollama_local", "gemini_api"]:
            self.config["active_provider"] = provider_name
            logger.info(f"Active provider changed to: {provider_name}")
            self.save_config()

    def get_provider_config(self, provider_name=None):
        if not provider_name:
            provider_name = self.get_active_provider()
        return self.config.get("providers", {}).get(provider_name, {}).copy()

    def set_provider_config(self, provider_name, provider_config):
        if "providers" not in self.config:
            self.config["providers"] = {}
        
        self.config["providers"][provider_name] = provider_config
        
        # Log masked key
        log_key = provider_config.get("api_key", "")
        masked = f"{log_key[:4]}...{log_key[-4:]}" if len(log_key) > 8 else "****"
        logger.info(f"Updated config for {provider_name} (API Key: {masked})")
        self.save_config()

    # Model Management
    def get_llm_model(self):
        return self.config.get("llm_model", "gemma3:2b")

    def set_llm_model(self, model_name):
        self.config["llm_model"] = model_name
        self.save_config()

    def get_llm_temperature(self) -> float:
        return self.config.get("llm_temperature", 0.7)

    def set_llm_temperature(self, value: float):
        self.config["llm_temperature"] = float(value)
        self.save_config()

    def get_last_model(self, provider_name=None):
        if not provider_name:
            provider_name = self.get_active_provider()
        return self.config.get("last_models", {}).get(provider_name)

    def set_last_model(self, model_name, provider_name=None):
        if not provider_name:
            provider_name = self.get_active_provider()
        if "last_models" not in self.config:
            self.config["last_models"] = {}
        self.config["last_models"][provider_name] = model_name
        self.save_config()

    def get_llm_models(self, provider_name=None):
        """Fetches models from live client or returns fallbacks."""
        if not provider_name:
            provider_name = self.get_active_provider()
        
        try:
            from src.llm.factory import LLMFactory
            conf = self.get_provider_config(provider_name)
            client = LLMFactory.create_client(
                provider_name=provider_name, 
                api_key=conf.get("api_key"), 
                base_url=conf.get("base_url")
            )
            return client.get_available_models()
        except Exception as e:
            logger.warning(f"Could not fetch live models for {provider_name}: {e}")
            from .constants import DEFAULT_LLM_MODELS
            return DEFAULT_LLM_MODELS.get(provider_name, ["gemma3:2b"])

    # Feature Flags
    def get_whisper_model(self):
        return self.config.get("whisper_model", "base")

    def set_whisper_model(self, model_name):
        self.config["whisper_model"] = model_name
        self.save_config()

    def get_visual_capture_enabled(self):
        return self.config.get("visual_capture_enabled", False)

    def set_visual_capture_enabled(self, enabled: bool):
        self.config["visual_capture_enabled"] = enabled
        self.save_config()

    def get_local_smart_enabled(self):
        return self.config.get("local_smart_enabled", False)

    def set_local_smart_enabled(self, enabled: bool):
        self.config["local_smart_enabled"] = enabled
        self.save_config()

    def get_force_gpu(self):
        return self.config.get("force_gpu", False)

    def set_force_gpu(self, enabled: bool):
        self.config["force_gpu"] = enabled
        self.save_config()

    def get_audio_source(self):
        return self.config.get("audio_source", "system")

    def set_audio_source(self, source):
        self.config["audio_source"] = source
        self.save_config()

    def get_knowledge_dir(self):
        return self.config.get("knowledge_dir", "")

    def set_knowledge_dir(self, directory_path):
        self.config["knowledge_dir"] = directory_path
        self.save_config()

    def get_edition(self):
        """Returns the current application edition. Defaulting to PRO for local use."""
        from .constants import AppEdition
        return AppEdition.PRO

    def get_llm_client(self, provider_name=None):
        """Factory helper for the specified or active provider."""
        from src.llm.factory import LLMFactory
        provider = provider_name or self.get_active_provider()
        conf = self.get_provider_config(provider)
        return LLMFactory.create_client(
            provider_name=provider,
            api_key=conf.get("api_key"),
            base_url=conf.get("base_url"),
            temperature=self.get_llm_temperature()
        )
