from __future__ import annotations

import asyncio
import logging
import signal
from enum import Enum, auto
from typing import Any

from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class AppState(Enum):
    CREATED = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class LifecycleManager:

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._state = AppState.CREATED
        self._components: list[Any] = []
        self._shutdown_event = asyncio.Event()

    @property
    def state(self) -> AppState:
        return self._state

    def register_component(self, component: Any) -> None:
        self._components.append(component)
        logger.debug("Registered component: %s", type(component).__name__)

    async def initialize(self) -> None:
        self._state = AppState.INITIALIZING
        await self._event_bus.emit("lifecycle.initializing")

        for component in self._components:
            if hasattr(component, "initialize"):
                logger.info("Initializing %s", type(component).__name__)
                await component.initialize()

        self._state = AppState.RUNNING
        await self._event_bus.emit("lifecycle.started")
        logger.info("All components initialized — state: RUNNING")

    async def shutdown(self) -> None:
        if self._state in (AppState.STOPPING, AppState.STOPPED):
            return

        self._state = AppState.STOPPING
        await self._event_bus.emit("lifecycle.stopping")
        logger.info("Shutting down components...")

        for component in reversed(self._components):
            if hasattr(component, "shutdown"):
                try:
                    await component.shutdown()
                    logger.info("Shut down %s", type(component).__name__)
                except Exception:
                    logger.exception("Error shutting down %s", type(component).__name__)

        self._state = AppState.STOPPED
        await self._event_bus.emit("lifecycle.stopped")
        self._shutdown_event.set()
        logger.info("All components stopped")

    async def pause(self) -> None:
        if self._state != AppState.RUNNING:
            return
        self._state = AppState.PAUSING
        for component in self._components:
            if hasattr(component, "pause"):
                await component.pause()
        self._state = AppState.PAUSED
        await self._event_bus.emit("lifecycle.paused")

    async def resume(self) -> None:
        if self._state != AppState.PAUSED:
            return
        for component in self._components:
            if hasattr(component, "resume"):
                await component.resume()
        self._state = AppState.RUNNING
        await self._event_bus.emit("lifecycle.resumed")

    def install_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

    async def wait_for_shutdown(self) -> None:
        await self._shutdown_event.wait()
