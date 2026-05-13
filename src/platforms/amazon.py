from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)


class AmazonStrategy(PlatformStrategy):
    """Targets Amazon's purchase intent and interest profiling.

    Poisons: Product interest graph, purchase intent signals,
    browsing history, recommendation engine, price tracking,
    category interests, review engagement.
    """

    name = "amazon"
    display_name = "Amazon"
    domains = ["amazon.com", "amazon.it", "amazon.co.uk", "amazon.de", "amazon.fr"]
    collection_vectors = [
        "product_interest_graph", "purchase_intent_signals", "browsing_history",
        "recommendation_engine", "category_interests", "price_sensitivity",
        "review_engagement", "ad_targeting",
    ]

    _PRODUCT_TEMPLATES = [
        "{interest} starter kit",
        "best {interest} equipment",
        "{interest} book",
        "{interest} tools",
        "professional {interest} set",
        "{interest} accessories",
        "{interest} guide",
        "{interest} for beginners",
        "top rated {interest}",
        "{interest} gift ideas",
    ]

    def get_entry_points(self) -> list[str]:
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com", "de": "de", "fr": "fr", "es": "es"}.get(locale, "com")
        return [
            f"https://www.amazon.{tld}",
            f"https://www.amazon.{tld}/gp/bestsellers/",
            f"https://www.amazon.{tld}/gp/new-releases/",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        interests = self.get_poison_interests(identity)
        queries = []
        for _ in range(count):
            interest = random.choice(interests)
            template = random.choice(self._PRODUCT_TEMPLATES)
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
            PlatformAction("search_products", weight=5.0),
            PlatformAction("browse_categories", weight=2.0),
            PlatformAction("view_product", weight=3.0),
            PlatformAction("browse_bestsellers", weight=2.0),
            PlatformAction("browse_deals", weight=1.5),
        ]

        num_actions = random.randint(3, 6)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "search_products":
                    await self._search_products(page, identity, session, behavior_engine)
                elif action.name == "browse_categories":
                    await self._browse_categories(page, session, behavior_engine)
                elif action.name == "view_product":
                    await self._view_product(page, session, behavior_engine)
                elif action.name == "browse_bestsellers":
                    await self._browse_bestsellers(page, session, behavior_engine)
                elif action.name == "browse_deals":
                    await self._browse_deals(page, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception:
                logger.debug("Action %s failed on Amazon, continuing", action.name)

        return session

    async def _search_products(self, page, identity, session: PlatformSession, behavior) -> None:
        queries = self.generate_search_queries(identity, count=1)
        query = queries[0]
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com", "de": "de", "fr": "fr"}.get(locale, "com")
        url = f"https://www.amazon.{tld}/s?k={quote_plus(query)}"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(query)
        session.pages_visited += 1
        session.data_points_poisoned += 2  # search + interest

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _browse_categories(self, page, session: PlatformSession, behavior) -> None:
        # Click on a category/department link
        cat_links = await page.query_selector_all("a[href*='/b/'], a[href*='/dp/']")
        if cat_links:
            link = random.choice(cat_links[:10])
            try:
                await link.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.urls_visited.append(page.url)
                session.data_points_poisoned += 1
                await behavior.simulate_scroll(page)
            except Exception:
                pass

    async def _view_product(self, page, session: PlatformSession, behavior) -> None:
        products = await page.query_selector_all("a[href*='/dp/']")
        if products:
            product = random.choice(products[:15])
            try:
                await product.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.urls_visited.append(page.url)
                session.data_points_poisoned += 2  # product view + interest

                await behavior.simulate_reading()
                await behavior.simulate_scroll(page)

                # Scroll to reviews section sometimes
                if random.random() < 0.3:
                    for _ in range(random.randint(3, 6)):
                        await behavior.simulate_scroll(page)
                        await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception:
                pass

    async def _browse_bestsellers(self, page, session: PlatformSession, behavior) -> None:
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com"}.get(locale, "com")
        url = f"https://www.amazon.{tld}/gp/bestsellers/"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

    async def _browse_deals(self, page, session: PlatformSession, behavior) -> None:
        locale = self._config.get("locale", "it")
        tld = {"it": "it", "en": "com"}.get(locale, "com")
        url = f"https://www.amazon.{tld}/deals"

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
