"""
api/session.py

Checkpointed session API (increment 1 of the LangGraph migration). Additive
only — mounted alongside the existing /api/research/* endpoints in main.py,
which are untouched.

Endpoints:
  POST /api/session/start                 — start a session, run the initial gather
  POST /api/session/{thread_id}/message   — send a chat turn; may pause for approval
  POST /api/session/{thread_id}/decision  — resume a paused turn with accept/decline
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException
from langgraph.types import Command

from app.graphs.session_graph import _state_to_result, session_graph
from app.schemas.session import (
    InterruptPayload,
    SessionDecisionRequest,
    SessionMessageRequest,
    SessionStartRequest,
    SessionStartResponse,
    SessionTurnResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["Session"])


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _paused_response(thread_id: str, snapshot) -> SessionTurnResponse:
    task = snapshot.tasks[0]
    payload = task.interrupts[0].value
    return SessionTurnResponse(
        thread_id=thread_id,
        status="paused",
        interrupt=InterruptPayload(**payload),
        run_mode=snapshot.values.get("run_mode", "research"),
    )


def _answered_response(thread_id: str, final: dict) -> SessionTurnResponse:
    research = _state_to_result(final)
    return SessionTurnResponse(
        thread_id=thread_id,
        status="answered",
        answer=final.get("last_answer"),
        research=research,
        plan=final.get("last_plan"),
        plan_markdown=final.get("last_plan_markdown"),
        run_mode=final.get("run_mode", "research"),
    )


@router.post("/start", response_model=SessionStartResponse)
async def start_session(body: SessionStartRequest):
    thread_id = str(uuid.uuid4())
    try:
        final = session_graph.invoke(
            {
                "topic": body.topic.strip(),
                "run_mode": body.run_mode,
                "turn_kind": "gather",
                "errors": {},
                "history": [],
            },
            config=_config(thread_id),
        )
    except Exception as exc:
        logger.exception("session start failed")
        raise HTTPException(status_code=500, detail=f"session start failed: {exc}") from exc

    research = _state_to_result(final)
    return SessionStartResponse(
        thread_id=thread_id,
        research=research,
        opening_message=final.get("last_answer") or "Research complete.",
        run_mode=final.get("run_mode", body.run_mode),
        routing=research.routing,
    )


@router.post("/{thread_id}/message", response_model=SessionTurnResponse)
async def send_message(thread_id: str, body: SessionMessageRequest):
    config = _config(thread_id)
    snapshot = session_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="unknown thread_id")
    if snapshot.next:
        raise HTTPException(
            status_code=409,
            detail="session is paused awaiting a decision; call /decision first",
        )

    try:
        final = session_graph.invoke(
            {
                "turn_kind": "chat",
                "question": body.question.strip(),
                "auto_expand": body.auto_expand,
                "auto_mode_switch": body.auto_mode_switch,
            },
            config=config,
        )
    except Exception as exc:
        logger.exception("session message failed")
        raise HTTPException(status_code=500, detail=f"message failed: {exc}") from exc

    state_after = session_graph.get_state(config)
    if state_after.next:
        return _paused_response(thread_id, state_after)
    return _answered_response(thread_id, final)


@router.post("/{thread_id}/decision", response_model=SessionTurnResponse)
async def decide(thread_id: str, body: SessionDecisionRequest):
    config = _config(thread_id)
    snapshot = session_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="unknown thread_id")
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="session is not currently paused")

    try:
        final = session_graph.invoke(
            Command(resume={"decision": body.decision, "accept": body.decision == "accept"}),
            config=config,
        )
    except Exception as exc:
        logger.exception("session decision failed")
        raise HTTPException(status_code=500, detail=f"decision failed: {exc}") from exc

    return _answered_response(thread_id, final)
