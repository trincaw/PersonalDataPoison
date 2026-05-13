from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)


class FacebookStrategy(PlatformStrategy):
    """Targets Meta/Facebook's data collection.

    Poisons: Social graph inference, ad interest profile,
    content preferences, demographic signals, marketplace interests.
    """

    name = "facebook"
    display_name = "Facebook (Meta)"
    domains = ["facebook.com", "www.facebook.com", "m.facebook.com"]
    collection_vectors = [
        "ad_interest_profile", "content_preferences", "social_graph_inference",
        "marketplace_interests", "event_interests", "group_discovery",
        "cross_platform_meta_profile", "demographic_signals",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://www.facebook.com/",
            "https://www.facebook.com/marketplace/",
            "https://www.facebook.com/watch/",
            "https://www.facebook.com/events/explore/",
            "https://www.facebook.com/gaming/",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        templates = [
            "{interest} groups",
            "{interest} community",
            "{interest} events near me",
            "{interest} marketplace",
            "{interest} pages",
            "buy {interest} equipment",
            "{interest} classes",
            "{interest} local",
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
            PlatformAction("browse_feed", weight=4.0),
            PlatformAction("marketplace_browse", weight=2.5),
            PlatformAction("watch_videos", weight=2.0),
            PlatformAction("explore_events", weight=1.5),
            PlatformAction("search", weight=3.0),
        ]

        num_actions = random.randint(2, 6)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "browse_feed":
                    await self._browse_feed(page, session, behavior_engine)
                elif action.name == "marketplace_browse":
                    await self._marketplace(page, identity, session, behavior_engine)
                elif action.name == "watch_videos":
                    await self._watch_videos(page, session, behavior_engine)
                elif action.name == "explore_events":
                    await self._explore_events(page, identity, session, behavior_engine)
                elif action.name == "search":
                    await self._search(page, identity, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception:
                logger.debug("Action %s failed on Facebook, continuing", action.name)

        return session

    async def _browse_feed(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        for _ in range(random.randint(3, 8)):
            await behavior.simulate_scroll(page)
            await asyncio.sleep(random.uniform(2.0, 6.0))

    async def _marketplace(self, page, identity, session: PlatformSession, behavior) -> None:
        interests = self.get_poison_interests(identity)
        interest = random.choice(interests)
        url = f"https://www.facebook.com/marketplace/search/?query={quote_plus(interest)}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"marketplace: {interest}")
        session.pages_visited += 1
        session.data_points_poisoned += 2

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

        # Click on a listing
        listings = await page.query_selector_all("a[href*='/marketplace/item/']")
        if listings:
            listing = random.choice(listings[:8])
            try:
                await listing.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.data_points_poisoned += 1
                await behavior.simulate_reading()
            except Exception:
                pass

    async def _watch_videos(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.facebook.com/watch/", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.facebook.com/watch/")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        for _ in range(random.randint(1, 4)):
            await asyncio.sleep(random.uniform(10.0, 30.0))
            await behavior.simulate_scroll(page)

    async def _explore_events(self, page, identity, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.facebook.com/events/explore/", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.facebook.com/events/explore/")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _search(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]
        url = f"https://www.facebook.com/search/top/?q={quote_plus(query)}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(query)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
