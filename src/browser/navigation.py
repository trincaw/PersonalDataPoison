from __future__ import annotations

import logging
import random
from typing import Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class NavigationEngine:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._visited_urls: list[str] = []
        self._max_history = 500

    async def navigate(self, page, url: str, wait_until: str = "domcontentloaded") -> bool:
        try:
            response = await page.goto(url, wait_until=wait_until, timeout=30000)
            if response and response.ok:
                self._record_visit(url)
                logger.debug("Navigated to %s (status=%d)", url, response.status)
                return True
            logger.warning("Navigation to %s failed (status=%s)", url, response.status if response else "no response")
            return False
        except Exception:
            logger.exception("Navigation error for %s", url)
            return False

    async def follow_random_link(self, page, same_domain: bool = False) -> str | None:
        try:
            links = await page.query_selector_all("a[href]")
            if not links:
                return None

            hrefs = []
            current_domain = urlparse(page.url).netloc

            for link in links[:50]:
                href = await link.get_attribute("href")
                if not href or href.startswith(("#", "javascript:", "mailto:")):
                    continue

                full_url = urljoin(page.url, href)
                parsed = urlparse(full_url)

                if parsed.scheme not in ("http", "https"):
                    continue

                if same_domain and parsed.netloc != current_domain:
                    continue

                hrefs.append(full_url)

            if not hrefs:
                return None

            target = random.choice(hrefs)
            success = await self.navigate(page, target)
            return target if success else None

        except Exception:
            logger.exception("Error following random link")
            return None

    async def search(self, page, query: str, engine: str = "duckduckgo") -> bool:
        search_urls = {
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
            "google": f"https://www.google.com/search?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
            "startpage": f"https://www.startpage.com/do/dsearch?query={query}",
        }
        url = search_urls.get(engine, search_urls["duckduckgo"])
        return await self.navigate(page, url)

    async def go_back(self, page) -> None:
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=10000)
        except Exception:
            pass

    def _record_visit(self, url: str) -> None:
        self._visited_urls.append(url)
        if len(self._visited_urls) > self._max_history:
            self._visited_urls = self._visited_urls[-self._max_history:]

    @property
    def visit_history(self) -> list[str]:
        return list(self._visited_urls)

    @property
    def unique_domains(self) -> set[str]:
        return {urlparse(u).netloc for u in self._visited_urls}
