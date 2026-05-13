from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.loader import ConfigLoader
from config.validators import ConfigValidator
from core.event_bus import EventBus
from core.lifecycle import LifecycleManager
from core.orchestrator import Orchestrator
from core.plugin_loader import PluginLoader
from browser.behavior_engine import BehaviorEngine
from browser.controller import BrowserController
from identity.generator import IdentityGenerator
from platforms.registry import PlatformRegistry
from storage.sqlite import SQLiteDatabase
from telemetry.logging_config import setup_logging
from telemetry.metrics import MetricsCollector
from timing.circadian import CircadianProfile

logger = logging.getLogger("pdp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pdp",
        description="Personal Data Poison — targeted anti-OSINT traffic generator",
    )
    parser.add_argument(
        "-c", "--config-dir",
        default="configs",
        help="Path to configs directory (default: configs)",
    )
    parser.add_argument(
        "-p", "--profile",
        default=None,
        help="Profile name to load (desktop, mobile, research)",
    )
    parser.add_argument(
        "-n", "--sessions",
        type=int,
        default=0,
        help="Number of sessions to run (0 = continuous)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate identities without launching browser",
    )
    parser.add_argument(
        "-t", "--target",
        type=str,
        default=None,
        help="Target a specific platform (google, youtube, instagram, ...)",
    )
    parser.add_argument(
        "--mode",
        choices=["single_platform", "multi_platform", "mixed"],
        default=None,
        help="Override session mode from config",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    loader = ConfigLoader(args.config_dir)
    config = loader.load_with_profile(args.profile)

    if args.verbose:
        config.setdefault("general", {})["log_level"] = "DEBUG"
    if args.headless is not None:
        config.setdefault("browser", {})["headless"] = args.headless
    if args.mode:
        config.setdefault("session", {})["mode"] = args.mode

    logging_config = loader.load_logging_config()
    setup_logging(logging_config.get("logging", config.get("general", {})))

    validator = ConfigValidator()
    errors = validator.validate(config)
    if errors:
        logger.warning("Config validation issues: %s", errors)

    logger.info("Starting PDP with profile=%s, sessions=%d", args.profile, args.sessions)

    event_bus = EventBus()
    lifecycle = LifecycleManager(event_bus)

    db = SQLiteDatabase(config.get("storage", {}).get("database_path", "data/pdp.db"))
    db.initialize()

    metrics = MetricsCollector()

    async def on_session_completed(event):
        metrics.increment("sessions_completed")

    async def on_page_loaded(event):
        metrics.increment("pages_loaded")

    async def on_platform_session(event):
        platform = event.data.get("platform", "unknown") if event.data else "unknown"
        metrics.increment(f"platform.{platform}.sessions")

    event_bus.subscribe("session.completed", on_session_completed)
    event_bus.subscribe("page.loaded", on_page_loaded)
    event_bus.subscribe("platform.session.completed", on_platform_session)

    identity_generator = IdentityGenerator(config.get("identity", {}))
    browser_controller = BrowserController(config.get("browser", {}))
    behavior_engine = BehaviorEngine(config.get("behavior", {}))
    circadian = CircadianProfile(config.get("timing", {}).get("circadian", {}))

    # Build platform registry from config (weights are used at selection time)
    platform_config = config.get("platforms", {})
    registry = PlatformRegistry(config=platform_config)
    registry.register_builtin()

    # Account store (optional — only active when accounts.enabled is true)
    account_store = None
    accounts_config = config.get("accounts", {})
    if accounts_config.get("enabled", False):
        try:
            from accounts.store import AccountStore
            account_store = AccountStore(
                accounts_dir=accounts_config.get("accounts_dir", "data/accounts"),
            )
            account_store.load()
            platforms_with_accounts = account_store.get_platforms_with_accounts()
            logger.info("Account store loaded — credentials for: %s", platforms_with_accounts)
        except ValueError as e:
            logger.warning("Account store disabled: %s", e)
        except Exception:
            logger.exception("Failed to initialize account store")

    orchestrator = Orchestrator(
        config=config,
        event_bus=event_bus,
        identity_generator=identity_generator,
        browser_controller=browser_controller,
        behavior_engine=behavior_engine,
        circadian=circadian,
        platform_registry=registry,
        account_store=account_store,
    )

    plugin_loader = PluginLoader()
    plugin_paths = config.get("plugins", [])
    if plugin_paths:
        plugin_loader.load_all(plugin_paths)

    lifecycle.register_component(browser_controller)
    lifecycle.register_component(orchestrator)
    lifecycle.register_component(plugin_loader)

    await lifecycle.initialize()

    loop = asyncio.get_event_loop()
    lifecycle.install_signal_handlers(loop)

    if args.dry_run:
        identities = identity_generator.create_batch(max(args.sessions, 5))
        for ident in identities:
            logger.info("Generated: %s | %s | %s/%s | %s | platforms=%s",
                        ident.alias, ident.persona_name,
                        ident.device.os_name, ident.device.browser_name,
                        ident.device.locale,
                        list(ident.preferences.platform_interests.keys()))
        logger.info("Dry run complete — %d identities generated", len(identities))
        logger.info("Registered platforms: %s", list(registry._strategies.keys()))
    elif args.target:
        # Single targeted platform run
        logger.info("Targeting platform: %s", args.target)
        identity = identity_generator.create()
        await orchestrator.run_targeted_session(args.target, identity)
    else:
        try:
            await orchestrator.run_continuous(max_sessions=args.sessions)
        except KeyboardInterrupt:
            pass

    await lifecycle.shutdown()
    db.close()

    snapshot = metrics.snapshot()
    logger.info("Session stats: %s", snapshot.get("counters", {}))
    logger.info("Platform stats: %s", registry.get_stats())


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
