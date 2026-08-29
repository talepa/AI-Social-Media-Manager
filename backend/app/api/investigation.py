"""
api/investigation.py

Phase 1 of the Director -> Specialists -> Evidence -> Synthesis pipeline.
Additive only -- mounted alongside /api/research/* and /api/session/*,
which are untouched.

Deliberately uses /api/investigation/* rather than the spec's literal
/api/research/runs: /api/research/* is already a large, differently-shaped
surface (multi/synthesize/chat/expand/plan/tavily/report/exports), so a
separate prefix keeps this new pipeline unambiguous while it's built out.
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.graphs.investigation_graph import investigation_graph, state_to_plan
from app.schemas.investigation import DirectorRequest, DirectorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigation", tags=["Investigation"])


@router.post("/runs", response_model=DirectorResponse)
async def start_run(body: DirectorRequest):
    run_id = str(uuid.uuid4())
    try:
        final = investigation_graph.invoke(
            {
                "run_id": run_id,
                "question": body.question.strip(),
                "mode": body.mode,
                "depth": body.depth,
                "errors": {},
                "events": [],
            },
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception as exc:
        logger.exception("investigation run failed")
        raise HTTPException(status_code=500, detail=f"run failed: {exc}") from exc

    plan = state_to_plan(final)
    if plan is None:
        raise HTTPException(status_code=500, detail="director produced no plan")

    return DirectorResponse(run_id=run_id, plan=plan)
