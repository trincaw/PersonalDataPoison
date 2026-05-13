import pytest
import asyncio
from core.event_bus import EventBus


class TestEventBus:

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        await bus.emit("test.event", {"key": "value"})

        assert len(received) == 1
        assert received[0].name == "test.event"
        assert received[0].payload == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        count = {"a": 0, "b": 0}

        async def handler_a(event):
            count["a"] += 1

        async def handler_b(event):
            count["b"] += 1

        bus.subscribe("test", handler_a)
        bus.subscribe("test", handler_b)
        await bus.emit("test")

        assert count["a"] == 1
        assert count["b"] == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        called = []

        async def handler(event):
            called.append(True)

        bus.subscribe("test", handler)
        bus.unsubscribe("test", handler)
        await bus.emit("test")

        assert len(called) == 0

    @pytest.mark.asyncio
    async def test_history(self, bus):
        await bus.emit("a", {"x": 1})
        await bus.emit("b", {"y": 2})

        history = bus.get_history()
        assert len(history) == 2

        filtered = bus.get_history("a")
        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_error_handler_doesnt_crash(self, bus):
        async def bad_handler(event):
            raise ValueError("boom")

        async def good_handler(event):
            pass

        bus.subscribe("test", bad_handler)
        bus.subscribe("test", good_handler)

        # Should not raise
        await bus.emit("test")
