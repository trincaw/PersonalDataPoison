from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)

_TIKTOK_CATEGORIES = [
    "comedy", "dance", "food", "beauty", "sports", "pets",
    "diy", "life hacks", "education", "science", "travel",
    "fitness", "gaming", "music", "art", "fashion",
]


class TikTokStrategy(PlatformStrategy):
    """Targets TikTok/ByteDance's recommendation engine.

    Poisons: FYP algorithm, interest classification, watch time signals,
    engagement patterns, content preference model, demographic inference.
    """

    name = "tiktok"
    display_name = "TikTok (ByteDance)"
    domains = ["tiktok.com", "www.tiktok.com"]
    collection_vectors = [
        "fyp_algorithm", "interest_classification", "watch_time_signals",
        "engagement_patterns", "content_preferences", "demographic_inference",
        "device_fingerprint", "behavioral_biometrics",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://www.tiktok.com/",
            "https://www.tiktok.com/explore",
            "https://www.tiktok.com/foryou",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        templates = [
            "{interest}",
            "{interest} tutorial",
            "#{interest_tag}",
            "{interest} hack",
            "{interest} trend",
            "{interest} compilation",
            "satisfying {interest}",
            "how to {interest}",
        ]
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            template = random.choice(templates)
            query = template.format(
                interest=interest,
                interest_tag=interest.replace(" ", ""),
            )
            queries.append(query)
        return queries

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)

        entry = random.choice(self.get_entry_points())
        await page.goto(entry, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(entry)
        session.pages_visited += 1

        await asyncio.sleep(random.uniform(2.0, 4.0))

        actions = [
            PlatformAction("scroll_fyp", weight=5.0),
            PlatformAction("search_topic", weight=3.0),
            PlatformAction("explore_discover", weight=2.0),
            PlatformAction("browse_hashtag", weight=2.5),
        ]

        num_actions = random.randint(2, 5)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "scroll_fyp":
                    await self._scroll_fyp(page, session, behavior_engine)
                elif action.name == "search_topic":
                    await self._search_topic(page, identity, session, behavior_engine)
                elif action.name == "explore_discover":
                    await self._explore_discover(page, session, behavior_engine)
                elif action.name == "browse_hashtag":
                    await self._browse_hashtag(page, identity, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(0.5, 2.0))

            except Exception:
                logger.debug("Action %s failed on TikTok, continuing", action.name)

        return session

    async def _scroll_fyp(self, page, session: PlatformSession, behavior) -> None:
        num_videos = random.randint(5, 15)
        for i in range(num_videos):
            # Each TikTok video: watch for variable time
            watch_time = random.uniform(3.0, 30.0)
            await asyncio.sleep(watch_time)
            session.duration_seconds += watch_time
            session.data_points_poisoned += 1

            # Scroll to next video
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(random.uniform(0.3, 1.0))

        session.pages_visited += num_videos
        logger.debug("Scrolled through %d TikTok videos", num_videos)

    async def _search_topic(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]

        url = f"https://www.tiktok.com/search?q={quote_plus(query)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(query)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await asyncio.sleep(random.uniform(2.0, 5.0))

        # Click on a result
        videos = await page.query_selector_all("a[href*='/video/'], div[data-e2e='search_top-item']")
        if videos:
            vid = random.choice(videos[:8])
            try:
                await vid.click()
                await asyncio.sleep(random.uniform(5.0, 20.0))
                session.pages_visited += 1
                session.data_points_poisoned += 1
            except Exception:
                pass

    async def _explore_discover(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.tiktok.com/explore", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.tiktok.com/explore")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        for _ in range(random.randint(2, 5)):
            await behavior.simulate_scroll(page)
            await asyncio.sleep(random.uniform(2.0, 5.0))

    async def _browse_hashtag(self, page, identity, session: PlatformSession, behavior) -> None:
        interests = self.get_poison_interests(identity)
        tag = random.choice(interests).replace(" ", "")
        url = f"https://www.tiktok.com/tag/{tag}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"#{tag}")
        session.pages_visited += 1
        session.data_points_poisoned += 2

        await behavior.simulate_scroll(page)
        await asyncio.sleep(random.uniform(3.0, 6.0))
