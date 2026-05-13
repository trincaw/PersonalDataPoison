from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:

    def __init__(self, base_dir: str | Path = "configs") -> None:
        self._base_dir = Path(base_dir)

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        path = Path(path)
        if not path.exists():
            logger.warning("Config file not found: %s", path)
            return {}

        with path.open("r") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    def load_with_profile(self, profile_name: str | None = None) -> dict[str, Any]:
        base_config = self.load(self._base_dir / "base.yaml")

        if profile_name:
            profile_path = self._base_dir / "profiles" / f"{profile_name}.yaml"
            profile_config = self.load(profile_path)
            base_config = _deep_merge(base_config, profile_config)
            logger.info("Loaded profile: %s", profile_name)

        base_config = self._apply_env_overrides(base_config)
        return base_config

    def load_logging_config(self) -> dict[str, Any]:
        return self.load(self._base_dir / "logging.yaml")

    @staticmethod
    def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
        env_prefix = "PDP_"
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_path = key[len(env_prefix):].lower().split("__")
                current = config
                for part in config_path[:-1]:
                    current = current.setdefault(part, {})
                current[config_path[-1]] = _parse_env_value(value)
        return config


def _parse_env_value(value: str) -> Any:
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value