from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, BrowserContext, Playwright

logger = logging.getLogger(__name__)


class BrowserController:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._playwright: Playwright | None = None
        self._contexts: list[BrowserContext] = []

    async def initialize(self) -> None:
        self._playwright = await async_playwright().start()
        logger.info("Playwright initialized")

    async def shutdown(self) -> None:
        for ctx in self._contexts:
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts.clear()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser controller shut down")

    async def launch(self, profile: dict[str, Any]) -> BrowserContext:
        if not self._playwright:
            await self.initialize()

        browser_type = self._config.get("browser_type", "chromium")
        headless = self._config.get("headless", True)

        browser_engine = getattr(self._playwright, browser_type)

        launch_args = []
        if self._config.get("disable_gpu"):
            launch_args.append("--disable-gpu")

        proxy_config = None
        if proxy := self._config.get("proxy"):
            proxy_config = {"server": proxy}

        browser = await browser_engine.launch(
            headless=headless,
            args=launch_args,
            proxy=proxy_config,
        )

        context_opts: dict[str, Any] = {
            "locale": profile.get("locale", "en-US"),
            "timezone_id": profile.get("timezone", "America/New_York"),
            "viewport": profile.get("screen", {"width": 1920, "height": 1080}),
            "user_agent": profile.get("user_agent", ""),
            "color_scheme": "light",
        }

        storage_dir = self._config.get("profile_storage_dir")
        if storage_dir:
            state_path = Path(storage_dir) / f"{profile.get('locale', 'default')}.json"
            if state_path.exists():
                context_opts["storage_state"] = str(state_path)

        extra_headers = profile.get("extra_http_headers")
        if extra_headers:
            context_opts["extra_http_headers"] = extra_headers

        context = await browser.new_context(**context_opts)

        if self._config.get("block_trackers", True):
            await context.route("**/*", self._block_tracking_requests)

        self._contexts.append(context)
        logger.info("Launched browser context: %s/%s", browser_type, profile.get("locale"))
        return context

    @staticmethod
    async def _block_tracking_requests(route) -> None:
        blocked_domains = [
            "google-analytics.com", "googletagmanager.com",
            "facebook.net", "doubleclick.net",
            "analytics.", "tracker.", "pixel.",
        ]
        url = route.request.url
        if any(domain in url for domain in blocked_domains):
            await route.abort()
        else:
            await route.continue_()

    async def save_state(self, context: BrowserContext, path: str | Path) -> None:
        state = await context.storage_state()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(str(state))
        logger.debug("Saved browser state to %s", path)