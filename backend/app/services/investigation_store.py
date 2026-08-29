"""
services/investigation_store.py

Investigation run store for SSE + GET-by-id.

  - In-memory by default
  - Postgres when DATABASE_URL is reachable (survives process restart)

Env:
  INVESTIGATION_STORE=auto|postgres|memory   (default: auto)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel, Field

from app.schemas.investigation import InvestigationRunResponse

logger = logging.getLogger(__name__)

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


class InvestigationRunStoreProtocol(Protocol):
    def create(
        self,
        run_id: str,
        *,
        question: str,
        mode: str,
        depth: str,
    ) -> StoredInvestigationRun: ...

    def append_events(self, run_id: str, events: List[dict]) -> None: ...

    def complete(self, run_id: str, result: InvestigationRunResponse) -> None: ...

    def fail(self, run_id: str, error: str) -> None: ...

    def get(self, run_id: str) -> Optional[StoredInvestigationRun]: ...

    def list_recent(self, limit: int = 20) -> List[StoredInvestigationRun]: ...


class InvestigationRunStore:
    """In-process store (lost on restart)."""

    def __init__(self, *, max_runs: int = 100):
        self._lock = threading.Lock()
        self._runs: Dict[str, StoredInvestigationRun] = {}
        self._max_runs = max_runs
        self.backend = "memory"

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


_SETUP_SQL = (
    """
    CREATE TABLE IF NOT EXISTS investigation_runs (
        run_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        question TEXT NOT NULL DEFAULT '',
        mode TEXT NOT NULL DEFAULT 'explore',
        depth TEXT NOT NULL DEFAULT 'standard',
        created_at DOUBLE PRECISION NOT NULL,
        updated_at DOUBLE PRECISION NOT NULL,
        events JSONB NOT NULL DEFAULT '[]'::jsonb,
        result JSONB,
        error TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS investigation_runs_updated_at_idx
        ON investigation_runs (updated_at DESC)
    """,
)


class PostgresInvestigationRunStore:
    """Durable investigation run store backed by PostgreSQL."""

    def __init__(self, database_url: str):
        import psycopg

        self.backend = "postgres"
        self._url = database_url.replace("postgres://", "postgresql://", 1)
        self._lock = threading.Lock()
        # Verify connectivity + schema
        with psycopg.connect(self._url, connect_timeout=3) as conn:
            for stmt in _SETUP_SQL:
                conn.execute(stmt)
            conn.commit()

    def _connect(self):
        import psycopg

        return psycopg.connect(self._url, connect_timeout=3)

    def create(
        self,
        run_id: str,
        *,
        question: str,
        mode: str,
        depth: str,
    ) -> StoredInvestigationRun:
        now = time.time()
        events = [{"event_type": "run_accepted", "run_id": run_id}]
        record = StoredInvestigationRun(
            run_id=run_id,
            status="running",
            question=question,
            mode=mode,
            depth=depth,
            created_at=now,
            updated_at=now,
            events=events,
        )
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO investigation_runs
                      (run_id, status, question, mode, depth, created_at, updated_at, events)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id) DO UPDATE SET
                      status = EXCLUDED.status,
                      question = EXCLUDED.question,
                      mode = EXCLUDED.mode,
                      depth = EXCLUDED.depth,
                      updated_at = EXCLUDED.updated_at,
                      events = EXCLUDED.events
                    """,
                    (
                        run_id,
                        "running",
                        question,
                        mode,
                        depth,
                        now,
                        now,
                        json.dumps(events),
                    ),
                )
                conn.commit()
        return record

    def append_events(self, run_id: str, events: List[dict]) -> None:
        if not events:
            return
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE investigation_runs
                    SET events = COALESCE(events, '[]'::jsonb) || %s::jsonb,
                        updated_at = %s
                    WHERE run_id = %s
                    """,
                    (json.dumps(events), time.time(), run_id),
                )
                conn.commit()

    def complete(self, run_id: str, result: InvestigationRunResponse) -> None:
        payload = result.model_dump(mode="json")
        events = list(result.events or [])
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE investigation_runs
                    SET status = 'completed',
                        result = %s::jsonb,
                        events = %s::jsonb,
                        error = NULL,
                        updated_at = %s
                    WHERE run_id = %s
                    """,
                    (json.dumps(payload), json.dumps(events), time.time(), run_id),
                )
                conn.commit()

    def fail(self, run_id: str, error: str) -> None:
        fail_event = {"event_type": "run_failed", "run_id": run_id, "error": error}
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE investigation_runs
                    SET status = 'failed',
                        error = %s,
                        events = COALESCE(events, '[]'::jsonb) || %s::jsonb,
                        updated_at = %s
                    WHERE run_id = %s
                    """,
                    (error, json.dumps([fail_event]), time.time(), run_id),
                )
                conn.commit()

    def get(self, run_id: str) -> Optional[StoredInvestigationRun]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, status, question, mode, depth,
                       created_at, updated_at, events, result, error
                FROM investigation_runs WHERE run_id = %s
                """,
                (run_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_recent(self, limit: int = 20) -> List[StoredInvestigationRun]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, status, question, mode, depth,
                       created_at, updated_at, events, result, error
                FROM investigation_runs
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row) -> StoredInvestigationRun:
        (
            run_id,
            status,
            question,
            mode,
            depth,
            created_at,
            updated_at,
            events,
            result,
            error,
        ) = row
        if isinstance(events, str):
            events = json.loads(events)
        parsed_result = None
        if result:
            if isinstance(result, str):
                result = json.loads(result)
            parsed_result = InvestigationRunResponse.model_validate(result)
        return StoredInvestigationRun(
            run_id=run_id,
            status=status,
            question=question or "",
            mode=mode or "explore",
            depth=depth or "standard",
            created_at=float(created_at),
            updated_at=float(updated_at),
            events=list(events or []),
            result=parsed_result,
            error=error,
        )


def _build_store() -> InvestigationRunStoreProtocol:
    mode = (os.getenv("INVESTIGATION_STORE") or "auto").strip().lower()
    if mode == "memory":
        logger.info("investigation store: memory (forced)")
        return InvestigationRunStore()

    url = (os.getenv("DATABASE_URL") or "").strip()
    if mode == "postgres" or (mode == "auto" and url):
        try:
            store = PostgresInvestigationRunStore(url)
            logger.info("investigation store: postgres")
            return store
        except Exception as exc:
            if mode == "postgres":
                logger.exception(
                    "Postgres investigation store required but failed — using memory: %s",
                    exc,
                )
            else:
                logger.warning(
                    "Postgres investigation store unavailable (%s) — using memory",
                    exc,
                )

    logger.info("investigation store: memory")
    return InvestigationRunStore()


investigation_store: InvestigationRunStoreProtocol = _build_store()


def reset_investigation_store_for_tests(
    store: Optional[InvestigationRunStoreProtocol] = None,
) -> InvestigationRunStoreProtocol:
    """Replace the module singleton (tests)."""
    global investigation_store
    investigation_store = store or InvestigationRunStore()
    return investigation_store
