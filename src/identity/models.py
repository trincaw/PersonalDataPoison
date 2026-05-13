from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OSFamily(str, Enum):
    WINDOWS = "Windows"
    MACOS = "macOS"
    LINUX = "Linux"


class BrowserFamily(str, Enum):
    CHROMIUM = "Chromium"
    FIREFOX = "Firefox"
    WEBKIT = "WebKit"


class DeviceProfile(BaseModel):
    os_name: str
    os_version: str = ""
    browser_name: str
    browser_version: str = ""
    screen_width: int
    screen_height: int
    color_depth: int = 24
    timezone: str
    locale: str
    user_agent: str = ""
    platform: str = ""
    hardware_concurrency: int = 8
    device_memory: int = 8
    webgl_vendor: str = ""
    webgl_renderer: str = ""

    def fingerprint_hash(self) -> str:
        import hashlib
        components = (
            f"{self.os_name}|{self.os_version}|{self.browser_name}|{self.browser_version}|"
            f"{self.screen_width}x{self.screen_height}|{self.timezone}|{self.locale}|"
            f"{self.hardware_concurrency}|{self.device_memory}"
        )
        return hashlib.sha256(components.encode()).hexdigest()[:16]


class BrowsingPreferences(BaseModel):
    preferred_categories: list[str] = Field(default_factory=lambda: ["news", "tech", "wiki"])
    search_engines: list[str] = Field(default_factory=lambda: ["google", "duckduckgo"])
    social_platforms: list[str] = Field(default_factory=list)
    language_codes: list[str] = Field(default_factory=lambda: ["en"])
    typing_speed_wpm: float = 60.0
    scroll_speed: str = "medium"
    # Per-platform poison interests — different interests per data collector
    platform_interests: dict[str, list[str]] = Field(default_factory=dict)


class Identity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    alias: str
    persona_name: str = ""
    email_pattern: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: Optional[datetime] = None
    device: DeviceProfile
    preferences: BrowsingPreferences = Field(default_factory=BrowsingPreferences)
    reputation_score: float = 1.0
    session_count: int = 0
    total_pages_visited: int = 0
    total_data_points_poisoned: int = 0
    platform_session_counts: dict[str, int] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def touch(self, platform: str | None = None) -> None:
        self.last_seen = datetime.now(timezone.utc)
        self.session_count += 1
        if platform:
            self.platform_session_counts[platform] = (
                self.platform_session_counts.get(platform, 0) + 1
            )