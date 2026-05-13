from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)

_SEARCH_TEMPLATES = [
    "{interest} tutorial",
    "{interest} beginner guide",
    "best {interest} tools",
    "{interest} near me",
    "how to start {interest}",
    "{interest} courses online",
    "{interest} vs {alt_interest}",
    "{interest} reddit",
    "{interest} community",
    "buy {interest} equipment",
    "{interest} tips and tricks",
    "top 10 {interest}",
    "{interest} for beginners 2024",
    "{interest} research papers",
    "{interest} news today",
    "{interest} events {city}",
    "best {interest} books",
    "{interest} YouTube channels",
    "{interest} certification",
    "is {interest} worth it",
]

_CITIES = [
    "Milano", "Roma", "New York", "London", "Berlin",
    "Paris", "Tokyo", "Barcelona", "Amsterdam", "Lisbon",
]


class GoogleStrategy(PlatformStrategy):
    """Targets Google's data collection ecosystem.

    Poisons: Search history, ad profiling, location interests,
    Maps queries, News preferences, Shopping interests, YouTube suggestions.
    """

    name = "google"
    display_name = "Google Search & Services"
    domains = [
        "google.com", "google.it", "google.co.uk",
        "maps.google.com", "news.google.com", "shopping.google.com",
    ]
    collection_vectors = [
        "search_history", "ad_profile", "location_history",
        "news_preferences", "shopping_interests", "youtube_watch_history",
    ]

    def get_entry_points(self) -> list[str]:
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com", "de": "de", "fr": "fr", "es": "es"}.get(locale, "com")
        return [
            f"https://www.google.{tld}",
            f"https://news.google.{tld}",
            f"https://maps.google.{tld}",
            f"https://www.google.{tld}/shopping",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            alt = random.choice([i for i in interests if i != interest] or interests)
            city = random.choice(_CITIES)
            template = random.choice(_SEARCH_TEMPLATES)
            query = template.format(interest=interest, alt_interest=alt, city=city)
            queries.append(query)
        return queries

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)
        queries = self.generate_search_queries(identity, count=random.randint(3, 8))

        actions = [
            PlatformAction("search", weight=5.0),
            PlatformAction("news", weight=2.0),
            PlatformAction("maps", weight=1.5),
            PlatformAction("shopping", weight=1.0),
            PlatformAction("images", weight=1.5),
        ]

        selected = self.select_weighted_actions(actions, random.randint(3, 7))

        for action in selected:
            try:
                if action.name == "search":
                    await self._do_search(page, queries, session, behavior_engine)
                elif action.name == "news":
                    await self._browse_news(page, session, behavior_engine)
                elif action.name == "maps":
                    await self._browse_maps(page, identity, session, behavior_engine)
                elif action.name == "shopping":
                    await self._browse_shopping(page, identity, session, behavior_engine)
                elif action.name == "images":
                    await self._search_images(page, queries, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(1.0, 4.0))

            except Exception:
                logger.debug("Action %s failed on Google, continuing", action.name)

        return session

    async def _do_search(self, page, queries: list[str], session: PlatformSession, behavior) -> None:
        query = random.choice(queries)
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com", "de": "de", "fr": "fr"}.get(locale, "com")
        url = f"https://www.google.{tld}/search?q={quote_plus(query)}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(query)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_human_interaction(page)

        # Sometimes click a result
        if random.random() < 0.5:
            results = await page.query_selector_all("h3")
            if results:
                target = random.choice(results[:5])
                try:
                    await target.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    session.pages_visited += 1
                    session.urls_visited.append(page.url)
                    await behavior.simulate_reading()
                    await behavior.simulate_scroll(page)
                except Exception:
                    pass

    async def _browse_news(self, page, session: PlatformSession, behavior) -> None:
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com"}.get(locale, "com")
        url = f"https://news.google.{tld}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

        # Click on a news article
        articles = await page.query_selector_all("article a, a[href*='article']")
        if articles:
            article = random.choice(articles[:10])
            try:
                await article.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                await behavior.simulate_reading()
            except Exception:
                pass

    async def _browse_maps(self, page, identity, session: PlatformSession, behavior) -> None:
        interests = self.get_poison_interests(identity)
        interest = random.choice(interests)
        city = random.choice(_CITIES)
        query = f"{interest} in {city}"

        url = f"https://www.google.com/maps/search/{quote_plus(query)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"maps: {query}")
        session.pages_visited += 1
        session.data_points_poisoned += 2  # location + interest

        await asyncio.sleep(random.uniform(3.0, 8.0))
        await behavior.simulate_scroll(page)

    async def _browse_shopping(self, page, identity, session: PlatformSession, behavior) -> None:
        interests = self.get_poison_interests(identity)
        interest = random.choice(interests)
        query = f"{interest} equipment"

        url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=shop"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"shopping: {query}")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _search_images(self, page, queries: list[str], session: PlatformSession, behavior) -> None:
        query = random.choice(queries)
        url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await asyncio.sleep(random.uniform(2.0, 5.0))
