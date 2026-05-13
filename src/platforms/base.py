from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PlatformAction:
    """Single atomic action on a platform (scroll, click, search, etc.)."""
    name: str
    weight: float = 1.0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformSession:
    """Describes the result of a platform interaction session."""
    platform_name: str
    actions_performed: list[str] = field(default_factory=list)
    pages_visited: int = 0
    data_points_poisoned: int = 0
    search_queries: list[str] = field(default_factory=list)
    urls_visited: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class PlatformStrategy(ABC):
    """Base class for all platform-specific behavior strategies.

    Each data-collecting company gets its own strategy that knows:
    - What URLs/pages to visit
    - What realistic user behavior looks like on that platform
    - What search queries / interactions to generate
    - How to poison the data that platform collects
    """

    name: str = "base"
    display_name: str = "Base Platform"
    domains: list[str] = []

    # Data collection vectors this platform uses
    collection_vectors: list[str] = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @abstractmethod
    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        """Run a complete realistic session on this platform."""
        ...

    @abstractmethod
    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        """Generate realistic search queries for this platform."""
        ...

    @abstractmethod
    def get_entry_points(self) -> list[str]:
        """Return realistic entry point URLs (bookmarks, direct nav, etc.)."""
        ...

    def get_poison_interests(self, identity: Any) -> list[str]:
        """Return interests/categories to inject into the platform's profiling."""
        base_interests = [
            "quantum computing", "beekeeping", "medieval history",
            "sourdough baking", "amateur radio", "origami",
            "birdwatching", "astrophotography", "fermentation",
            "woodworking", "calligraphy", "mycology",
            "model trains", "geocaching", "leather crafting",
            "urban sketching", "permaculture", "philately",
        ]
        if hasattr(identity, "preferences") and identity.preferences.preferred_categories:
            return identity.preferences.preferred_categories + random.sample(
                base_interests, k=min(3, len(base_interests))
            )
        return random.sample(base_interests, k=random.randint(3, 6))

    def select_weighted_actions(self, actions: list[PlatformAction], count: int) -> list[PlatformAction]:
        """Select actions based on their weights (more realistic distributions)."""
        if not actions:
            return []
        weights = [a.weight for a in actions]
        return random.choices(actions, weights=weights, k=min(count, len(actions)))
