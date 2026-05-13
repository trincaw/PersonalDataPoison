from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)


class TwitterStrategy(PlatformStrategy):
    """Targets X/Twitter's data collection and ad targeting.

    Poisons: Interest graph, timeline algorithm, ad profile,
    topic preferences, trending engagement, demographic inference.
    """

    name = "twitter"
    display_name = "X (Twitter)"
    domains = ["x.com", "twitter.com"]
    collection_vectors = [
        "interest_graph", "timeline_algorithm", "ad_profile",
        "topic_preferences", "engagement_patterns", "demographic_inference",
        "conversation_tracking", "trend_participation",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://x.com/home",
            "https://x.com/explore",
            "https://x.com/search",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        templates = [
            "{interest}",
            "#{interest_tag}",
            "{interest} news",
            "{interest} thread",
            "best {interest} accounts to follow",
            "{interest} discussion",
            "{interest} hot take",
        ]
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            template = random.choice(templates)
            queries.append(template.format(
                interest=interest,
                interest_tag=interest.replace(" ", ""),
            ))
        return queries

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)

        entry = random.choice(self.get_entry_points())
        await page.goto(entry, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(entry)
        session.pages_visited += 1

        await behavior_engine.simulate_reading()

        actions = [
            PlatformAction("scroll_timeline", weight=4.0),
            PlatformAction("explore_trending", weight=3.0),
            PlatformAction("search_topic", weight=3.0),
            PlatformAction("browse_lists", weight=1.0),
        ]

        num_actions = random.randint(2, 5)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "scroll_timeline":
                    await self._scroll_timeline(page, session, behavior_engine)
                elif action.name == "explore_trending":
                    await self._explore_trending(page, session, behavior_engine)
                elif action.name == "search_topic":
                    await self._search_topic(page, identity, session, behavior_engine)
                elif action.name == "browse_lists":
                    await self._browse_lists(page, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(0.5, 2.0))

            except Exception:
                logger.debug("Action %s failed on Twitter/X, continuing", action.name)

        return session

    async def _scroll_timeline(self, page, session: PlatformSession, behavior) -> None:
        for _ in range(random.randint(5, 15)):
            await behavior.simulate_scroll(page)
            await asyncio.sleep(random.uniform(1.0, 4.0))
            session.data_points_poisoned += 1

            # Sometimes click on a tweet to expand
            if random.random() < 0.15:
                tweets = await page.query_selector_all("article a[href*='/status/']")
                if tweets:
                    tweet = random.choice(tweets[:5])
                    try:
                        await tweet.click()
                        await asyncio.sleep(random.uniform(3.0, 8.0))
                        session.pages_visited += 1
                        await page.go_back()
                    except Exception:
                        pass

        session.pages_visited += 1

    async def _explore_trending(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://x.com/explore/tabs/trending", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://x.com/explore/tabs/trending")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

        # Click on a trending topic
        trends = await page.query_selector_all("a[href*='/search?q=']")
        if trends:
            trend = random.choice(trends[:10])
            try:
                await trend.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.data_points_poisoned += 1
                await behavior.simulate_scroll(page)
            except Exception:
                pass

    async def _search_topic(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]
        url = f"https://x.com/search?q={quote_plus(query)}&src=typed_query"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(query)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _browse_lists(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://x.com/explore", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://x.com/explore")
        session.pages_visited += 1

        await behavior.simulate_scroll(page)
        await asyncio.sleep(random.uniform(2.0, 5.0))
