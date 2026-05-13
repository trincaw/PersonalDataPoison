from __future__ import annotations

import logging
from typing import Any

from identity.models import DeviceProfile, Identity
from identity.generator import IdentityGenerator
from fingerprint.consistency import FingerprintConsistencyValidator, ValidationResult

logger = logging.getLogger(__name__)


class FingerprintManager:

    def __init__(
        self,
        generator: IdentityGenerator,
        validator: FingerprintConsistencyValidator | None = None,
        max_retries: int = 10,
    ) -> None:
        self._generator = generator
        self._validator = validator or FingerprintConsistencyValidator()
        self._max_retries = max_retries
        self._known_hashes: set[str] = set()

    def generate_consistent_identity(self, **kwargs) -> Identity:
        for attempt in range(self._max_retries):
            identity = self._generator.create(**kwargs)
            result = self._validator.validate(identity.device)

            if not result.valid:
                logger.debug("Attempt %d: inconsistent fingerprint — %s", attempt + 1, result.issues)
                continue

            fp_hash = identity.device.fingerprint_hash()
            if fp_hash in self._known_hashes:
                logger.debug("Attempt %d: duplicate fingerprint hash %s", attempt + 1, fp_hash)
                continue

            self._known_hashes.add(fp_hash)
            logger.info("Generated consistent identity on attempt %d (hash=%s)", attempt + 1, fp_hash)
            return identity

        logger.warning("Max retries reached, returning last generated identity")
        return self._generator.create(**kwargs)

    def validate_identity(self, identity: Identity) -> ValidationResult:
        return self._validator.validate(identity.device)

    def get_browser_args(self, device: DeviceProfile) -> dict[str, Any]:
        args: dict[str, Any] = {
            "locale": device.locale,
            "timezone_id": device.timezone,
            "viewport": {"width": device.screen_width, "height": device.screen_height},
            "user_agent": device.user_agent,
            "color_scheme": "light",
            "screen": {"width": device.screen_width, "height": device.screen_height},
        }

        if device.browser_name == "Chromium":
            args["extra_http_headers"] = {
                "Accept-Language": device.locale.replace("-", ",") + ";q=0.9",
            }

        return args

    def register_hash(self, fp_hash: str) -> None:
        self._known_hashes.add(fp_hash)

    @property
    def known_fingerprints(self) -> int:
        return len(self._known_hashes)
