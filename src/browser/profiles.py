from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from identity.models import DeviceProfile

logger = logging.getLogger(__name__)

_DEFAULT_PROFILES_DIR = "data/browser_profiles"


class BrowserProfileManager:

    def __init__(self, profiles_dir: str | Path = _DEFAULT_PROFILES_DIR) -> None:
        self._dir = Path(profiles_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def build_context_options(self, device: DeviceProfile) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "locale": device.locale,
            "timezone_id": device.timezone,
            "viewport": {"width": device.screen_width, "height": device.screen_height},
            "screen": {"width": device.screen_width, "height": device.screen_height},
            "color_scheme": "light",
            "user_agent": device.user_agent,
            "extra_http_headers": {
                "Accept-Language": self._build_accept_language(device.locale),
            },
        }
        return opts

    def save_state(self, identity_id: str, state: dict[str, Any]) -> None:
        path = self._dir / f"{identity_id}.json"
        path.write_text(json.dumps(state, indent=2))
        logger.debug("Saved browser profile state for %s", identity_id)

    def load_state(self, identity_id: str) -> dict[str, Any] | None:
        path = self._dir / f"{identity_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def delete_state(self, identity_id: str) -> bool:
        path = self._dir / f"{identity_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_profiles(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.json")]

    @staticmethod
    def _build_accept_language(locale: str) -> str:
        lang = locale.split("-")[0]
        parts = [locale]
        if lang != locale:
            parts.append(f"{lang};q=0.9")
        if lang != "en":
            parts.append("en;q=0.8")
        return ", ".join(parts)
