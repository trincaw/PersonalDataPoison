from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from plugins.base import Plugin

logger = logging.getLogger(__name__)


class PluginLoader:

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def load(self, plugin_path: str) -> Plugin:
        module_name, class_name = plugin_path.rsplit(":", 1)
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name)

        if not issubclass(plugin_class, Plugin):
            raise TypeError(f"{plugin_path} is not a Plugin subclass")

        instance = plugin_class()
        self._plugins[plugin_path] = instance
        logger.info("Loaded plugin: %s", plugin_path)
        return instance

    def load_all(self, plugin_paths: list[str]) -> list[Plugin]:
        plugins = []
        for path in plugin_paths:
            try:
                plugins.append(self.load(path))
            except Exception:
                logger.exception("Failed to load plugin: %s", path)
        return plugins

    def get(self, plugin_path: str) -> Plugin | None:
        return self._plugins.get(plugin_path)

    @property
    def loaded(self) -> dict[str, Plugin]:
        return dict(self._plugins)

    async def initialize_all(self) -> None:
        for name, plugin in self._plugins.items():
            try:
                await plugin.initialize()
                logger.info("Initialized plugin: %s", name)
            except Exception:
                logger.exception("Failed to initialize plugin: %s", name)

    async def shutdown_all(self) -> None:
        for name, plugin in reversed(list(self._plugins.items())):
            try:
                await plugin.shutdown()
                logger.info("Shut down plugin: %s", name)
            except Exception:
                logger.exception("Failed to shut down plugin: %s", name)