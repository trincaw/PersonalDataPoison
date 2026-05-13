from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class DNSConfig:

    DOH_SERVERS = [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "https://dns.quad9.net/dns-query",
        "https://doh.opendns.com/dns-query",
    ]

    STANDARD_SERVERS = [
        "1.1.1.1",
        "8.8.8.8",
        "9.9.9.9",
        "208.67.222.222",
    ]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._use_doh = self._config.get("use_doh", True)
        self._rotate = self._config.get("rotate", True)

    def get_server(self) -> str:
        servers = self.DOH_SERVERS if self._use_doh else self.STANDARD_SERVERS
        if self._rotate:
            return random.choice(servers)
        return servers[0]

    def get_browser_args(self) -> list[str]:
        if not self._use_doh:
            return []
        server = self.get_server()
        return [f"--enable-features=DnsOverHttps", f"--dns-over-https-mode=secure", f"--dns-over-https-template={server}"]
