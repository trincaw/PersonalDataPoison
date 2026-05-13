from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "system"


class EventBus:

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 1000

    def subscribe(self, event_name: str, callback: EventHandler) -> None:
        self._subscribers[event_name].append(callback)
        logger.debug("Subscribed %s to event '%s'", callback.__qualname__, event_name)

    def unsubscribe(self, event_name: str, callback: EventHandler) -> None:
        self._subscribers[event_name] = [
            cb for cb in self._subscribers[event_name] if cb is not callback
        ]

    async def emit(self, event_name: str, payload: dict[str, Any] | None = None, source: str = "system") -> None:
        event = Event(name=event_name, payload=payload or {}, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug("Emitting event '%s' from '%s'", event_name, source)

        tasks = []
        for callback in self._subscribers.get(event_name, []):
            tasks.append(self._safe_call(callback, event))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_call(self, callback: EventHandler, event: Event) -> None:
        try:
            await callback(event)
        except Exception:
            logger.exception("Error in handler %s for event '%s'", callback.__qualname__, event.name)

    def get_history(self, event_name: str | None = None, limit: int = 50) -> list[Event]:
        events = self._history
        if event_name:
            events = [e for e in events if e.name == event_name]
        return events[-limit:]