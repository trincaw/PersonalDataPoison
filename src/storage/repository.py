from __future__ import annotations

import logging
from typing import Any, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.models import Base

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class Repository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Base) -> None:
        self._session.add(entity)
        self._session.commit()
        logger.debug("Saved %s", type(entity).__name__)

    def save_all(self, entities: list[Base]) -> None:
        self._session.add_all(entities)
        self._session.commit()

    def get(self, model: Type[T], entity_id: Any) -> T | None:
        return self._session.get(model, entity_id)

    def find_all(self, model: Type[T], limit: int = 100) -> list[T]:
        stmt = select(model).limit(limit)
        return list(self._session.scalars(stmt).all())

    def find_by(self, model: Type[T], **filters) -> list[T]:
        stmt = select(model)
        for attr, value in filters.items():
            stmt = stmt.where(getattr(model, attr) == value)
        return list(self._session.scalars(stmt).all())

    def delete(self, entity: Base) -> None:
        self._session.delete(entity)
        self._session.commit()

    def count(self, model: Type[T]) -> int:
        stmt = select(model)
        return len(list(self._session.scalars(stmt).all()))

    def flush(self) -> None:
        self._session.flush()

    def rollback(self) -> None:
        self._session.rollback()