import pytest
from identity.generator import IdentityGenerator
from identity.models import Identity, DeviceProfile


class TestIdentityGenerator:

    def setup_method(self):
        self.generator = IdentityGenerator()

    def test_create_returns_identity(self):
        identity = self.generator.create()
        assert isinstance(identity, Identity)
        assert identity.alias.startswith("id-")
        assert identity.persona_name != ""

    def test_create_with_locale(self):
        identity = self.generator.create(locale="it-IT")
        assert identity.device.locale == "it-IT"
        assert identity.device.timezone.startswith("Europe/")

    def test_create_with_os(self):
        identity = self.generator.create(os_name="Linux")
        assert identity.device.os_name == "Linux"
        assert "Linux" in identity.device.platform

    def test_create_batch(self):
        batch = self.generator.create_batch(5)
        assert len(batch) == 5
        aliases = {i.alias for i in batch}
        assert len(aliases) == 5  # all unique

    def test_user_agent_matches_os(self):
        identity = self.generator.create(os_name="Windows")
        assert "Windows NT" in identity.device.user_agent

        identity = self.generator.create(os_name="macOS")
        assert "Macintosh" in identity.device.user_agent

    def test_device_profile_has_all_fields(self):
        identity = self.generator.create()
        device = identity.device
        assert device.screen_width > 0
        assert device.screen_height > 0
        assert device.hardware_concurrency > 0
        assert device.device_memory > 0
        assert device.timezone
        assert device.locale

    def test_fingerprint_hash_consistent(self):
        identity = self.generator.create()
        h1 = identity.device.fingerprint_hash()
        h2 = identity.device.fingerprint_hash()
        assert h1 == h2
        assert len(h1) == 16
