import pytest
from pathlib import Path
from config.loader import ConfigLoader


class TestConfigLoader:

    def test_load_base_config(self):
        config = ConfigLoader.load("configs/base.yaml")
        assert isinstance(config, dict)
        assert "general" in config
        assert "browser" in config
        assert "timing" in config

    def test_load_missing_file(self):
        config = ConfigLoader.load("nonexistent.yaml")
        assert config == {}

    def test_load_with_profile(self):
        loader = ConfigLoader("configs")
        config = loader.load_with_profile("desktop")
        assert config["browser"]["headless"] is False

    def test_profile_overrides_base(self):
        loader = ConfigLoader("configs")
        base = loader.load_with_profile()
        desktop = loader.load_with_profile("desktop")
        # Desktop overrides headless to False
        assert desktop["browser"]["headless"] is False

    def test_load_logging_config(self):
        loader = ConfigLoader("configs")
        log_config = loader.load_logging_config()
        assert "logging" in log_config
