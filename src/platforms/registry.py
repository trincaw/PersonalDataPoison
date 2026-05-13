from __future__ import annotations

import logging
import random
from typing import Any

from platforms.base import PlatformStrategy
from platforms.google import GoogleStrategy
from platforms.youtube import YouTubeStrategy
from platforms.instagram import InstagramStrategy
from platforms.facebook import FacebookStrategy
from platforms.tiktok import TikTokStrategy
from platforms.linkedin import LinkedInStrategy
from platforms.twitter import TwitterStrategy
from platforms.amazon import AmazonStrategy

logger = logging.getLogger(__name__)

_BUILTIN_STRATEGIES: dict[str, type[PlatformStrategy]] = {
    "google": GoogleStrategy,
    "youtube": YouTubeStrategy,
    "instagram": InstagramStrategy,
    "facebook": FacebookStrategy,
    "tiktok": TikTokStrategy,
    "linkedin": LinkedInStrategy,
    "twitter": TwitterStrategy,
    "amazon": AmazonStrategy,
}


class PlatformRegistry:
    """Central registry for all platform targeting strategies.

    Manages platform selection, weighting, and rotation to ensure
    realistic distribution across data collectors.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._strategies: dict[str, PlatformStrategy] = {}
        self._session_history: list[str] = []

    def register(self, strategy: PlatformStrategy) -> None:
        self._strategies[strategy.name] = strategy
        logger.info("Registered platform strategy: %s", strategy.display_name)

    def register_builtin(self, platform_names: list[str] | None = None) -> None:
        """Register built-in strategies. If no names given, register all enabled ones."""
        enabled = platform_names or list(self._config.get("enabled", _BUILTIN_STRATEGIES.keys()))
        platform_configs = self._config.get("platform_configs", {})

        for name in enabled:
            cls = _BUILTIN_STRATEGIES.get(name)
            if cls is None:
                logger.warning("Unknown platform: %s", name)
                continue
            pcfg = platform_configs.get(name, {})
            # Pass locale from parent config
            if "locale" not in pcfg and "locale" in self._config:
                pcfg["locale"] = self._config["locale"]
            self.register(cls(pcfg))

    def get(self, name: str) -> PlatformStrategy | None:
        return self._strategies.get(name)

    def select_platform(self, weights: dict[str, float] | None = None) -> PlatformStrategy:
        """Select a platform using configured weights.

        Applies anti-correlation: recently used platforms get reduced probability.
        """
        if not self._strategies:
            raise RuntimeError("No platform strategies registered")

        available = list(self._strategies.values())

        if weights is None:
            weights = self._config.get("weights", {})

        base_weights = []
        for s in available:
            w = weights.get(s.name, 1.0)

            # Anti-correlation: reduce weight for recently used platforms
            recent_count = sum(1 for h in self._session_history[-10:] if h == s.name)
            decay = max(0.1, 1.0 - (recent_count * 0.2))
            base_weights.append(w * decay)

        selected = random.choices(available, weights=base_weights, k=1)[0]
        self._session_history.append(selected.name)

        if len(self._session_history) > 100:
            self._session_history = self._session_history[-100:]

        logger.info("Selected platform: %s (decay-adjusted)", selected.display_name)
        return selected

    def select_multi(self, count: int = 3) -> list[PlatformStrategy]:
        """Select multiple different platforms for a multi-platform session."""
        available = list(self._strategies.values())
        random.shuffle(available)
        return available[:min(count, len(available))]

    @property
    def available_platforms(self) -> list[str]:
        return list(self._strategies.keys())

    @property
    def platform_count(self) -> int:
        return len(self._strategies)

    def get_stats(self) -> dict[str, int]:
        """Return usage counts per platform from session history."""
        stats: dict[str, int] = {}
        for name in self._session_history:
            stats[name] = stats.get(name, 0) + 1
        return stats
