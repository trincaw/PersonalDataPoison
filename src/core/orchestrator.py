from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from core.event_bus import EventBus
from identity.generator import IdentityGenerator
from identity.models import Identity
from browser.controller import BrowserController
from browser.behavior_engine import BehaviorEngine
from accounts.store import AccountStore
from accounts.login import PlatformLogin, LoginResult, save_session_after_login, load_session
from platforms.registry import PlatformRegistry
from timing.circadian import CircadianProfile
from timing.distributions import TimingDistribution

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates targeted sessions against specific data-collecting platforms.

    Instead of generic browsing, each session targets a specific platform
    (Google, Instagram, Facebook, etc.) with realistic per-platform behavior
    to maximize data poisoning effectiveness and OSINT decorrelation.
    """

    def __init__(
        self,
        config: dict[str, Any],
        event_bus: EventBus,
        identity_generator: IdentityGenerator,
        browser_controller: BrowserController,
        behavior_engine: BehaviorEngine,
        platform_registry: PlatformRegistry,
        circadian: CircadianProfile,
        account_store: AccountStore | None = None,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._identity_generator = identity_generator
        self._browser = browser_controller
        self._behavior = behavior_engine
        self._platforms = platform_registry
        self._circadian = circadian
        self._account_store = account_store
        self._platform_login = PlatformLogin(config.get("accounts", {}))
        self._running = False
        self._active_sessions: dict[str, Any] = {}
        self._total_data_points = 0

    async def initialize(self) -> None:
        self._running = True
        logger.info("Orchestrator initialized — %d platforms available: %s",
                     self._platforms.platform_count,
                     ", ".join(self._platforms.available_platforms))

    async def shutdown(self) -> None:
        self._running = False
        for session_id, ctx in list(self._active_sessions.items()):
            try:
                await ctx.close()
            except Exception:
                logger.exception("Error closing session %s", session_id)
        self._active_sessions.clear()
        logger.info("Orchestrator shut down — total data points poisoned: %d", self._total_data_points)

    async def run_targeted_session(
        self,
        platform_name: str | None = None,
        identity: Identity | None = None,
    ) -> None:
        """Run a session targeting a specific data collection platform."""
        if identity is None:
            identity = self._identity_generator.create()

        # Select platform
        if platform_name:
            platform = self._platforms.get(platform_name)
            if platform is None:
                logger.error("Unknown platform: %s", platform_name)
                return
        else:
            platform = self._platforms.select_platform()

        await self._event_bus.emit("session.starting", {
            "identity_id": str(identity.id),
            "platform": platform.name,
            "platform_display": platform.display_name,
        })

        logger.info("▶ Session: %s → %s (identity: %s)",
                     identity.alias, platform.display_name, identity.device.locale)

        # Build browser profile from identity
        identity_str = str(identity.id)
        sessions_dir = self._config.get("accounts", {}).get("sessions_dir", "data/sessions")

        # Check for saved authenticated session
        saved_session = await load_session(identity_str, platform.name, sessions_dir)

        profile = {
            "locale": identity.device.locale,
            "timezone": identity.device.timezone,
            "screen": {
                "width": identity.device.screen_width,
                "height": identity.device.screen_height,
            },
            "user_agent": identity.device.user_agent,
        }

        # If we have a saved session, load it into the browser context
        if saved_session:
            profile["storage_state"] = saved_session
            logger.info("Restoring saved session for %s@%s", identity.alias, platform.name)

        context = await self._browser.launch(profile)
        self._active_sessions[identity_str] = context

        try:
            page = await context.new_page()

            # Attempt login if we have credentials and no saved session
            if not saved_session and self._account_store:
                credential = self._account_store.get_account(platform.name, identity_str)
                if credential:
                    logger.info("Attempting login: %s → %s", credential.username, platform.display_name)
                    login_result = await self._platform_login.login(page, credential)
                    if login_result.success:
                        # Save session for future reuse
                        await save_session_after_login(context, identity_str, platform.name, sessions_dir)
                        await self._event_bus.emit("account.login.success", {
                            "platform": platform.name,
                            "username": credential.username,
                        })
                    else:
                        logger.warning("Login failed for %s@%s: %s",
                                       credential.username, platform.name, login_result.error)
                        await self._event_bus.emit("account.login.failed", {
                            "platform": platform.name,
                            "username": credential.username,
                            "error": login_result.error,
                        })

            # Execute platform-specific session
            result = await platform.execute_session(page, identity, self._behavior)

            self._total_data_points += result.data_points_poisoned

            await self._event_bus.emit("session.completed", {
                "identity_id": str(identity.id),
                "platform": platform.name,
                "pages_visited": result.pages_visited,
                "data_points_poisoned": result.data_points_poisoned,
                "search_queries": result.search_queries,
                "actions": result.actions_performed,
            })

            logger.info("✓ Session complete: %s → %s | pages=%d queries=%d poisoned=%d",
                         identity.alias, platform.display_name,
                         result.pages_visited, len(result.search_queries),
                         result.data_points_poisoned)

        except Exception:
            logger.exception("Session error: %s → %s", identity.alias, platform.display_name)
            await self._event_bus.emit("session.error", {
                "identity_id": str(identity.id),
                "platform": platform.name,
            })
        finally:
            await context.close()
            self._active_sessions.pop(str(identity.id), None)

    async def run_multi_platform_session(self, identity: Identity | None = None) -> None:
        """Run a multi-platform session — same identity visits multiple platforms.

        This simulates realistic cross-platform browsing behavior where a user
        visits Google, then YouTube, then checks Instagram in the same sitting.
        """
        if identity is None:
            identity = self._identity_generator.create()

        num_platforms = random.randint(2, 4)
        platforms = self._platforms.select_multi(num_platforms)

        logger.info("▶ Multi-platform session: %s → [%s]",
                     identity.alias, ", ".join(p.display_name for p in platforms))

        for platform in platforms:
            if not self._running:
                break

            await self.run_targeted_session(platform.name, identity)

            # Realistic delay between switching platforms
            delay = TimingDistribution.gaussian(
                mean=self._config.get("timing", {}).get("inter_platform_mean", 30.0),
                sigma=self._config.get("timing", {}).get("inter_platform_sigma", 15.0),
            )
            await asyncio.sleep(delay)

    async def run_continuous(self, max_sessions: int = 0) -> None:
        """Run continuous sessions with platform rotation and circadian awareness."""
        session_count = 0
        mode = self._config.get("session", {}).get("mode", "single_platform")

        while self._running:
            if max_sessions and session_count >= max_sessions:
                break

            # Circadian check
            if not self._circadian.should_be_active():
                sleep_time = self._circadian.suggested_delay(60.0)
                logger.debug("Outside active window, sleeping %.0fs", sleep_time)
                await asyncio.sleep(sleep_time)
                continue

            if mode == "multi_platform" or (mode == "mixed" and random.random() < 0.3):
                await self.run_multi_platform_session()
            else:
                await self.run_targeted_session()

            session_count += 1

            # Inter-session pause with circadian modulation
            pause = TimingDistribution.gaussian(
                mean=self._config.get("timing", {}).get("inter_session_mean", 300.0),
                sigma=self._config.get("timing", {}).get("inter_session_sigma", 120.0),
            ) * (1.0 / max(self._circadian.activity_multiplier(), 0.1))

            logger.info("Waiting %.1fs before next session (total sessions: %d, poisoned: %d)",
                         pause, session_count, self._total_data_points)
            await asyncio.sleep(pause)

        # Log final stats
        stats = self._platforms.get_stats()
        logger.info("=== Final Stats ===")
        logger.info("Sessions: %d | Data points poisoned: %d", session_count, self._total_data_points)
        logger.info("Platform distribution: %s", stats)