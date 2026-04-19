import logging
from collections.abc import Callable

from python_event_bus import EventBus

logger = logging.getLogger(__name__)

# Standard Event Types
EVENT_TRANSCRIPTION_PROGRESS = "transcription_progress"
EVENT_TRANSCRIPTION_SEGMENT = "transcription_segment"
EVENT_TRANSCRIPTION_FINISHED = "transcription_finished"
EVENT_TRANSCRIPTION_ERROR = "transcription_error"
EVENT_STATUS_UPDATE = "status_update"


class AppEventBus:
    """
    Wrapper for python-event-bus to provide a singleton and type-safe event handling.
    """

    def __init__(self):
        self.bus = EventBus()
        logger.info("AppEventBus: Initialized.")

    def publish(self, event_type: str, *args, **kwargs):
        """Publishes an event with optional payload."""
        logger.debug(f"AppEventBus: Publishing '{event_type}'")
        EventBus.call(event_type, *args, **kwargs)

    def subscribe(self, event_type: str):
        """Decorator for subscribing to an event."""
        return EventBus.on(event_type)

    @staticmethod
    def add_handler(event_name: str, handler: Callable):
        EventBus.subscribe(event_name, handler)

    def clear(self):
        """Clears all subscribers (useful for tests)."""
        logger.info("AppEventBus: Clearing all subscribers.")
        # python-event-bus doesn't have a clean clear(), so we reset the internal dict
        if hasattr(EventBus, "_handlers"):
            EventBus._handlers = {}
        # Also clear any instance-level state if we add it in future


# Singleton instance
event_bus = AppEventBus()
