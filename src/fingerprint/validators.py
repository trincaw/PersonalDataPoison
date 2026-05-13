from __future__ import annotations

import logging
import re

from identity.models import DeviceProfile

logger = logging.getLogger(__name__)


class FingerprintFieldValidator:

    @staticmethod
    def validate_user_agent(ua: str) -> bool:
        if not ua:
            return True
        return bool(re.match(r"^Mozilla/5\.0 \(", ua))

    @staticmethod
    def validate_screen(width: int, height: int) -> bool:
        if width < 320 or height < 240:
            return False
        if width > 7680 or height > 4320:
            return False
        return True

    @staticmethod
    def validate_timezone(tz: str) -> bool:
        if not tz or "/" not in tz:
            return False
        parts = tz.split("/")
        return len(parts) >= 2 and parts[0] in (
            "Africa", "America", "Asia", "Atlantic", "Australia",
            "Europe", "Indian", "Pacific", "Etc",
        )

    @staticmethod
    def validate_locale(locale: str) -> bool:
        return bool(re.match(r"^[a-z]{2}(-[A-Z]{2})?$", locale))

    def validate_all(self, device: DeviceProfile) -> list[str]:
        errors: list[str] = []
        if not self.validate_user_agent(device.user_agent):
            errors.append(f"Invalid user_agent format: {device.user_agent[:50]}")
        if not self.validate_screen(device.screen_width, device.screen_height):
            errors.append(f"Invalid screen: {device.screen_width}x{device.screen_height}")
        if not self.validate_timezone(device.timezone):
            errors.append(f"Invalid timezone: {device.timezone}")
        if not self.validate_locale(device.locale):
            errors.append(f"Invalid locale: {device.locale}")
        if errors:
            logger.warning("Fingerprint validation errors: %s", errors)
        return errors
