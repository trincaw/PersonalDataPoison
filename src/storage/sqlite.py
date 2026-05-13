from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from storage.models import Base

logger = logging.getLogger(__name__)


class SQLiteDatabase:

    def __init__(self, db_path: str | Path = "data/pdp.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self._session_factory = sessionmaker(bind=self._engine)

    def initialize(self) -> None:
        Base.metadata.create_all(self._engine)
        logger.info("Database initialized at %s", self._db_path)

    def get_session(self) -> Session:
        return self._session_factory()

    def drop_all(self) -> None:
        Base.metadata.drop_all(self._engine)
        logger.warning("All tables dropped")

    @property
    def engine(self):
        return self._engine

    def close(self) -> None:
        self._engine.dispose()
        logger.info("Database connection closed")
