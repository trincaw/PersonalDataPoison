from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    name: str = "base_plugin"
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    async def on_event(self, event_name: str, payload: dict[str, Any]) -> None:
        pass

    def get_info(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }


class BrowserPlugin(Plugin):

    async def before_navigation(self, page: Any, url: str) -> str:
        return url

    async def after_navigation(self, page: Any, url: str) -> None:
        pass

    async def on_page_load(self, page: Any) -> None:
        pass


class IdentityPlugin(Plugin):

    async def on_identity_created(self, identity: Any) -> Any:
        return identity

    async def on_identity_rotated(self, old_id: Any, new_id: Any) -> None:
        pass


class TimingPlugin(Plugin):

    async def adjust_delay(self, base_delay: float) -> float:
        return base_delay