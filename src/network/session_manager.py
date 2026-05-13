from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    identity_id: UUID
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pages_visited: int = 0
    bytes_transferred: int = 0
    proxy_url: str | None = None
    context: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionManager:

    def __init__(self) -> None:
        self._active: dict[UUID, SessionInfo] = {}
        self._completed: list[SessionInfo] = []
        self._max_completed = 100

    def register(self, identity_id: UUID, context: Any = None, proxy_url: str | None = None) -> SessionInfo:
        session = SessionInfo(
            identity_id=identity_id,
            context=context,
            proxy_url=proxy_url,
        )
        self._active[identity_id] = session
        logger.info("Registered session for identity %s", identity_id)
        return session

    def get(self, identity_id: UUID) -> SessionInfo | None:
        return self._active.get(identity_id)

    def update_pages(self, identity_id: UUID, count: int = 1) -> None:
        if session := self._active.get(identity_id):
            session.pages_visited += count

    def complete(self, identity_id: UUID) -> SessionInfo | None:
        session = self._active.pop(identity_id, None)
        if session:
            self._completed.append(session)
            if len(self._completed) > self._max_completed:
                self._completed = self._completed[-self._max_completed:]
            logger.info("Completed session for %s (%d pages)", identity_id, session.pages_visited)
        return session

    @property
    def active_sessions(self) -> dict[UUID, SessionInfo]:
        return dict(self._active)

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def completed_count(self) -> int:
        return len(self._completed)