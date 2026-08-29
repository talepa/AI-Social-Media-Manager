"""
graphs/session_graph.py

Increment 1 of the LangGraph migration: a single checkpointed graph that owns
a whole research session (gather, then repeated chat turns), instead of the
gather-only graph in research_graph.py plus plain-function chat handling in
research_chat.py.

Additive only — nothing in research_graph.py's or research_chat.py's existing
behavior changes. This graph imports and reuses their node functions / decision
logic verbatim.

Turn lifecycle on one thread_id:
  - First turn ("gather"): route -> [tavily|news|papers|github]* -> gather -> build_result -> END
  - Later turns ("chat"): chat -> (may pause via interrupt()) -> END

Human-in-the-loop: chat_node calls interrupt(...) when it wants to expand
research with more sources, or switch run_mode, instead of returning an
"action" field for the client to poll and re-request. The caller resumes with
Command(resume=...).

Checkpointer: MemorySaver (in-process only). Known limits, acceptable for this
increment: state is lost on server restart, and this only works correctly with
a single uvicorn worker process (see backend/app/main.py comment).
"""

from __future__ import annotations

from typing import Annotated, Dict, List, Literal, NotRequired, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.graphs.research_graph import (
    _merge_dicts,
    gather_node,
    github_node,
    news_node,
    papers_node,
    state_to_multi_source_result,
    tavily_node,
)
from app.schemas.research import MultiSourceResearchResult, ResearchItem, ResearchRoutingPlan
from app.services.plan_synthesizer import synthesize_plan
from app.services.research_chat import (
    _PLAN_RE,
    ChatTurn,
    analyze_followup,
    answer_from_context,
    build_opening_summary,
    detect_mode_switch,
    expand_research,
)
from app.services.topic_router import route_topic


def _dump_items(items: object) -> List[dict]:
    """Convert a list of ResearchItem (or dicts) into plain dicts.

    Kept as dicts in checkpointed state rather than ResearchItem instances —
    langgraph's default serializer warns on unregistered pydantic types when a
    checkpointer is attached, and _normalize_items()/state_to_multi_source_result()
    already accept plain dicts, so there is no reconstruction cost.
    """
    out: List[dict] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, ResearchItem):
            out.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            out.append(item)
    return out


class SessionState(TypedDict):
    # --- shared with research_graph.py's MultiSourceState (reused nodes need these) ---
    topic: str
    search_query: NotRequired[Optional[str]]
    papers_search_query: NotRequired[Optional[str]]
    limit: NotRequired[int]
    with_report: NotRequired[bool]
    category: NotRequired[Optional[str]]
    sources: NotRequired[List[str]]
    tavily_results: NotRequired[List[dict]]
    news_results: NotRequired[List[dict]]
    papers_results: NotRequired[List[dict]]
    github_results: NotRequired[List[dict]]
    tavily_answer: NotRequired[Optional[str]]
    media_urls: NotRequired[List[str]]
    errors: Annotated[Dict[str, str], _merge_dicts]

    # --- session bookkeeping (new) ---
    run_mode: NotRequired[str]
    routing: NotRequired[Optional[dict]]
    sources_used: NotRequired[List[str]]
    turn_kind: NotRequired[Literal["gather", "chat"]]
    question: NotRequired[Optional[str]]
    history: NotRequired[List[ChatTurn]]
    auto_expand: NotRequired[bool]
    auto_mode_switch: NotRequired[bool]
    last_answer: NotRequired[Optional[str]]
    last_plan: NotRequired[Optional[dict]]
    last_plan_markdown: NotRequired[Optional[str]]


def _state_to_result(state: dict) -> MultiSourceResearchResult:
    routing_dict = state.get("routing")
    routing = ResearchRoutingPlan.model_validate(routing_dict) if routing_dict else None
    return state_to_multi_source_result(
        state,
        topic=(state.get("topic") or "").strip(),
        category=state.get("category"),
        routing=routing,
        sources_used=list(state.get("sources_used") or state.get("sources") or []),
    )


def _result_to_state_update(result: MultiSourceResearchResult) -> dict:
    return {
        "tavily_results": _dump_items(result.tavily_results),
        "news_results": _dump_items(result.news_results),
        "papers_results": _dump_items(result.papers_results),
        "github_results": _dump_items(result.github_results),
        "tavily_answer": result.tavily_answer,
        "media_urls": list(result.media_urls or []),
        "errors": dict(result.errors or {}),
        "sources_used": list(result.sources_used or []),
    }


def dispatch_edge(state: SessionState) -> str:
    return "route" if state.get("turn_kind") == "gather" else "chat"


