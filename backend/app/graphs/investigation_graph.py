"""
graphs/investigation_graph.py

Phase 1 of the Director -> Specialists -> Evidence -> Synthesis pipeline
(see ~/Downloads/ATELIER_FINAL_ARCHITECTURE.md). This increment builds only
the Director step:

    START -> initialize_run -> director -> END

Later phases add specialist subgraphs, dynamic dispatch, evidence analysis,
synthesis, and citation validation as additional nodes on this same graph —
the typed state below is intentionally a superset (per the architecture
spec's ResearchState) so later increments extend it rather than replace it.

This is a new, additive graph. research_graph.py and session_graph.py are
untouched.
"""

from __future__ import annotations

from typing import Annotated, Dict, List, NotRequired, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.director import create_research_plan
from app.schemas.investigation import InvestigationDepth, InvestigationMode, InvestigationPlan


def _merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    return {**(left or {}), **(right or {})}


def _append_events(left: List[dict], right: List[dict]) -> List[dict]:
    return [*(left or []), *(right or [])]


class InvestigationState(TypedDict):
    run_id: str
    question: str
    mode: InvestigationMode
    depth: InvestigationDepth

    plan: NotRequired[Optional[dict]]  # InvestigationPlan.model_dump()

    tool_calls_used: NotRequired[int]
    llm_calls_used: NotRequired[int]

    errors: Annotated[Dict[str, str], _merge_dicts]
    events: Annotated[List[dict], _append_events]


def initialize_run_node(state: InvestigationState) -> dict:
    return {
        "events": [{"event_type": "run_started", "run_id": state["run_id"]}],
        "tool_calls_used": 0,
        "llm_calls_used": 0,
        "errors": {},
    }


def director_node(state: InvestigationState) -> dict:
    plan = create_research_plan(
        state["question"],
        mode=state.get("mode", "explore"),
        depth=state.get("depth", "standard"),
    )
    return {
        "plan": plan.model_dump(mode="json"),
        "llm_calls_used": state.get("llm_calls_used", 0) + 1,
        "events": [
            {
                "event_type": "plan_created",
                "run_id": state["run_id"],
                "required_specialists": plan.required_specialists,
                "sub_question_count": len(plan.sub_questions),
            }
        ],
    }


def build_investigation_graph():
    g = StateGraph(InvestigationState)
    g.add_node("initialize_run", initialize_run_node)
    g.add_node("director", director_node)

    g.add_edge(START, "initialize_run")
    g.add_edge("initialize_run", "director")
    g.add_edge("director", END)

    return g.compile(checkpointer=MemorySaver())


investigation_graph = build_investigation_graph()


def state_to_plan(state: dict) -> Optional[InvestigationPlan]:
    plan_dict = state.get("plan")
    if not plan_dict:
        return None
    return InvestigationPlan.model_validate(plan_dict)
