from __future__ import annotations

import logging
import ssl
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class TransportLayer:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._session: aiohttp.ClientSession | None = None

    async def initialize(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self._config.get("timeout", 30))
        connector = aiohttp.TCPConnector(
            limit=self._config.get("max_connections", 10),
            ssl=self._build_ssl_context(),
        )
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._config.get("default_headers", {}),
        )
        logger.info("Transport layer initialized")

    async def shutdown(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Transport layer shut down")

    async def get(self, url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
        if not self._session:
            await self.initialize()
        async with self._session.get(url, headers=headers) as resp:
            body = await resp.text()
            return resp.status, body

    async def post(self, url: str, data: Any = None, headers: dict[str, str] | None = None) -> tuple[int, str]:
        if not self._session:
            await self.initialize()
        async with self._session.post(url, json=data, headers=headers) as resp:
            body = await resp.text()
            return resp.status, body

    async def head(self, url: str) -> int:
        if not self._session:
            await self.initialize()
        async with self._session.head(url) as resp:
            return resp.status

    def _build_ssl_context(self) -> ssl.SSLContext | bool:
        if not self._config.get("verify_ssl", True):
            return False
        ctx = ssl.create_default_context()
        return ctx
