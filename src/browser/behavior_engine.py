from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class BehaviorEngine:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._scroll_speed = self._config.get("scroll_speed", "medium")

    async def simulate_human_interaction(self, page) -> None:
        actions = [
            self.simulate_reading,
            lambda: self.simulate_scroll(page),
            lambda: self.simulate_mouse_movement(page),
        ]

        if random.random() < 0.3:
            actions.append(lambda: self.simulate_hover(page))

        random.shuffle(actions)
        num_actions = random.randint(2, min(len(actions), 4))

        for action in actions[:num_actions]:
            await action()
            await asyncio.sleep(random.uniform(0.2, 0.8))

    async def simulate_reading(self) -> None:
        duration = random.uniform(2.0, 12.0)
        logger.debug("Simulating reading for %.1fs", duration)
        await asyncio.sleep(duration)

    async def simulate_scroll(self, page) -> None:
        speed_map = {"slow": (100, 300), "medium": (200, 600), "fast": (400, 900)}
        low, high = speed_map.get(self._scroll_speed, (200, 600))

        num_scrolls = random.randint(1, 5)
        for _ in range(num_scrolls):
            distance = random.randint(low, high)
            if random.random() < 0.15:
                distance = -distance  # occasional scroll up

            await page.mouse.wheel(0, distance)
            await asyncio.sleep(random.uniform(0.3, 1.5))

        logger.debug("Scrolled %d times", num_scrolls)

    async def simulate_mouse_movement(self, page) -> None:
        viewport = page.viewport_size or {"width": 1920, "height": 1080}
        num_moves = random.randint(2, 6)

        for _ in range(num_moves):
            x = random.randint(50, viewport["width"] - 50)
            y = random.randint(50, viewport["height"] - 50)
            await page.mouse.move(x, y, steps=random.randint(5, 20))
            await asyncio.sleep(random.uniform(0.1, 0.5))

        logger.debug("Moved mouse %d times", num_moves)

    async def simulate_hover(self, page) -> None:
        try:
            links = await page.query_selector_all("a[href]")
            if links:
                link = random.choice(links[:20])
                box = await link.bounding_box()
                if box:
                    await page.mouse.move(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                        steps=random.randint(5, 15),
                    )
                    await asyncio.sleep(random.uniform(0.3, 1.2))
                    logger.debug("Hovered over a link")
        except Exception:
            pass

    async def simulate_typing(self, page, selector: str, text: str, wpm: float = 60.0) -> None:
        element = await page.query_selector(selector)
        if not element:
            return

        await element.click()
        char_delay = 60.0 / (wpm * 5)

        for char in text:
            await element.type(char, delay=int(char_delay * 1000 * random.uniform(0.7, 1.3)))
            if random.random() < 0.02:
                await asyncio.sleep(random.uniform(0.5, 2.0))

    async def simulate_click(self, page, selector: str) -> bool:
        try:
            element = await page.query_selector(selector)
            if not element:
                return False
            box = await element.bounding_box()
            if box:
                x = box["x"] + random.uniform(2, box["width"] - 2)
                y = box["y"] + random.uniform(2, box["height"] - 2)
                await page.mouse.click(x, y, delay=random.randint(50, 150))
                return True
        except Exception:
            pass
        return False