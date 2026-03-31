from src.core.event_bus import AppEventBus


def test_event_bus_singleton():
    """Verify that event_bus is a singleton."""
    from src.core.event_bus import event_bus as eb1
    from src.core.event_bus import event_bus as eb2

    assert eb1 is eb2
    assert isinstance(eb1, AppEventBus)


def test_event_bus_publish_subscribe():
    """Verify that events can be published and subscribed to."""
    bus = AppEventBus()
    received_data = []

    def handler(data):
        received_data.append(data)

    bus.add_handler("test_event", handler)
    bus.publish("test_event", "hello")

    assert "hello" in received_data
    assert len(received_data) == 1


def test_event_bus_decorator():
    """Verify the decorator subscription works."""
    bus = AppEventBus()
    received_data = []

    @bus.subscribe("decorated_event")
    def handler(data):
        received_data.append(data)

    bus.publish("decorated_event", "world")

    assert "world" in received_data
    assert len(received_data) == 1


def test_event_bus_multiple_args():
    """Verify multiple arguments are passed correctly."""
    bus = AppEventBus()
    results = []

    def handler(a, b, c=None):
        results.append((a, b, c))

    bus.add_handler("multi_arg", handler)
    bus.publish("multi_arg", 1, 2, c=3)

    assert results[0] == (1, 2, 3)
