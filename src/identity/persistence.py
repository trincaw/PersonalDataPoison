from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from identity.models import Identity

logger = logging.getLogger(__name__)


class IdentityStore:

    def __init__(self, storage_dir: str | Path = "data/identities") -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[UUID, Identity] = {}

    def save(self, identity: Identity) -> None:
        path = self._dir / f"{identity.id}.json"
        path.write_text(identity.model_dump_json(indent=2))
        self._cache[identity.id] = identity
        logger.debug("Saved identity %s to %s", identity.alias, path)

    def load(self, identity_id: UUID) -> Identity | None:
        if identity_id in self._cache:
            return self._cache[identity_id]

        path = self._dir / f"{identity_id}.json"
        if not path.exists():
            return None

        identity = Identity.model_validate_json(path.read_text())
        self._cache[identity.id] = identity
        return identity

    def load_all(self) -> list[Identity]:
        identities = []
        for path in self._dir.glob("*.json"):
            try:
                identity = Identity.model_validate_json(path.read_text())
                self._cache[identity.id] = identity
                identities.append(identity)
            except Exception:
                logger.exception("Failed to load identity from %s", path)
        return identities

    def delete(self, identity_id: UUID) -> bool:
        path = self._dir / f"{identity_id}.json"
        self._cache.pop(identity_id, None)
        if path.exists():
            path.unlink()
            return True
        return False

    def find_by_alias(self, alias: str) -> Identity | None:
        for identity in self.load_all():
            if identity.alias == alias:
                return identity
        return None

    def count(self) -> int:
        return len(list(self._dir.glob("*.json")))
