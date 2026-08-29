"""
services/investigation_runner.py

Shared helpers to run the investigation graph (sync or streaming) and
map graph state → InvestigationRunResponse.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Generator, List, Optional

from app.graphs.investigation_graph import (
    investigation_graph,
    state_to_evidence,
    state_to_findings,
    state_to_plan,
    state_to_report,
    state_to_sources,
    state_to_specialist_results,
    state_to_verification,
)
from app.schemas.investigation import DirectorRequest, InvestigationRunResponse
from app.services import investigation_store as store_mod

logger = logging.getLogger(__name__)


def initial_state(run_id: str, body: DirectorRequest) -> dict:
    return {
        "run_id": run_id,
        "question": body.question.strip(),
        "mode": body.mode,
        "depth": body.depth,
        "use_llm": bool(body.use_llm),
        "errors": {},
        "events": [],
    }


def config_for(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def response_from_state(run_id: str, state: dict) -> InvestigationRunResponse:
    plan = state_to_plan(state)
    if plan is None:
        raise ValueError("director produced no plan")
    return InvestigationRunResponse(
        run_id=run_id,
        plan=plan,
        specialist_results=state_to_specialist_results(state),
        sources=state_to_sources(state),
        findings=state_to_findings(state),
        evidence=state_to_evidence(state),
        report=state_to_report(state),
        verification=state_to_verification(state),
        tool_calls_used=int(state.get("tool_calls_used") or 0),
        llm_calls_used=int(state.get("llm_calls_used") or 0),
        use_llm=bool(state.get("use_llm", False)),
        errors=dict(state.get("errors") or {}),
        events=list(state.get("events") or []),
    )


def run_investigation_sync(body: DirectorRequest) -> InvestigationRunResponse:
    run_id = str(uuid.uuid4())
    store_mod.investigation_store.create(
        run_id,
        question=body.question.strip(),
        mode=body.mode,
        depth=body.depth,
    )
    try:
        final = investigation_graph.invoke(
            initial_state(run_id, body),
            config=config_for(run_id),
        )
        result = response_from_state(run_id, final)
        store_mod.investigation_store.complete(run_id, result)
        return result
    except Exception as exc:
        logger.exception("investigation run failed")
        store_mod.investigation_store.fail(run_id, str(exc))
        raise


def _sse(event: str, data: Any) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def iter_investigation_sse(
    body: DirectorRequest,
) -> Generator[str, None, None]:
    """
    Stream investigation progress as Server-Sent Events.

    Events:
      - accepted: run accepted (run_id)
      - node: graph node finished (node name + summary)
      - progress: domain events from graph state (plan_created, etc.)
      - complete: full InvestigationRunResponse
      - error: failure payload
    """
    run_id = str(uuid.uuid4())
    store_mod.investigation_store.create(
        run_id,
        question=body.question.strip(),
        mode=body.mode,
        depth=body.depth,
    )
    yield _sse(
        "accepted",
        {
            "run_id": run_id,
            "question": body.question.strip(),
            "mode": body.mode,
            "depth": body.depth,
            "use_llm": bool(body.use_llm),
        },
    )

    seen_events = 0
    last_state: Optional[dict] = None
    try:
        for state in investigation_graph.stream(
            initial_state(run_id, body),
            config=config_for(run_id),
            stream_mode="values",
        ):
            last_state = state
            events = list(state.get("events") or [])
            new_events = events[seen_events:]
            seen_events = len(events)
            if new_events:
                store_mod.investigation_store.append_events(run_id, new_events)
                for ev in new_events:
                    yield _sse("progress", ev)

            # Infer which phase just advanced from event types / state keys
            phase = _infer_phase(state, new_events)
            yield _sse(
                "node",
                {
                    "run_id": run_id,
                    "phase": phase,
                    "tool_calls_used": state.get("tool_calls_used", 0),
                    "llm_calls_used": state.get("llm_calls_used", 0),
                    "use_llm": bool(state.get("use_llm", False)),
                    "has_plan": bool(state.get("plan")),
                    "finding_count": len(state.get("findings") or []),
                    "claim_count": len((state.get("evidence") or {}).get("claims") or [])
                    if isinstance(state.get("evidence"), dict)
                    else 0,
                    "has_report": bool(state.get("report")),
                    "error_count": len(state.get("errors") or {}),
                },
            )

        if last_state is None:
            raise RuntimeError("investigation stream produced no state")

        result = response_from_state(run_id, last_state)
        store_mod.investigation_store.complete(run_id, result)
        yield _sse("complete", result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("investigation stream failed")
        store_mod.investigation_store.fail(run_id, str(exc))
        yield _sse("error", {"run_id": run_id, "error": str(exc)})


def _infer_phase(state: dict, new_events: List[dict]) -> str:
    for ev in reversed(new_events):
        et = ev.get("event_type") or ""
        if et:
            return str(et)
    if state.get("report"):
        return "synthesis"
    if state.get("evidence"):
        return "evidence_analyst"
    if state.get("findings"):
        return "specialists"
    if state.get("plan"):
        return "director"
    return "initialize_run"
