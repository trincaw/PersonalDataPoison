from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProxyEntry:
    url: str
    protocol: str = "http"
    country: str = ""
    last_used: datetime | None = None
    fail_count: int = 0
    latency_ms: float = 0.0
    active: bool = True

    @property
    def server_string(self) -> str:
        return self.url


class ProxyPool:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._proxies: list[ProxyEntry] = []
        self._max_fails = self._config.get("max_fails", 3)

        for proxy_url in self._config.get("proxies", []):
            if isinstance(proxy_url, str):
                self._proxies.append(ProxyEntry(url=proxy_url))
            elif isinstance(proxy_url, dict):
                self._proxies.append(ProxyEntry(**proxy_url))

    def add(self, url: str, **kwargs) -> None:
        self._proxies.append(ProxyEntry(url=url, **kwargs))

    def get(self, country: str | None = None) -> ProxyEntry | None:
        available = [p for p in self._proxies if p.active]
        if country:
            available = [p for p in available if p.country == country]
        if not available:
            return None

        proxy = min(available, key=lambda p: (p.fail_count, p.latency_ms))
        proxy.last_used = datetime.now(timezone.utc)
        return proxy

    def get_random(self) -> ProxyEntry | None:
        available = [p for p in self._proxies if p.active]
        if not available:
            return None
        proxy = random.choice(available)
        proxy.last_used = datetime.now(timezone.utc)
        return proxy

    def report_failure(self, proxy: ProxyEntry) -> None:
        proxy.fail_count += 1
        if proxy.fail_count >= self._max_fails:
            proxy.active = False
            logger.warning("Proxy %s disabled after %d failures", proxy.url, proxy.fail_count)

    def report_success(self, proxy: ProxyEntry, latency_ms: float = 0.0) -> None:
        proxy.fail_count = max(0, proxy.fail_count - 1)
        proxy.latency_ms = latency_ms

    def reset_all(self) -> None:
        for p in self._proxies:
            p.fail_count = 0
            p.active = True

    @property
    def active_count(self) -> int:
        return sum(1 for p in self._proxies if p.active)

    @property
    def total_count(self) -> int:
        return len(self._proxies)
