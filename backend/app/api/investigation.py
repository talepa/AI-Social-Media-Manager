"""
api/investigation.py

Director -> Specialists -> Evidence -> Synthesis pipeline.
Additive only -- mounted alongside /api/research/* and /api/session/*.

Endpoints:
  POST /api/investigation/runs          — sync full run
  POST /api/investigation/runs/stream   — SSE progress + final result
  GET  /api/investigation/runs/{run_id} — fetch stored run
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.investigation import (
    DirectorRequest,
    InvestigationRunResponse,
    InvestigationRunStatusResponse,
)
from app.services.investigation_runner import (
    iter_investigation_sse,
    run_investigation_sync,
)
from app.services.investigation_store import investigation_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigation", tags=["Investigation"])


@router.post("/runs", response_model=InvestigationRunResponse)
async def start_run(body: DirectorRequest):
    try:
        return run_investigation_sync(body)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("investigation run failed")
        raise HTTPException(status_code=500, detail=f"run failed: {exc}") from exc


@router.post("/runs/stream")
async def start_run_stream(body: DirectorRequest):
    """
    Server-Sent Events stream for a live investigation.

    event: accepted | progress | node | complete | error
    """
    return StreamingResponse(
        iter_investigation_sse(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}", response_model=InvestigationRunStatusResponse)
async def get_run(run_id: str):
    record = investigation_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return InvestigationRunStatusResponse(
        run_id=record.run_id,
        status=record.status,
        question=record.question,
        mode=record.mode,
        depth=record.depth,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=record.events,
        result=record.result,
        error=record.error,
    )
