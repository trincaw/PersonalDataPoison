from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)

_YOUTUBE_CATEGORIES = [
    "music", "gaming", "science", "technology", "cooking",
    "travel", "education", "sports", "art", "comedy",
    "news", "documentary", "diy", "fitness", "history",
]


class YouTubeStrategy(PlatformStrategy):
    """Targets YouTube/Google's video recommendation engine.

    Poisons: Watch history, recommendation graph, ad targeting,
    search suggestions, channel subscriptions signals.
    """

    name = "youtube"
    display_name = "YouTube"
    domains = ["youtube.com", "youtu.be", "m.youtube.com"]
    collection_vectors = [
        "watch_history", "search_history", "recommendation_graph",
        "ad_profile", "engagement_signals", "demographic_inference",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://www.youtube.com",
            "https://www.youtube.com/feed/trending",
            "https://www.youtube.com/feed/explore",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        templates = [
            "{interest} tutorial",
            "{interest} explained",
            "{interest} for beginners",
            "best {interest} 2024",
            "{interest} documentary",
            "{interest} how to",
            "{interest} review",
            "{interest} tips",
            "learn {interest} from scratch",
            "{interest} compilation",
            "{interest} vlog",
            "{interest} ASMR",
            "{interest} timelapse",
        ]
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            template = random.choice(templates)
            queries.append(template.format(interest=interest))
        return queries

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)

        entry = random.choice(self.get_entry_points())
        await page.goto(entry, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(entry)
        session.pages_visited += 1

        await behavior_engine.simulate_reading()

        actions = [
            PlatformAction("search_and_watch", weight=4.0),
            PlatformAction("browse_trending", weight=2.0),
            PlatformAction("watch_suggested", weight=3.0),
            PlatformAction("browse_category", weight=1.5),
        ]

        num_actions = random.randint(3, 8)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "search_and_watch":
                    await self._search_and_watch(page, identity, session, behavior_engine)
                elif action.name == "browse_trending":
                    await self._browse_trending(page, session, behavior_engine)
                elif action.name == "watch_suggested":
                    await self._watch_suggested(page, session, behavior_engine)
                elif action.name == "browse_category":
                    await self._browse_category(page, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(0.5, 2.0))

            except Exception:
                logger.debug("Action %s failed on YouTube, continuing", action.name)

        return session

    async def _search_and_watch(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]

        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        session.search_queries.append(query)
        session.urls_visited.append(search_url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)

        # Click on a video result
        videos = await page.query_selector_all("a#video-title, ytd-video-renderer a")
        if videos:
            video = random.choice(videos[:8])
            try:
                await video.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.urls_visited.append(page.url)
                session.data_points_poisoned += 2  # watch + recommendation

                # Simulate watching (partial)
                watch_time = random.uniform(15.0, 120.0)
                await asyncio.sleep(watch_time)
                session.duration_seconds += watch_time

                # Sometimes scroll to comments
                if random.random() < 0.3:
                    await behavior.simulate_scroll(page)

            except Exception:
                pass

    async def _browse_trending(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.youtube.com/feed/trending", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.youtube.com/feed/trending")
        session.pages_visited += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _watch_suggested(self, page, session: PlatformSession, behavior) -> None:
        # Click on a suggested/recommended video from current page
        suggestions = await page.query_selector_all(
            "ytd-compact-video-renderer a, ytd-rich-item-renderer a"
        )
        if suggestions:
            vid = random.choice(suggestions[:10])
            try:
                await vid.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.urls_visited.append(page.url)
                session.data_points_poisoned += 1

                watch_time = random.uniform(10.0, 60.0)
                await asyncio.sleep(watch_time)
                session.duration_seconds += watch_time
            except Exception:
                pass

    async def _browse_category(self, page, session: PlatformSession, behavior) -> None:
        category = random.choice(_YOUTUBE_CATEGORIES)
        url = f"https://www.youtube.com/results?search_query={quote_plus(category)}&sp=CAI%253D"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()
