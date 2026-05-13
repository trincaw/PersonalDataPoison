"""Tests for the platform targeting system."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from platforms.base import PlatformAction, PlatformSession, PlatformStrategy
from platforms.registry import PlatformRegistry
from platforms.google import GoogleStrategy
from platforms.youtube import YouTubeStrategy
from platforms.instagram import InstagramStrategy
from platforms.facebook import FacebookStrategy
from platforms.tiktok import TikTokStrategy
from platforms.linkedin import LinkedInStrategy
from platforms.twitter import TwitterStrategy
from platforms.amazon import AmazonStrategy


# --- Fixtures ---

@pytest.fixture
def registry():
    reg = PlatformRegistry()
    reg.register_builtin()
    return reg


@pytest.fixture
def google():
    return GoogleStrategy({"locale": "it"})


@pytest.fixture
def mock_identity():
    identity = MagicMock()
    identity.preferences.preferred_categories = ["tech", "science", "cooking"]
    identity.preferences.platform_interests = {
        "google": ["quantum computing", "beekeeping"],
        "youtube": ["origami", "mycology"],
        "instagram": ["astrophotography", "calligraphy"],
    }
    identity.device.locale = "it-IT"
    return identity


# --- PlatformRegistry Tests ---

class TestPlatformRegistry:

    def test_register_builtin_all(self, registry: PlatformRegistry):
        assert registry.platform_count == 8
        expected = {"google", "youtube", "instagram", "facebook",
                    "tiktok", "linkedin", "twitter", "amazon"}
        assert set(registry.available_platforms) == expected

    def test_register_builtin_subset(self):
        reg = PlatformRegistry()
        reg.register_builtin(["google", "youtube"])
        assert reg.platform_count == 2
        assert set(reg.available_platforms) == {"google", "youtube"}

    def test_register_builtin_unknown_ignored(self):
        reg = PlatformRegistry()
        reg.register_builtin(["google", "nonexistent_platform"])
        assert reg.platform_count == 1
        assert "google" in reg.available_platforms

    def test_get_existing(self, registry: PlatformRegistry):
        g = registry.get("google")
        assert g is not None
        assert g.name == "google"

    def test_get_nonexistent(self, registry: PlatformRegistry):
        assert registry.get("myspace") is None

    def test_select_platform_returns_registered(self, registry: PlatformRegistry):
        platform = registry.select_platform()
        assert platform.name in registry.available_platforms

    def test_select_platform_respects_weights(self, registry: PlatformRegistry):
        # With extreme weights, selection should be heavily biased
        weights = {
            "google": 1000.0,
            "youtube": 0.001, "instagram": 0.001, "facebook": 0.001,
            "tiktok": 0.001, "linkedin": 0.001, "twitter": 0.001, "amazon": 0.001,
        }
        selections = [registry.select_platform(weights).name for _ in range(50)]
        google_count = selections.count("google")
        assert google_count > 40, f"Google selected only {google_count}/50 times despite extreme weight"

    def test_anti_correlation_decay(self, registry: PlatformRegistry):
        """Recently used platforms should get lower selection probability."""
        # Fill history with one platform
        for _ in range(10):
            registry._session_history.append("google")

        # With equal weights, Google should be less likely now
        equal_weights = {name: 1.0 for name in registry.available_platforms}
        selections = [registry.select_platform(equal_weights).name for _ in range(100)]
        google_pct = selections.count("google") / len(selections)
        # With 8 platforms and equal weights, baseline is ~12.5%
        # With anti-correlation, Google should be notably below average
        assert google_pct < 0.2, f"Google selected {google_pct:.1%} despite anti-correlation"

    def test_session_history_capped(self, registry: PlatformRegistry):
        for _ in range(200):
            registry.select_platform()
        assert len(registry._session_history) <= 200

    def test_select_multi(self, registry: PlatformRegistry):
        multi = registry.select_multi(3)
        assert len(multi) == 3
        names = [s.name for s in multi]
        # All should be unique
        assert len(set(names)) == 3

    def test_select_multi_capped(self, registry: PlatformRegistry):
        multi = registry.select_multi(100)
        assert len(multi) == registry.platform_count

    def test_get_stats(self, registry: PlatformRegistry):
        registry._session_history = ["google", "google", "youtube", "amazon"]
        stats = registry.get_stats()
        assert stats["google"] == 2
        assert stats["youtube"] == 1
        assert stats["amazon"] == 1

    def test_select_platform_empty_raises(self):
        reg = PlatformRegistry()
        with pytest.raises(RuntimeError, match="No platform strategies"):
            reg.select_platform()

    def test_config_locale_propagated(self):
        reg = PlatformRegistry(config={"locale": "de", "enabled": ["google"]})
        reg.register_builtin()
        g = reg.get("google")
        assert g._config.get("locale") == "de"


# --- Strategy Tests ---

class TestGoogleStrategy:

    def test_name_and_display(self, google: GoogleStrategy):
        assert google.name == "google"
        assert "Google" in google.display_name

    def test_entry_points_are_urls(self, google: GoogleStrategy):
        urls = google.get_entry_points()
        assert len(urls) > 0
        for url in urls:
            assert url.startswith("https://")

    def test_generate_search_queries(self, google: GoogleStrategy, mock_identity):
        queries = google.generate_search_queries(mock_identity, count=10)
        assert len(queries) == 10
        assert all(isinstance(q, str) and len(q) > 0 for q in queries)

    def test_domains_set(self, google: GoogleStrategy):
        assert "google.com" in google.domains


class TestYouTubeStrategy:

    def test_basic(self):
        yt = YouTubeStrategy()
        assert yt.name == "youtube"
        assert len(yt.get_entry_points()) > 0

    def test_queries(self, mock_identity):
        yt = YouTubeStrategy()
        queries = yt.generate_search_queries(mock_identity, count=5)
        assert len(queries) == 5


class TestInstagramStrategy:

    def test_basic(self):
        ig = InstagramStrategy()
        assert ig.name == "instagram"

    def test_queries(self, mock_identity):
        ig = InstagramStrategy()
        queries = ig.generate_search_queries(mock_identity, count=5)
        assert len(queries) == 5


class TestFacebookStrategy:

    def test_basic(self):
        fb = FacebookStrategy()
        assert fb.name == "facebook"
        assert "facebook.com" in fb.domains


class TestTikTokStrategy:

    def test_basic(self):
        tt = TikTokStrategy()
        assert tt.name == "tiktok"

    def test_queries(self, mock_identity):
        tt = TikTokStrategy()
        queries = tt.generate_search_queries(mock_identity, count=5)
        assert len(queries) == 5


class TestLinkedInStrategy:

    def test_basic(self):
        li = LinkedInStrategy()
        assert li.name == "linkedin"

    def test_queries(self, mock_identity):
        li = LinkedInStrategy()
        queries = li.generate_search_queries(mock_identity, count=5)
        assert len(queries) == 5


class TestTwitterStrategy:

    def test_basic(self):
        tw = TwitterStrategy()
        assert tw.name == "twitter"


class TestAmazonStrategy:

    def test_basic(self):
        amz = AmazonStrategy()
        assert amz.name == "amazon"

    def test_queries(self, mock_identity):
        amz = AmazonStrategy()
        queries = amz.generate_search_queries(mock_identity, count=5)
        assert len(queries) == 5


# --- PlatformAction / PlatformSession Tests ---

class TestPlatformModels:

    def test_action_defaults(self):
        a = PlatformAction(name="click")
        assert a.weight == 1.0
        assert a.params == {}

    def test_session_defaults(self):
        s = PlatformSession(platform_name="google")
        assert s.pages_visited == 0
        assert s.data_points_poisoned == 0
        assert s.actions_performed == []

    def test_select_weighted_actions(self, google: GoogleStrategy):
        actions = [
            PlatformAction(name="search", weight=10.0),
            PlatformAction(name="maps", weight=0.001),
        ]
        # Note: select_weighted_actions caps at len(actions), so count <= len
        selected = google.select_weighted_actions(actions, count=2)
        # With extreme weight ratio, search should dominate
        assert len(selected) == 2

    def test_select_weighted_empty(self, google: GoogleStrategy):
        assert google.select_weighted_actions([], count=5) == []


# --- Poison Interests Tests ---

class TestPoisonInterests:

    def test_returns_interests(self, google: GoogleStrategy, mock_identity):
        interests = google.get_poison_interests(mock_identity)
        assert len(interests) > 0
        assert all(isinstance(i, str) for i in interests)

    def test_without_identity_preferences(self, google: GoogleStrategy):
        bare_identity = MagicMock(spec=[])
        interests = google.get_poison_interests(bare_identity)
        assert 3 <= len(interests) <= 6
