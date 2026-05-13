from __future__ import annotations

import logging
import random
from typing import Any
from uuid import uuid4

from faker import Faker

from identity.models import (
    BrowsingPreferences,
    DeviceProfile,
    Identity,
)

logger = logging.getLogger(__name__)

_OS_CONFIGS = [
    {
        "os_name": "Windows",
        "os_version": "10",
        "platform": "Win32",
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER)",
    },
    {
        "os_name": "Windows",
        "os_version": "11",
        "platform": "Win32",
        "webgl_vendor": "Google Inc. (AMD)",
        "webgl_renderer": "ANGLE (AMD, AMD Radeon RX 580)",
    },
    {
        "os_name": "macOS",
        "os_version": "14.2",
        "platform": "MacIntel",
        "webgl_vendor": "Apple",
        "webgl_renderer": "Apple M2",
    },
    {
        "os_name": "Linux",
        "os_version": "6.5",
        "platform": "Linux x86_64",
        "webgl_vendor": "Mesa",
        "webgl_renderer": "Mesa Intel(R) UHD Graphics 630",
    },
]

_SCREEN_RESOLUTIONS = [
    (1920, 1080), (2560, 1440), (1366, 768), (1536, 864),
    (1440, 900), (1680, 1050), (3840, 2160), (1280, 720),
]

_LOCALE_TIMEZONE_MAP = {
    "it-IT": ["Europe/Rome"],
    "en-US": ["America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver"],
    "en-GB": ["Europe/London"],
    "de-DE": ["Europe/Berlin"],
    "fr-FR": ["Europe/Paris"],
    "es-ES": ["Europe/Madrid"],
    "pt-BR": ["America/Sao_Paulo"],
    "ja-JP": ["Asia/Tokyo"],
    "zh-CN": ["Asia/Shanghai"],
}

_BROWSER_VERSIONS = {
    "Chromium": ["120.0.6099.130", "121.0.6167.85", "122.0.6261.57", "123.0.6312.58"],
    "Firefox": ["121.0", "122.0", "123.0", "124.0"],
}

_CATEGORIES = ["news", "tech", "science", "sports", "cooking", "travel", "finance", "gaming", "music", "art"]


class IdentityGenerator:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._faker = Faker(self._config.get("default_locale", "en_US"))

    def create(self, locale: str | None = None, os_name: str | None = None) -> Identity:
        locale = locale or random.choice(list(_LOCALE_TIMEZONE_MAP.keys()))
        tz = random.choice(_LOCALE_TIMEZONE_MAP[locale])

        os_cfg = None
        if os_name:
            os_cfg = next((c for c in _OS_CONFIGS if c["os_name"] == os_name), None)
        if os_cfg is None:
            os_cfg = random.choice(_OS_CONFIGS)

        screen = random.choice(_SCREEN_RESOLUTIONS)
        browser_name = random.choice(["Chromium", "Firefox"])
        browser_version = random.choice(_BROWSER_VERSIONS[browser_name])

        ua = self._build_user_agent(os_cfg, browser_name, browser_version)

        device = DeviceProfile(
            os_name=os_cfg["os_name"],
            os_version=os_cfg["os_version"],
            browser_name=browser_name,
            browser_version=browser_version,
            screen_width=screen[0],
            screen_height=screen[1],
            color_depth=random.choice([24, 32]),
            timezone=tz,
            locale=locale,
            user_agent=ua,
            platform=os_cfg["platform"],
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            webgl_vendor=os_cfg["webgl_vendor"],
            webgl_renderer=os_cfg["webgl_renderer"],
        )

        prefs = BrowsingPreferences(
            preferred_categories=random.sample(_CATEGORIES, k=random.randint(2, 5)),
            search_engines=random.sample(["google", "duckduckgo", "bing", "startpage"], k=random.randint(1, 2)),
            language_codes=[locale.split("-")[0]],
            typing_speed_wpm=random.gauss(65, 15),
            scroll_speed=random.choice(["slow", "medium", "fast"]),
            platform_interests=self._generate_platform_interests(),
        )

        alias = f"id-{uuid4().hex[:8]}"
        persona_name = self._faker.name()

        identity = Identity(
            alias=alias,
            persona_name=persona_name,
            device=device,
            preferences=prefs,
        )

        logger.info("Generated identity %s (%s) — %s/%s @ %s", alias, persona_name, os_cfg["os_name"], browser_name, locale)
        return identity

    def create_batch(self, count: int, **kwargs) -> list[Identity]:
        return [self.create(**kwargs) for _ in range(count)]

    @staticmethod
    def _generate_platform_interests() -> dict[str, list[str]]:
        """Generate distinct interest sets per platform to complicate cross-platform correlation."""
        all_interests = [
            "quantum computing", "beekeeping", "medieval history", "sourdough baking",
            "amateur radio", "origami", "birdwatching", "astrophotography",
            "fermentation", "woodworking", "calligraphy", "mycology",
            "model trains", "geocaching", "leather crafting", "urban sketching",
            "permaculture", "philately", "competitive chess", "drone photography",
            "rock climbing", "pottery", "aquascaping", "vintage watches",
            "mechanical keyboards", "home automation", "foraging", "kintsugi",
            "speed cubing", "letterpress printing", "blacksmithing", "herbalism",
        ]
        random.shuffle(all_interests)

        platforms = ["google", "youtube", "instagram", "facebook", "tiktok", "linkedin", "twitter", "amazon"]
        result: dict[str, list[str]] = {}

        for platform in platforms:
            # Each platform gets a partially overlapping but distinct set
            num = random.randint(3, 6)
            chosen = random.sample(all_interests, k=min(num, len(all_interests)))
            result[platform] = chosen

        return result

    @staticmethod
    def _build_user_agent(os_cfg: dict, browser: str, version: str) -> str:
        os_name = os_cfg["os_name"]
        if os_name == "Windows":
            os_part = "Windows NT 10.0; Win64; x64"
        elif os_name == "macOS":
            os_part = f"Macintosh; Intel Mac OS X {os_cfg['os_version'].replace('.', '_')}"
        else:
            os_part = "X11; Linux x86_64"

        if browser == "Chromium":
            return f"Mozilla/5.0 ({os_part}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        else:
            return f"Mozilla/5.0 ({os_part}; rv:{version}) Gecko/20100101 Firefox/{version}"