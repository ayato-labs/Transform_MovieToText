import json
import logging
import os

from dotenv import load_dotenv

from .constants import DEFAULT_ACTIVE_PROVIDER, DEFAULT_CONFIG_PATH
from .migrator import ConfigMigrator

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        load_dotenv()  # Load environment variables from .env if it exists
        self.config_path = config_path
        self.config = self.load_config()
        self._migrate_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return {}

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.debug(f"Config saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)

    def _migrate_config(self):
        """Migrates old config structure using ConfigMigrator."""
        if ConfigMigrator.migrate(self.config):
            self.save_config()

    def get_active_provider(self):
        # We only support local now.
        return DEFAULT_ACTIVE_PROVIDER

    def set_active_provider(self, provider_name):
        # Fixed to local. Kept for API compatibility.
        logger.info(f"Ignored request to set provider to {provider_name}. Only ollama_local is supported.")

    def get_provider_config(self, provider_name="ollama_local"):
        conf = self.config.get("providers", {}).get(provider_name, {}).copy()

        # Override with environment variables if present
        env_key = f"{provider_name.upper()}_API_KEY"
        env_val = os.getenv(env_key)
        if env_val:
            logger.debug(f"Using API key from environment for {provider_name}")
            conf["api_key"] = env_val

        return conf

    def set_provider_config(self, provider_name, provider_config):
        if "providers" not in self.config:
            self.config["providers"] = {}

        # Mask API key in log if present
        log_config = provider_config.copy()
        if "api_key" in log_config and log_config["api_key"]:
            key = log_config["api_key"]
            log_config["api_key"] = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"

        logger.info(f"Updating config for provider {provider_name}: {log_config}")
        self.config["providers"][provider_name] = provider_config
        self.save_config()

    def get_last_model(self, provider_name=None):
        provider_name = "ollama_local"
        return self.config.get("last_models", {}).get(provider_name, "gemma3:2b")

    def set_last_model(self, model_name, provider_name=None):
        provider_name = "ollama_local"
        if "last_models" not in self.config:
            self.config["last_models"] = {}
        self.config["last_models"][provider_name] = model_name
        self.save_config()

    def get_llm_models(self, provider_name=None):
        provider_name = "ollama_local"
        
        try:
            from src.llm.factory import LLMFactory

            conf = self.get_provider_config(provider_name)
            client = LLMFactory.create_client(provider_name=provider_name, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            installed_models = client.get_available_models()

            if installed_models:
                # Filter to only show Gemma models
                valid_models = [m for m in installed_models if "gemma" in m.lower()]
                if valid_models:
                    return valid_models
        except Exception as e:
            logger.warning(f"Failed to fetch live models for {provider_name}: {e}")

        # Fallback to constants if live fetch fails or no Gemma models are installed yet
        from .constants import DEFAULT_LLM_MODELS
        return DEFAULT_LLM_MODELS.get(provider_name, [])

    def get_whisper_model(self):
        return self.config.get("whisper_model", "base")

    def set_whisper_model(self, model_name):
        old = self.get_whisper_model()
        if old != model_name:
            self.config["whisper_model"] = model_name
            logger.info(f"Whisper model changed: {old} -> {model_name}")
            self.save_config()

    def get_visual_capture_enabled(self):
        """Returns whether screen/video capture is enabled."""
        return self.config.get("visual_capture_enabled", False)

    def set_visual_capture_enabled(self, enabled: bool):
        """Sets whether screen/video capture is enabled."""
        old = self.get_visual_capture_enabled()
        if old != enabled:
            self.config["visual_capture_enabled"] = enabled
            logger.info(f"Visual capture setting changed: {old} -> {enabled}")
            self.save_config()

    def get_local_smart_enabled(self):
        """Returns whether Local Smart optimization is enabled."""
        return self.config.get("local_smart_enabled", False)

    def set_local_smart_enabled(self, enabled: bool):
        """Sets whether Local Smart optimization is enabled."""
        old = self.get_local_smart_enabled()
        if old != enabled:
            self.config["local_smart_enabled"] = enabled
            logger.info(f"Local Smart setting changed: {old} -> {enabled}")
            self.save_config()

    def get_llm_model(self):
        """Returns the current LLM model name (e.g. for summary)."""
        return self.config.get("llm_model", "gemma3:2b")  # Local default

    def set_llm_model(self, model_name):
        """Sets the LLM model name."""
        old = self.get_llm_model()
        if old != model_name:
            self.config["llm_model"] = model_name
            logger.info(f"LLM model changed: {old} -> {model_name}")
            self.save_config()

    def get_force_gpu(self):
        return self.config.get("force_gpu", False)

    def set_force_gpu(self, enabled):
        old = self.get_force_gpu()
        if old != enabled:
            self.config["force_gpu"] = enabled
            logger.info(f"Force GPU setting changed: {old} -> {enabled}")
            self.save_config()

    def get_llm_client(self, provider_name=None, api_key=None):
        """Returns an initialized LLM client for the provider."""
        provider_name = "ollama_local"
        conf = self.get_provider_config(provider_name)
        from src.llm.factory import LLMFactory

        return LLMFactory.create_client(provider_name=provider_name, api_key=api_key or conf.get("api_key"), base_url=conf.get("base_url"))

    def get_audio_source(self):
        """Returns the current audio source: 'system' or 'microphone'."""
        return self.config.get("audio_source", "system")

    def set_audio_source(self, source):
        """Sets the audio source: 'system' or 'microphone'."""
        old = self.get_audio_source()
        if old != source:
            self.config["audio_source"] = source
            logger.info(f"Audio source changed: {old} -> {source}")
            self.save_config()

    def get_knowledge_dir(self):
        """Returns the configured knowledge library directory."""
        return self.config.get("knowledge_dir", "")

    def set_knowledge_dir(self, directory_path):
        """Sets the knowledge library directory."""
        old = self.get_knowledge_dir()
        if old != directory_path:
            self.config["knowledge_dir"] = directory_path
            logger.info(f"Knowledge directory changed: {old} -> {directory_path}")
            self.save_config()

    def get_edition(self):
        """Returns the current application edition. Defaulting to PRO for local use."""
        from .constants import AppEdition

        return AppEdition.PRO