def route_node(state: SessionState) -> dict:
    plan = route_topic(state["topic"], run_mode=state.get("run_mode", "research"))  # type: ignore[arg-type]
    return {
        "routing": plan.model_dump(mode="json"),
        "search_query": plan.search_query,
        "papers_search_query": plan.papers_search_query,
        "sources": list(plan.sources),
        "limit": plan.limit,
        "category": plan.category,
        "with_report": False,
        "errors": {},
    }


def route_sources(state: SessionState) -> List[str]:
    # route_topic() always selects >=1 source in practice; fall back to a plain
    # web search rather than silently skipping straight to END (which would
    # skip gather/build_result and leave last_answer/history unset).
    return list(state.get("sources") or []) or ["tavily"]


def gather_wrapper_node(state: SessionState) -> dict:
    out = dict(gather_node(state))
    for key in ("tavily_results", "news_results", "papers_results", "github_results"):
        if key in out:
            out[key] = _dump_items(out[key])
    out["sources_used"] = list(state.get("sources") or [])
    return out


def build_result_node(state: SessionState) -> dict:
    result = _state_to_result(state)
    answer = build_opening_summary(result)
    history = list(state.get("history") or [])
    history.append({"role": "assistant", "content": answer})
    return {"last_answer": answer, "history": history}


def chat_node(state: SessionState) -> dict:
    question = state.get("question") or ""
    current_mode = state.get("run_mode", "research")
    result = _state_to_result(state)
    history = list(state.get("history") or [])

    run_mode = current_mode
    state_update: dict = {}

    mode_switch = detect_mode_switch(question, current_mode)  # type: ignore[arg-type]
    if mode_switch and mode_switch.suggested_mode != current_mode:
        if state.get("auto_mode_switch"):
            decision = {"decision": "accept"}
        else:
            decision = interrupt(
                {
                    "type": "mode_switch",
                    "suggested_mode": mode_switch.suggested_mode,
                    "reason": mode_switch.reason,
                    "query": mode_switch.query,
                    "current_mode": current_mode,
                }
            )
        if isinstance(decision, dict) and decision.get("decision") == "accept":
            run_mode = mode_switch.suggested_mode
    else:
        analysis = analyze_followup(question, result, current_mode=current_mode)  # type: ignore[arg-type]
        if analysis.mode == "propose_research":
            if state.get("auto_expand"):
                decision = {"decision": "accept"}
            else:
                decision = interrupt(
                    {
                        "type": "expand_research",
                        "query": analysis.query or question,
                        "sources": analysis.sources or ["tavily"],
                        "reason": analysis.reason,
                        "user_message": analysis.user_message,
                    }
                )
            if isinstance(decision, dict) and decision.get("decision") == "accept":
                expanded = expand_research(
                    research=result,
                    query=analysis.query or question,
                    sources=analysis.sources or ["tavily"],
                )
                result = expanded
                state_update.update(_result_to_state_update(expanded))
        elif current_mode == "plan" and _PLAN_RE.search(question):
            plan, markdown, _err = synthesize_plan(result, result.routing, use_llm=False)
            answer = (
                f"Updated plan for your follow-up — see structured sections below.\n\n"
                f"**{plan.headline}**"
            )
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            state_update.update(
                {
                    "last_answer": answer,
                    "last_plan": plan.model_dump(mode="json"),
                    "last_plan_markdown": markdown,
                    "history": history,
                }
            )
            return state_update

    answer = answer_from_context(
        question=question,
        research=result,
        history=history,
        current_mode=run_mode,  # type: ignore[arg-type]
    )
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    state_update.update(
        {
            "run_mode": run_mode,
            "last_answer": answer,
            "last_plan": None,
            "last_plan_markdown": None,
            "history": history,
        }
    )
    return state_update


def build_session_graph():
    g = StateGraph(SessionState)
    g.add_node("route", route_node)
    g.add_node("tavily_research", tavily_node)
    g.add_node("news_research", news_node)
    g.add_node("papers_research", papers_node)
    g.add_node("github_research", github_node)
    g.add_node("gather", gather_wrapper_node)
    g.add_node("build_result", build_result_node)
    g.add_node("chat", chat_node)

    g.add_conditional_edges(START, dispatch_edge, {"route": "route", "chat": "chat"})
    g.add_conditional_edges(
        "route",
        route_sources,
        {
            "tavily": "tavily_research",
            "news": "news_research",
            "papers": "papers_research",
            "github": "github_research",
        },
    )
    for n in ("tavily_research", "news_research", "papers_research", "github_research"):
        g.add_edge(n, "gather")
    g.add_edge("gather", "build_result")
    g.add_edge("build_result", END)
    g.add_edge("chat", END)

    return g.compile(checkpointer=MemorySaver())


session_graph = build_session_graph()
