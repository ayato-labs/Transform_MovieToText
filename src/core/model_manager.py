import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class VRAMClient(Protocol):
    """Protocol for clients that use VRAM and can be unloaded."""

    def unload(self) -> None:
        """Release VRAM/RAM resources."""
        ...


class ModelManager:
    """
    Singleton manager to orchestrate VRAM usage between competing AI models (Whisper and LLM).
    Ensures that only one heavy model occupies VRAM at a time in constrained environments.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clients = {}
            cls._instance._active_client = None
        return cls._instance

    def register(self, name: str, client: VRAMClient):
        """Registers a client with the manager."""
        self._clients[name] = client
        logger.debug(f"ModelManager: Registered client '{name}'")

    def request_vram(self, requester_name: str):
        """
        Requests exclusive VRAM access for the named client.
        Unloads all other registered clients to free up resources.
        """
        logger.info(f"ModelManager: '{requester_name}' is requesting VRAM access.")

        if self._active_client == requester_name:
            logger.debug(f"ModelManager: '{requester_name}' already has VRAM access.")
            return

        # Unload others
        for name, client in self._clients.items():
            if name != requester_name:
                try:
                    logger.info(f"ModelManager: Unloading '{name}' to make room for '{requester_name}'...")
                    client.unload()
                except Exception:
                    logger.exception(f"ModelManager: Failed to unload '{name}'")

        self._active_client = requester_name
        logger.info(f"ModelManager: VRAM access granted to '{requester_name}'.")

    def release_all(self):
        """Unlocks everything. Useful for app shutdown or low-power modes."""
        for name, client in self._clients.items():
            try:
                client.unload()
            except Exception:
                logger.exception(f"ModelManager: Failed to unload '{name}' during release_all")
        self._active_client = None


# Global singleton instance
model_manager = ModelManager()
