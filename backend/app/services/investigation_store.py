"""
services/investigation_store.py

In-process store for investigation runs. Enough for SSE + GET-by-id while
the graph still uses MemorySaver. Not durable across process restarts.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.investigation import InvestigationRunResponse

RunStatus = Literal["running", "completed", "failed"]


class StoredInvestigationRun(BaseModel):
    run_id: str
    status: RunStatus
    question: str = ""
    mode: str = "explore"
    depth: str = "standard"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    events: List[dict] = Field(default_factory=list)
    result: Optional[InvestigationRunResponse] = None
    error: Optional[str] = None


class InvestigationRunStore:
    def __init__(self, *, max_runs: int = 100):
        self._lock = threading.Lock()
        self._runs: Dict[str, StoredInvestigationRun] = {}
        self._max_runs = max_runs

    def create(
        self,
        run_id: str,
        *,
        question: str,
        mode: str,
        depth: str,
    ) -> StoredInvestigationRun:
        record = StoredInvestigationRun(
            run_id=run_id,
            status="running",
            question=question,
            mode=mode,
            depth=depth,
            events=[{"event_type": "run_accepted", "run_id": run_id}],
        )
        with self._lock:
            self._runs[run_id] = record
            self._prune_locked()
        return record

    def append_events(self, run_id: str, events: List[dict]) -> None:
        if not events:
            return
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.events.extend(events)
            rec.updated_at = time.time()

    def complete(self, run_id: str, result: InvestigationRunResponse) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.status = "completed"
            rec.result = result
            rec.events = list(result.events or rec.events)
            rec.updated_at = time.time()

    def fail(self, run_id: str, error: str) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.status = "failed"
            rec.error = error
            rec.events.append(
                {"event_type": "run_failed", "run_id": run_id, "error": error}
            )
            rec.updated_at = time.time()

    def get(self, run_id: str) -> Optional[StoredInvestigationRun]:
        with self._lock:
            rec = self._runs.get(run_id)
            return rec.model_copy(deep=True) if rec else None

    def list_recent(self, limit: int = 20) -> List[StoredInvestigationRun]:
        with self._lock:
            items = sorted(
                self._runs.values(),
                key=lambda r: r.updated_at,
                reverse=True,
            )
            return [r.model_copy(deep=True) for r in items[:limit]]

    def _prune_locked(self) -> None:
        if len(self._runs) <= self._max_runs:
            return
        ordered = sorted(self._runs.values(), key=lambda r: r.updated_at)
        for old in ordered[: max(0, len(self._runs) - self._max_runs)]:
            self._runs.pop(old.run_id, None)


investigation_store = InvestigationRunStore()
