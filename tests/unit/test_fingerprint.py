import pytest
from fingerprint.consistency import FingerprintConsistencyValidator
from fingerprint.validators import FingerprintFieldValidator
from fingerprint.manager import FingerprintManager
from identity.generator import IdentityGenerator
from identity.models import DeviceProfile


class TestFingerprintConsistency:

    def setup_method(self):
        self.validator = FingerprintConsistencyValidator()

    def _make_device(self, **overrides) -> DeviceProfile:
        defaults = {
            "os_name": "Windows",
            "os_version": "10",
            "browser_name": "Chromium",
            "browser_version": "120.0",
            "screen_width": 1920,
            "screen_height": 1080,
            "timezone": "Europe/Rome",
            "locale": "it-IT",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "platform": "Win32",
        }
        defaults.update(overrides)
        return DeviceProfile(**defaults)

    def test_valid_profile(self):
        device = self._make_device()
        result = self.validator.validate(device)
        assert result.valid
        assert len(result.issues) == 0

    def test_timezone_locale_mismatch(self):
        device = self._make_device(timezone="Europe/Rome", locale="ja-JP")
        result = self.validator.validate(device)
        assert not result.valid
        assert any("inconsistent" in i.lower() for i in result.issues)

    def test_platform_os_mismatch(self):
        device = self._make_device(os_name="Windows", platform="MacIntel")
        result = self.validator.validate(device)
        assert not result.valid

    def test_user_agent_os_mismatch(self):
        device = self._make_device(os_name="macOS", user_agent="Mozilla/5.0 (Windows NT 10.0)")
        result = self.validator.validate(device)
        assert not result.valid


class TestFingerprintFieldValidator:

    def setup_method(self):
        self.validator = FingerprintFieldValidator()

    def test_valid_timezone(self):
        assert self.validator.validate_timezone("Europe/Rome")
        assert self.validator.validate_timezone("America/New_York")

    def test_invalid_timezone(self):
        assert not self.validator.validate_timezone("Invalid")
        assert not self.validator.validate_timezone("")

    def test_valid_locale(self):
        assert self.validator.validate_locale("it-IT")
        assert self.validator.validate_locale("en")

    def test_invalid_locale(self):
        assert not self.validator.validate_locale("INVALID")
        assert not self.validator.validate_locale("")

    def test_valid_screen(self):
        assert self.validator.validate_screen(1920, 1080)

    def test_invalid_screen(self):
        assert not self.validator.validate_screen(0, 0)
        assert not self.validator.validate_screen(99999, 99999)


class TestFingerprintManager:

    def test_generate_consistent(self):
        generator = IdentityGenerator()
        manager = FingerprintManager(generator)
        identity = manager.generate_consistent_identity()
        assert identity is not None
        assert manager.known_fingerprints >= 1

    def test_unique_fingerprints(self):
        generator = IdentityGenerator()
        manager = FingerprintManager(generator)
        ids = [manager.generate_consistent_identity() for _ in range(5)]
        hashes = {i.device.fingerprint_hash() for i in ids}
        assert len(hashes) == 5
