from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from urllib.parse import quote_plus

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy

logger = logging.getLogger(__name__)


class LinkedInStrategy(PlatformStrategy):
    """Targets LinkedIn/Microsoft's professional data collection.

    Poisons: Professional interest graph, job preferences, industry signals,
    skill associations, company interest tracking, recruiter search index.
    """

    name = "linkedin"
    display_name = "LinkedIn (Microsoft)"
    domains = ["linkedin.com", "www.linkedin.com"]
    collection_vectors = [
        "professional_interest_graph", "job_search_history", "industry_signals",
        "skill_associations", "company_interest_tracking", "content_engagement",
        "demographic_professional_profile", "ad_targeting_b2b",
    ]

    _JOB_TITLES = [
        "data scientist", "software engineer", "product manager",
        "ux designer", "devops engineer", "machine learning engineer",
        "cybersecurity analyst", "cloud architect", "technical writer",
        "systems administrator", "blockchain developer", "ai researcher",
        "fullstack developer", "data analyst", "network engineer",
    ]

    _INDUSTRIES = [
        "artificial intelligence", "renewable energy", "biotech",
        "fintech", "cybersecurity", "quantum computing",
        "autonomous vehicles", "space technology", "edtech",
        "healthtech", "cleantech", "robotics",
    ]

    def get_entry_points(self) -> list[str]:
        return [
            "https://www.linkedin.com/feed/",
            "https://www.linkedin.com/jobs/",
            "https://www.linkedin.com/news/",
        ]

    def generate_search_queries(self, identity: Any, count: int = 5) -> list[str]:
        queries = []
        for _ in range(count):
            variant = random.choice(["job", "people", "company", "content"])
            if variant == "job":
                title = random.choice(self._JOB_TITLES)
                queries.append(f"{title} remote")
            elif variant == "people":
                industry = random.choice(self._INDUSTRIES)
                queries.append(f"{industry} expert")
            elif variant == "company":
                industry = random.choice(self._INDUSTRIES)
                queries.append(f"{industry} startups hiring")
            else:
                industry = random.choice(self._INDUSTRIES)
                queries.append(f"{industry} trends 2024")
        return queries

    async def execute_session(self, page, identity: Any, behavior_engine: Any) -> PlatformSession:
        session = PlatformSession(platform_name=self.name)

        entry = random.choice(self.get_entry_points())
        await page.goto(entry, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(entry)
        session.pages_visited += 1

        await behavior_engine.simulate_reading()

        actions = [
            PlatformAction("browse_feed", weight=3.0),
            PlatformAction("search_jobs", weight=4.0),
            PlatformAction("browse_companies", weight=2.0),
            PlatformAction("read_articles", weight=2.5),
            PlatformAction("search_people", weight=1.5),
        ]

        num_actions = random.randint(2, 5)
        selected = self.select_weighted_actions(actions, num_actions)

        for action in selected:
            try:
                if action.name == "browse_feed":
                    await self._browse_feed(page, session, behavior_engine)
                elif action.name == "search_jobs":
                    await self._search_jobs(page, session, behavior_engine)
                elif action.name == "browse_companies":
                    await self._browse_companies(page, session, behavior_engine)
                elif action.name == "read_articles":
                    await self._read_articles(page, session, behavior_engine)
                elif action.name == "search_people":
                    await self._search_people(page, session, behavior_engine)

                session.actions_performed.append(action.name)
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception:
                logger.debug("Action %s failed on LinkedIn, continuing", action.name)

        return session

    async def _browse_feed(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
        session.pages_visited += 1
        session.data_points_poisoned += 1

        for _ in range(random.randint(3, 8)):
            await behavior.simulate_scroll(page)
            await asyncio.sleep(random.uniform(2.0, 5.0))

    async def _search_jobs(self, page, session: PlatformSession, behavior) -> None:
        title = random.choice(self._JOB_TITLES)
        url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(title)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"jobs: {title}")
        session.pages_visited += 1
        session.data_points_poisoned += 2

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

        # Click on a job listing
        listings = await page.query_selector_all("a[href*='/jobs/view/']")
        if listings:
            listing = random.choice(listings[:5])
            try:
                await listing.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                session.data_points_poisoned += 1
                await behavior.simulate_reading()
            except Exception:
                pass

    async def _browse_companies(self, page, session: PlatformSession, behavior) -> None:
        industry = random.choice(self._INDUSTRIES)
        url = f"https://www.linkedin.com/search/results/companies/?keywords={quote_plus(industry)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"companies: {industry}")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)

    async def _read_articles(self, page, session: PlatformSession, behavior) -> None:
        await page.goto("https://www.linkedin.com/news/", wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append("https://www.linkedin.com/news/")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
        await behavior.simulate_reading()

        articles = await page.query_selector_all("a[href*='/pulse/'], a[href*='/news/']")
        if articles:
            article = random.choice(articles[:5])
            try:
                await article.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                session.pages_visited += 1
                await behavior.simulate_reading()
            except Exception:
                pass

    async def _search_people(self, page, session: PlatformSession, behavior) -> None:
        industry = random.choice(self._INDUSTRIES)
        url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(industry + ' professional')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        session.urls_visited.append(url)
        session.search_queries.append(f"people: {industry}")
        session.pages_visited += 1
        session.data_points_poisoned += 1

        await behavior.simulate_scroll(page)
