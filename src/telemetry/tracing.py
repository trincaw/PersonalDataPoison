from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionTracer:

    def __init__(self, traces_dir: str | Path = "data/telemetry/traces") -> None:
        self._dir = Path(traces_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._current_trace: list[dict[str, Any]] = []
        self._session_id: str | None = None

    def start_trace(self, session_id: str) -> None:
        self._session_id = session_id
        self._current_trace = []
        self._add_event("trace.started")

    def add_event(self, event_name: str, data: dict[str, Any] | None = None) -> None:
        self._add_event(event_name, data)

    def end_trace(self) -> Path | None:
        if not self._session_id:
            return None

        self._add_event("trace.ended")
        path = self._dir / f"trace_{self._session_id}_{self._timestamp()}.json"
        path.write_text(json.dumps(self._current_trace, indent=2, default=str))

        logger.debug("Trace saved to %s (%d events)", path, len(self._current_trace))
        result = path
        self._current_trace = []
        self._session_id = None
        return result

    def _add_event(self, name: str, data: dict[str, Any] | None = None) -> None:
        self._current_trace.append({
            "event": name,
            "session_id": self._session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        })

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def list_traces(self, limit: int = 50) -> list[Path]:
        traces = sorted(self._dir.glob("trace_*.json"), reverse=True)
        return traces[:limit]
