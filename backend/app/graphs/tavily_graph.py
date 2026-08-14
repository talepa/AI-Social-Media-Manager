"""
graphs/tavily_graph.py

Feature 1 LangGraph: user topic -> Tavily web search -> results.

Flow: START -> tavily_research -> END
"""

from datetime import datetime, timezone
from typing import List, NotRequired, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.research import WebResearchResult, WebResult
from app.services.tavily_client import search_web


class TavilyResearchState(TypedDict):
    topic: str
    limit: NotRequired[int]
    results: NotRequired[List[WebResult]]
    answer: NotRequired[Optional[str]]
    error: NotRequired[str]


def tavily_research_node(state: TavilyResearchState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = int(state.get("limit") or 10)
    try:
        results, answer, _images = search_web(topic=topic, limit=limit)
        return {"results": results, "answer": answer, "error": None}
    except Exception as exc:
        return {"results": [], "answer": None, "error": str(exc)}


def build_tavily_graph():
    workflow = StateGraph(TavilyResearchState)
    workflow.add_node("tavily_research", tavily_research_node)
    workflow.add_edge(START, "tavily_research")
    workflow.add_edge("tavily_research", END)
    return workflow.compile()


tavily_graph = build_tavily_graph()


def run_tavily_research(topic: str, limit: int = 10) -> WebResearchResult:
    """Invoke the Tavily graph and return a typed API result."""
    final = tavily_graph.invoke({"topic": topic, "limit": limit})
    raw = final.get("results") or []
    normalized: List[WebResult] = []
    for item in raw:
        if isinstance(item, WebResult):
            normalized.append(item)
        else:
            normalized.append(WebResult.model_validate(item))

    return WebResearchResult(
        topic=topic,
        results=normalized,
        answer=final.get("answer"),
        fetched_at=datetime.now(timezone.utc),
        error=final.get("error"),
    )
