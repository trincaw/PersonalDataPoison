from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any


class CircadianProfile:

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._wake_hour = cfg.get("wake_hour", 7)
        self._sleep_hour = cfg.get("sleep_hour", 23)
        self._peak_hour = cfg.get("peak_hour", 14)
        self._noise = cfg.get("noise", 0.1)
        self._weekend_shift = cfg.get("weekend_shift_hours", 1.5)

    def activity_multiplier(self, dt: datetime | None = None) -> float:
        if dt is None:
            dt = datetime.now(timezone.utc)

        hour = dt.hour + dt.minute / 60.0

        if dt.weekday() >= 5:
            hour = (hour - self._weekend_shift) % 24

        if self._sleep_hour <= hour or hour < self._wake_hour:
            base = 0.05
        else:
            awake_range = (self._sleep_hour - self._wake_hour) % 24
            if awake_range == 0:
                awake_range = 16
            mid = self._wake_hour + awake_range / 2
            normalized = (hour - mid) / (awake_range / 2)
            base = math.exp(-0.5 * (normalized ** 2))

        noise = random.uniform(-self._noise, self._noise)
        return max(0.01, min(1.0, base + noise))

    def should_be_active(self, dt: datetime | None = None) -> bool:
        return self.activity_multiplier(dt) > 0.2

    def suggested_delay(self, base_delay: float, dt: datetime | None = None) -> float:
        multiplier = self.activity_multiplier(dt)
        if multiplier < 0.1:
            return base_delay * 10
        return base_delay / multiplier

    def next_active_window(self, dt: datetime | None = None) -> tuple[int, int]:
        return (self._wake_hour, self._sleep_hour)