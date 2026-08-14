"""
graphs/research_graph.py

Feature 2 LangGraph: parallel multi-source research.

Flow:
  START → tavily_research  ─┐
  START → news_research    ─┼→ gather → END
  START → papers_research  ─┘
"""

from datetime import datetime, timezone
from typing import Annotated, Dict, List, NotRequired, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.research import MultiSourceResearchResult, ResearchItem, WebResult
from app.services.news_client import search_news
from app.services.papers_client import search_papers
from app.services.tavily_client import search_web


def _merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    return {**(left or {}), **(right or {})}


class MultiSourceState(TypedDict):
    topic: str
    limit: NotRequired[int]
    tavily_results: NotRequired[List[ResearchItem]]
    news_results: NotRequired[List[ResearchItem]]
    papers_results: NotRequired[List[ResearchItem]]
    tavily_answer: NotRequired[Optional[str]]
    # Parallel nodes may each report an error — merge instead of overwrite
    errors: Annotated[Dict[str, str], _merge_dicts]


def tavily_node(state: MultiSourceState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = int(state.get("limit") or 8)
    try:
        results, answer = search_web(topic=topic, limit=limit)
        items = [
            ResearchItem(
                title=r.title,
                url=r.url,
                content=r.content,
                source="tavily",
                score=r.score,
            )
            for r in results
        ]
        return {
            "tavily_results": items,
            "tavily_answer": answer,
        }
    except Exception as exc:
        return {
            "tavily_results": [],
            "tavily_answer": None,
            "errors": {"tavily": str(exc)},
        }


def news_node(state: MultiSourceState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = min(int(state.get("limit") or 8), 10)
    try:
        items = search_news(topic=topic, limit=limit)
        return {"news_results": items}
    except Exception as exc:
        return {"news_results": [], "errors": {"news": str(exc)}}


def papers_node(state: MultiSourceState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = min(int(state.get("limit") or 8), 8)
    try:
        items = search_papers(topic=topic, limit=limit)
        return {"papers_results": items}
    except Exception as exc:
        return {"papers_results": [], "errors": {"papers": str(exc)}}


def gather_node(state: MultiSourceState) -> dict:
    # Join point after parallel sources — state already holds each list.
    return {}


def build_research_graph():
    workflow = StateGraph(MultiSourceState)

    workflow.add_node("tavily_research", tavily_node)
    workflow.add_node("news_research", news_node)
    workflow.add_node("papers_research", papers_node)
    workflow.add_node("gather", gather_node)

    # Fan-out from START (LangGraph runs these in parallel)
    workflow.add_edge(START, "tavily_research")
    workflow.add_edge(START, "news_research")
    workflow.add_edge(START, "papers_research")

    # Fan-in to gather
    workflow.add_edge("tavily_research", "gather")
    workflow.add_edge("news_research", "gather")
    workflow.add_edge("papers_research", "gather")
    workflow.add_edge("gather", END)

    return workflow.compile()


research_graph = build_research_graph()


def _normalize_items(raw: object, source: str) -> List[ResearchItem]:
    items: List[ResearchItem] = []
    if not isinstance(raw, list):
        return items
    for item in raw:
        if isinstance(item, ResearchItem):
            items.append(item)
        elif isinstance(item, WebResult):
            items.append(
                ResearchItem(
                    title=item.title,
                    url=item.url,
                    content=item.content,
                    source="tavily",
                    score=item.score,
                )
            )
        elif isinstance(item, dict):
            data = dict(item)
            data.setdefault("source", source)
            items.append(ResearchItem.model_validate(data))
    return items


def run_multi_source_research(topic: str, limit: int = 8) -> MultiSourceResearchResult:
    final = research_graph.invoke(
        {
            "topic": topic,
            "limit": limit,
            "errors": {},
        }
    )

    errors = final.get("errors") or {}
    if not isinstance(errors, dict):
        errors = {}

    return MultiSourceResearchResult(
        topic=topic,
        tavily_results=_normalize_items(final.get("tavily_results"), "tavily"),
        news_results=_normalize_items(final.get("news_results"), "news"),
        papers_results=_normalize_items(final.get("papers_results"), "papers"),
        tavily_answer=final.get("tavily_answer"),
        errors={str(k): str(v) for k, v in errors.items()},
        fetched_at=datetime.now(timezone.utc),
    )
