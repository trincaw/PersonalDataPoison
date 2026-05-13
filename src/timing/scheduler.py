from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from timing.circadian import CircadianProfile
from timing.distributions import TimingDistribution

logger = logging.getLogger(__name__)

Task = Callable[[], Coroutine[Any, Any, None]]


class Scheduler:

    def __init__(
        self,
        circadian: CircadianProfile | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._circadian = circadian or CircadianProfile()
        self._config = config or {}
        self._running = False
        self._tasks: list[tuple[str, Task, dict[str, Any]]] = []

    def add_task(self, name: str, task: Task, **timing_opts) -> None:
        self._tasks.append((name, task, timing_opts))
        logger.info("Scheduled task: %s", name)

    async def initialize(self) -> None:
        self._running = True

    async def shutdown(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Scheduler started with %d tasks", len(self._tasks))

        while self._running:
            now = datetime.now(timezone.utc)

            if not self._circadian.should_be_active(now):
                sleep_time = TimingDistribution.uniform(60, 300)
                logger.debug("Outside active window, sleeping %.0fs", sleep_time)
                await asyncio.sleep(sleep_time)
                continue

            for name, task, opts in self._tasks:
                if not self._running:
                    break

                try:
                    logger.debug("Executing task: %s", name)
                    await task()
                except Exception:
                    logger.exception("Task '%s' failed", name)

                inter_task_delay = self._circadian.suggested_delay(
                    opts.get("base_delay", 10.0), now
                )
                jitter = TimingDistribution.gaussian(inter_task_delay, inter_task_delay * 0.2)
                await asyncio.sleep(jitter)

            cycle_delay = self._circadian.suggested_delay(
                self._config.get("cycle_delay", 60.0), now
            )
            logger.debug("Cycle complete, waiting %.1fs", cycle_delay)
            await asyncio.sleep(cycle_delay)

    async def run_once(self) -> None:
        for name, task, _opts in self._tasks:
            try:
                await task()
            except Exception:
                logger.exception("Task '%s' failed", name)
