import logging

from .constants import DEFAULT_ACTIVE_PROVIDER, DEFAULT_PROVIDERS

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """Handles migration of configuration data from older versions to newer schemas."""

    @staticmethod
    def migrate(config: dict) -> bool:
        """
        Migrates old config structure to new provider-based structure.
        Returns True if changes were made.
        """
        changed = False

        if "providers" not in config:
            from copy import deepcopy

            config["providers"] = deepcopy(DEFAULT_PROVIDERS)
            config["active_provider"] = DEFAULT_ACTIVE_PROVIDER
            changed = True
        else:
            # Remove legacy providers
            if "openai_custom" in config["providers"]:
                logger.info("Removing legacy 'openai_custom' provider from config.")
                config["providers"].pop("openai_custom")
                changed = True

            # Ensure current providers exist
            from copy import deepcopy

            for p_name, p_defaults in DEFAULT_PROVIDERS.items():
                if p_name not in config["providers"]:
                    config["providers"][p_name] = deepcopy(p_defaults)
                    changed = True

            # Fix legacy cloud host if it was local
            cloud_conf = config["providers"].get("ollama_cloud", {})
            if cloud_conf.get("base_url") == "http://localhost:11434/v1":
                cloud_conf["base_url"] = "https://ollama.com"
                changed = True

        # Check active provider validity
        active = config.get("active_provider")
        if active == "openai_custom":
            config["active_provider"] = DEFAULT_ACTIVE_PROVIDER
            changed = True
        elif active == "ollama":
            config["active_provider"] = "ollama_local"
            changed = True

        return changed
