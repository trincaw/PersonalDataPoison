"""Platform-specific login flows using Playwright.

Each platform has its own login page structure, CAPTCHA handling,
and 2FA flows. These are implemented as async functions that
authenticate a browser context against a specific platform.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import Page, BrowserContext

from accounts.store import AccountCredential

logger = logging.getLogger(__name__)


class LoginResult:
    """Result of a login attempt."""

    def __init__(self, success: bool, platform: str, username: str, error: str = "") -> None:
        self.success = success
        self.platform = platform
        self.username = username
        self.error = error


class PlatformLogin:
    """Handles login flows for each platform."""

    # Max wait time for page loads during login
    NAVIGATION_TIMEOUT = 30_000  # ms
    # Delay between typing characters (human-like)
    TYPING_DELAY = 80  # ms

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def login(self, page: Page, credential: AccountCredential) -> LoginResult:
        """Route to the correct platform login handler."""
        handlers = {
            "google": self._login_google,
            "youtube": self._login_google,  # YouTube uses Google auth
            "instagram": self._login_instagram,
            "facebook": self._login_facebook,
            "tiktok": self._login_tiktok,
            "linkedin": self._login_linkedin,
            "twitter": self._login_twitter,
            "amazon": self._login_amazon,
        }

        handler = handlers.get(credential.platform)
        if handler is None:
            return LoginResult(False, credential.platform, credential.username,
                               f"No login handler for platform: {credential.platform}")

        try:
            return await handler(page, credential)
        except Exception as e:
            logger.exception("Login failed for %s@%s", credential.username, credential.platform)
            return LoginResult(False, credential.platform, credential.username, str(e))

    async def _login_google(self, page: Page, cred: AccountCredential) -> LoginResult:
        """Google/YouTube login flow."""
        await page.goto("https://accounts.google.com/signin", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(2)

        # Email field
        email_input = page.locator('input[type="email"]')
        await email_input.fill("")
        await email_input.type(cred.email or cred.username, delay=self.TYPING_DELAY)
        await page.locator('#identifierNext button, [data-idom-class*="nCP5yc"]').click()
        await asyncio.sleep(3)

        # Password field
        password_input = page.locator('input[type="password"]')
        await password_input.wait_for(state="visible", timeout=10_000)
        await password_input.type(cred.password, delay=self.TYPING_DELAY)
        await page.locator('#passwordNext button, [data-idom-class*="nCP5yc"]').click()
        await asyncio.sleep(5)

        # Check if login succeeded (redirected away from accounts.google.com)
        if "myaccount.google.com" in page.url or "google.com" in page.url:
            if "challenge" not in page.url and "signin" not in page.url:
                logger.info("Google login success: %s", cred.username)
                return LoginResult(True, "google", cred.username)

        # Might need 2FA or got blocked
        if "challenge" in page.url:
            return LoginResult(False, "google", cred.username,
                               "2FA challenge detected — manual intervention needed")

        return LoginResult(False, "google", cred.username,
                           f"Login unclear, current URL: {page.url}")

    async def _login_instagram(self, page: Page, cred: AccountCredential) -> LoginResult:
        """Instagram login flow."""
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(3)

        # Dismiss cookie dialog if present
        try:
            cookie_btn = page.locator('button:has-text("Allow"), button:has-text("Accetta")')
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        username_input = page.locator('input[name="username"]')
        await username_input.type(cred.username, delay=self.TYPING_DELAY)

        password_input = page.locator('input[name="password"]')
        await password_input.type(cred.password, delay=self.TYPING_DELAY)

        await page.locator('button[type="submit"]').click()
        await asyncio.sleep(5)

        # Check for success
        if "instagram.com" in page.url and "login" not in page.url:
            logger.info("Instagram login success: %s", cred.username)
            return LoginResult(True, "instagram", cred.username)

        # Check for "suspicious login" or challenge
        if "challenge" in page.url:
            return LoginResult(False, "instagram", cred.username,
                               "Security challenge detected")

        return LoginResult(False, "instagram", cred.username,
                           f"Login may have failed, URL: {page.url}")

    async def _login_facebook(self, page: Page, cred: AccountCredential) -> LoginResult:
        """Facebook login flow."""
        await page.goto("https://www.facebook.com/login", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(2)

        # Dismiss cookies
        try:
            cookie_btn = page.locator('button[data-cookiebanner="accept_button"], button:has-text("Accetta")')
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        await page.locator('#email').type(cred.email or cred.username, delay=self.TYPING_DELAY)
        await page.locator('#pass').type(cred.password, delay=self.TYPING_DELAY)
        await page.locator('button[name="login"]').click()
        await asyncio.sleep(5)

        if "facebook.com" in page.url and "login" not in page.url and "checkpoint" not in page.url:
            logger.info("Facebook login success: %s", cred.username)
            return LoginResult(True, "facebook", cred.username)

        if "checkpoint" in page.url:
            return LoginResult(False, "facebook", cred.username, "Checkpoint/2FA required")

        return LoginResult(False, "facebook", cred.username,
                           f"Login unclear, URL: {page.url}")

    async def _login_tiktok(self, page: Page, cred: AccountCredential) -> LoginResult:
        """TikTok login flow (email/password)."""
        await page.goto("https://www.tiktok.com/login/phone-or-email/email", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(3)

        username_input = page.locator('input[name="username"], input[placeholder*="email" i]')
        await username_input.type(cred.email or cred.username, delay=self.TYPING_DELAY)

        password_input = page.locator('input[type="password"]')
        await password_input.type(cred.password, delay=self.TYPING_DELAY)

        await page.locator('button[type="submit"]').click()
        await asyncio.sleep(5)

        if "tiktok.com" in page.url and "login" not in page.url:
            logger.info("TikTok login success: %s", cred.username)
            return LoginResult(True, "tiktok", cred.username)

        return LoginResult(False, "tiktok", cred.username,
                           f"Login may have failed, URL: {page.url}")

    async def _login_linkedin(self, page: Page, cred: AccountCredential) -> LoginResult:
        """LinkedIn login flow."""
        await page.goto("https://www.linkedin.com/login", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(2)

        await page.locator('#username').type(cred.email or cred.username, delay=self.TYPING_DELAY)
        await page.locator('#password').type(cred.password, delay=self.TYPING_DELAY)
        await page.locator('button[type="submit"]').click()
        await asyncio.sleep(5)

        if "linkedin.com/feed" in page.url or "linkedin.com/mynetwork" in page.url:
            logger.info("LinkedIn login success: %s", cred.username)
            return LoginResult(True, "linkedin", cred.username)

        if "challenge" in page.url or "checkpoint" in page.url:
            return LoginResult(False, "linkedin", cred.username, "Security challenge detected")

        return LoginResult(False, "linkedin", cred.username,
                           f"Login unclear, URL: {page.url}")

    async def _login_twitter(self, page: Page, cred: AccountCredential) -> LoginResult:
        """Twitter/X login flow."""
        await page.goto("https://x.com/i/flow/login", wait_until="networkidle",
                        timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(3)

        # Username step
        username_input = page.locator('input[autocomplete="username"]')
        await username_input.wait_for(state="visible", timeout=10_000)
        await username_input.type(cred.username, delay=self.TYPING_DELAY)
        await page.locator('button:has-text("Next"), button:has-text("Avanti")').click()
        await asyncio.sleep(3)

        # Password step
        password_input = page.locator('input[type="password"]')
        await password_input.wait_for(state="visible", timeout=10_000)
        await password_input.type(cred.password, delay=self.TYPING_DELAY)
        await page.locator('button[data-testid="LoginForm_Login_Button"]').click()
        await asyncio.sleep(5)

        if "x.com/home" in page.url or ("x.com" in page.url and "login" not in page.url):
            logger.info("Twitter/X login success: %s", cred.username)
            return LoginResult(True, "twitter", cred.username)

        return LoginResult(False, "twitter", cred.username,
                           f"Login unclear, URL: {page.url}")

    async def _login_amazon(self, page: Page, cred: AccountCredential) -> LoginResult:
        """Amazon login flow."""
        await page.goto("https://www.amazon.it/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.it",
                        wait_until="networkidle", timeout=self.NAVIGATION_TIMEOUT)
        await asyncio.sleep(2)

        await page.locator('#ap_email').type(cred.email or cred.username, delay=self.TYPING_DELAY)
        await page.locator('#continue').click()
        await asyncio.sleep(2)

        await page.locator('#ap_password').type(cred.password, delay=self.TYPING_DELAY)
        await page.locator('#signInSubmit').click()
        await asyncio.sleep(5)

        if "amazon" in page.url and "signin" not in page.url and "ap/" not in page.url:
            logger.info("Amazon login success: %s", cred.username)
            return LoginResult(True, "amazon", cred.username)

        if "approval" in page.url or "mfa" in page.url:
            return LoginResult(False, "amazon", cred.username, "MFA/approval required")

        return LoginResult(False, "amazon", cred.username,
                           f"Login unclear, URL: {page.url}")


async def save_session_after_login(
    context: BrowserContext,
    identity_id: str,
    platform: str,
    sessions_dir: str = "data/sessions",
) -> str:
    """Save browser session state (cookies + localStorage) after login."""
    from pathlib import Path

    session_dir = Path(sessions_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    path = session_dir / f"{identity_id}_{platform}.json"
    state = await context.storage_state(path=str(path))
    logger.info("Saved authenticated session: %s → %s", platform, path.name)
    return str(path)


async def load_session(
    identity_id: str,
    platform: str,
    sessions_dir: str = "data/sessions",
) -> str | None:
    """Check if we have a saved session for this identity+platform."""
    from pathlib import Path

    path = Path(sessions_dir) / f"{identity_id}_{platform}.json"
    if path.exists():
        return str(path)
    return None
