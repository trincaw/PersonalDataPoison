import pytest
from timing.circadian import CircadianProfile
from timing.distributions import TimingDistribution
from datetime import datetime, timezone


class TestCircadianProfile:

    def test_default_multiplier_range(self):
        profile = CircadianProfile()
        mult = profile.activity_multiplier()
        assert 0.0 <= mult <= 1.0

    def test_night_low_activity(self):
        profile = CircadianProfile({"wake_hour": 7, "sleep_hour": 23, "noise": 0.0})
        dt = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)
        mult = profile.activity_multiplier(dt)
        assert mult < 0.2

    def test_midday_high_activity(self):
        profile = CircadianProfile({"wake_hour": 7, "sleep_hour": 23, "noise": 0.0})
        dt = datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc)
        mult = profile.activity_multiplier(dt)
        assert mult > 0.5

    def test_should_be_active(self):
        profile = CircadianProfile({"wake_hour": 7, "sleep_hour": 23, "noise": 0.0})
        dt_day = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        dt_night = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)
        assert profile.should_be_active(dt_day)
        assert not profile.should_be_active(dt_night)

    def test_suggested_delay(self):
        profile = CircadianProfile()
        delay = profile.suggested_delay(10.0)
        assert delay > 0


class TestTimingDistribution:

    def test_gaussian_positive(self):
        for _ in range(100):
            assert TimingDistribution.gaussian(5.0, 2.0) >= 0.1

    def test_exponential_positive(self):
        for _ in range(100):
            assert TimingDistribution.exponential(5.0) >= 0.1

    def test_human_keystroke(self):
        delay = TimingDistribution.human_keystroke(60)
        assert delay > 0

    def test_page_dwell_time(self):
        dwell = TimingDistribution.page_dwell_time(30)
        assert dwell >= 2.0
