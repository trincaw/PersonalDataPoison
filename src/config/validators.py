from __future__ import annotations

import logging
from typing import Any

from jsonschema import validate, ValidationError

from config.schema import CONFIG_SCHEMA

logger = logging.getLogger(__name__)


class ConfigValidator:

    def __init__(self, schema: dict[str, Any] | None = None) -> None:
        self._schema = schema or CONFIG_SCHEMA

    def validate(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        try:
            validate(instance=config, schema=self._schema)
        except ValidationError as e:
            errors.append(f"{e.json_path}: {e.message}")
            logger.warning("Config validation error: %s", e.message)
        return errors

    def is_valid(self, config: dict[str, Any]) -> bool:
        return len(self.validate(config)) == 0

    @staticmethod
    def check_required_fields(config: dict[str, Any]) -> list[str]:
        missing = []
        if not config.get("general"):
            missing.append("general section missing")
        if not config.get("browser"):
            missing.append("browser section missing")
        return missing
