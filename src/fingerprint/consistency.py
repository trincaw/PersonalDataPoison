from __future__ import annotations

import logging
from dataclasses import dataclass

from identity.models import DeviceProfile

logger = logging.getLogger(__name__)

_TIMEZONE_LOCALE_RULES: list[tuple[str, str, bool]] = [
    ("Europe/", "ja", False),
    ("Europe/", "zh", False),
    ("Asia/Tokyo", "en-US", False),
    ("Asia/Shanghai", "en-US", False),
    ("America/", "ja", False),
    ("America/", "zh", False),
]

_OS_PLATFORM_RULES = {
    "Windows": ["Win32"],
    "macOS": ["MacIntel"],
    "Linux": ["Linux x86_64", "Linux aarch64"],
}

_OS_BROWSER_EXCLUSIONS = [
    ("Linux", "WebKit"),
]


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str]

    def __bool__(self) -> bool:
        return self.valid


class FingerprintConsistencyValidator:

    def validate(self, profile: DeviceProfile) -> ValidationResult:
        issues: list[str] = []

        for tz_prefix, locale_prefix, allowed in _TIMEZONE_LOCALE_RULES:
            if profile.timezone.startswith(tz_prefix) and profile.locale.startswith(locale_prefix):
                if not allowed:
                    issues.append(f"Timezone {profile.timezone} inconsistent with locale {profile.locale}")

        expected_platforms = _OS_PLATFORM_RULES.get(profile.os_name, [])
        if expected_platforms and profile.platform and profile.platform not in expected_platforms:
            issues.append(f"Platform '{profile.platform}' inconsistent with OS '{profile.os_name}'")

        for os_name, browser in _OS_BROWSER_EXCLUSIONS:
            if profile.os_name == os_name and profile.browser_name == browser:
                issues.append(f"Browser {browser} uncommon on {os_name}")

        if profile.screen_width < profile.screen_height:
            issues.append("Desktop screen_width < screen_height is unusual")

        if profile.user_agent:
            if profile.os_name == "Windows" and "Windows NT" not in profile.user_agent:
                issues.append("User-agent doesn't match Windows OS")
            if profile.os_name == "macOS" and "Macintosh" not in profile.user_agent:
                issues.append("User-agent doesn't match macOS")
            if profile.os_name == "Linux" and "Linux" not in profile.user_agent:
                issues.append("User-agent doesn't match Linux OS")

        if issues:
            logger.warning("Fingerprint inconsistencies for %s: %s", profile.fingerprint_hash(), issues)

        return ValidationResult(valid=len(issues) == 0, issues=issues)