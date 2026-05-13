from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)

_HASHTAG_POOLS = {
    "travel": ["travel", "wanderlust", "explore", "adventure", "travelgram", "instatravel"],
    "food": ["foodie", "foodporn", "instafood", "cooking", "recipe", "homemade"],
    "fitness": ["fitness", "workout", "gym", "fitlife", "training", "health"],
    "art": ["art", "artist", "painting", "drawing", "creative", "artwork"],
    "nature": ["nature", "naturephotography", "landscape", "outdoor", "hiking", "wildlife"],
    "tech": ["technology", "coding", "programming", "developer", "tech", "innovation"],
    "photography": ["photography", "photo", "photooftheday", "streetphotography", "portrait"],
    "music": ["music", "musician", "guitar", "piano", "livemusic", "songwriter"],
}


class InstagramStrategy(PlatformStrategy):
    """Targets Meta/Instagram's data collection.

    Poisons: Interest graph, ad targeting, explore page recommendations,
    hashtag associations, engagement patterns, demographic profiling.
    """

    name = "instagram"
    display_name = "Instagram (Meta)"
    domains = ["instagram.com", "www.instagram.com"]
    collection_vectors = [
        "interest_graph", "explore_recommendations", "ad_profile",
        "hashtag_associations", "engagement_patterns", "content_preferences",
        "demographic_inference", "cross_platform_meta_profile",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://www.instagram.com/",
            "https://www.instagram.com/explore/",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            variant = random.choice([
                interest,
                f"#{interest.replace(' ', '')}",
                f"{interest} inspiration",
                f"best {interest} accounts",
            ])
            queries.append(variant)
        return queries

    def _get_hashtags(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        tags = []
        for interest in interests:
            key = interest.lower()
            for pool_key, pool_tags in _HASHTAG_POOLS.items():
                if pool_key in key or key in pool_key:
                    tags.extend(pool_tags)
                    break
            else:
                tags.append(interest.replace(" ", "").lower())
        random.shuffle(tags)
        return tags[:count]

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)

        entry = random.choice(self.get_entry_points())
        await page.goto(entry, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(entry)
        session.pages_visited += 1

        await asyncio.sleep(random.uniform(2.0, 5.0))

        actions = [
            PlatformAction("explore_feed", weight=4.0),
            PlatformAction("search_hashtag", weight=3.0),
            PlatformAction("browse_profile", weight=2.0),
            PlatformAction("explore_reels", weight=2.5),
            PlatformAction("search_topic", weight=2.0),
        ]

        num_actions = random.randint(3, 7)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "explore_feed":
                    await self._explore_feed(page, session, behavior_engine)
                elif action.name == "search_hashtag":
                    await self._search_hashtag(page, identity, session, behavior_engine)
                elif action.name == "browse_profile":
                    await self._browse_profile(page, session, behavior_engine)
                elif action.name == "explore_reels":
                    await self._explore_reels(page, session, behavior_engine)
                elif action.name == "search_topic":
                    await self._search_topic(page, identity, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception:
                logger.debug("Action %s failed on Instagram, continuing", action.name)

        return session

    async def _explore_feed(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.instagram.com/explore/", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.instagram.com/explore/")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        # Scroll through explore grid
        for _ in range(random.randint(2, 6)):
            await behavior.simulate_scroll(page)
            await asyncio.sleep(random.uniform(1.0, 3.0))

        # Sometimes click a post
        if random.random() < 0.4:
            posts = await page.query_selector_all("article a, a[href*='/p/']")
            if posts:
                post = random.choice(posts[:12])
                try:
                    await post.click()
                    await asyncio.sleep(random.uniform(3.0, 8.0))
                    session.pages_visited += 1
                    session.data_points_poisoned += 1
                except Exception:
                    pass

    async def _search_hashtag(self, page, identity, session: PlatformSession, behavior) -> None:
        hashtags = self._get_hashtags(identity, count=1)
        if not hashtags:
            return
        tag = hashtags[0]
        url = f"https://www.instagram.com/explore/tags/{tag}/"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"#{tag}")
        session.pages_visited += 1
        session.data_points_poisoned += 2  # hashtag interest + browsing

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _browse_profile(self, page, session: PlatformSession, behavior) -> None:
        # Look for profile links on current page
        profile_links = await page.query_selector_all("a[href*='instagram.com/'][href$='/']")
        if profile_links:
            link = random.choice(profile_links[:10])
            try:
                await link.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.urls_visited.append(page.url)
                session.data_points_poisoned += 1

                await behavior.simulate_scroll(page)
                await asyncio.sleep(random.uniform(2.0, 5.0))
            except Exception:
                pass

    async def _explore_reels(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.instagram.com/reels/")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        # Simulate watching a few reels
        for _ in range(random.randint(2, 5)):
            await asyncio.sleep(random.uniform(5.0, 20.0))
            await behavior.simulate_scroll(page)

    async def _search_topic(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]

        # Use Instagram search
        search_input = await page.query_selector("input[placeholder*='Search'], input[aria-label*='Search']")
        if search_input:
            await search_input.click()
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await search_input.fill(query)
            session.search_queries.append(query)
            session.data_points_poisoned += 1
            await asyncio.sleep(random.uniform(1.5, 3.0))

            # Press Enter or click first result
            await page.keyboard.press("Enter")
            await asyncio.sleep(random.uniform(2.0, 4.0))
            session.pages_visited += 1
