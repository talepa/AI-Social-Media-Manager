"""
graphs/research_graph.py

Multi-source research + optional report synthesis.

Flow:
  START → enabled sources (parallel) → gather → synthesize_report → END

Sources are selected via category preset or an explicit sources list.
"""

from datetime import datetime, timezone
from typing import Annotated, Dict, List, NotRequired, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.research import (
    MultiSourceResearchResult,
    ResearchItem,
    ResearchReport,
    ResearchRoutingPlan,
    WebResult,
)
from app.services.github_client import search_github_repos
from app.services.news_client import search_news
from app.services.papers_client import search_papers
from app.services.preview_client import (
    backfill_images_from_media,
    collect_media_urls,
    enrich_items_with_previews,
)
from app.services.result_classifier import reclassify_results
from app.services.query_utils import build_web_search_query, wants_youtube
from app.services.web_utils import filter_tavily_results
from app.services.report_synthesizer import synthesize_report
from app.services.research_categories import resolve_sources
from app.services.tavily_client import search_web


def _merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    return {**(left or {}), **(right or {})}


class MultiSourceState(TypedDict):
    topic: str
    search_query: NotRequired[Optional[str]]
    papers_search_query: NotRequired[Optional[str]]
    limit: NotRequired[int]
    with_report: NotRequired[bool]
    category: NotRequired[Optional[str]]
    sources: NotRequired[List[str]]
    tavily_results: NotRequired[List[ResearchItem]]
    news_results: NotRequired[List[ResearchItem]]
    papers_results: NotRequired[List[ResearchItem]]
    github_results: NotRequired[List[ResearchItem]]
    tavily_answer: NotRequired[Optional[str]]
    media_urls: NotRequired[List[str]]
    # Parallel nodes may each report an error — merge instead of overwrite
    errors: Annotated[Dict[str, str], _merge_dicts]
    report: NotRequired[Optional[ResearchReport]]
    report_error: NotRequired[Optional[str]]


def _enabled(state: MultiSourceState, source: str) -> bool:
    sources = state.get("sources") or []
    return source in sources


def _query(state: MultiSourceState) -> str:
    return (state.get("search_query") or state.get("topic") or "").strip()


def tavily_node(state: MultiSourceState) -> dict:
    if not _enabled(state, "tavily"):
        return {"tavily_results": [], "tavily_answer": None}
    raw_topic = (state.get("topic") or "").strip()
    topic = _query(state)
    limit = int(state.get("limit") or 8)
    yt = wants_youtube(raw_topic) or "site:youtube.com" in topic.lower()
    search_q = topic
    if yt and "site:youtube.com" not in topic.lower():
        search_q = build_web_search_query(raw_topic, youtube=True)
    try:
        results, answer, images = search_web(
            topic=search_q,
            limit=limit,
            time_range=None if yt else "month",
        )
        items = [
            ResearchItem(
                title=r.title,
                url=r.url,
                content=r.content,
                source="tavily",
                score=r.score,
                image_url=r.image_url,
                favicon_url=r.favicon_url,
            )
            for r in results
        ]
        items = filter_tavily_results(raw_topic or search_q, items, limit=limit)
        media = [i.image_url for i in items if i.image_url]
        for u in images:
            if u not in media:
                media.append(u)
        return {
            "tavily_results": items,
            "tavily_answer": answer,
            "media_urls": media[:12],
        }
    except Exception as exc:
        return {
            "tavily_results": [],
            "tavily_answer": None,
            "errors": {"tavily": str(exc)},
        }


def news_node(state: MultiSourceState) -> dict:
    if not _enabled(state, "news"):
        return {"news_results": []}
    topic = _query(state)
    limit = min(int(state.get("limit") or 8), 10)
    try:
        items = search_news(topic=topic, limit=limit)
        return {"news_results": items}
    except Exception as exc:
        return {"news_results": [], "errors": {"news": str(exc)}}


def _papers_query(state: MultiSourceState) -> str:
    return (
        state.get("papers_search_query")
        or state.get("search_query")
        or state.get("topic")
        or ""
    ).strip()


def papers_node(state: MultiSourceState) -> dict:
    if not _enabled(state, "papers"):
        return {"papers_results": []}
    topic = _papers_query(state)
    limit = min(int(state.get("limit") or 8), 8)
    try:
        items = search_papers(topic=topic, limit=limit)
        return {"papers_results": items}
    except Exception as exc:
        return {"papers_results": [], "errors": {"papers": str(exc)}}


def github_node(state: MultiSourceState) -> dict:
    if not _enabled(state, "github"):
        return {"github_results": []}
    topic = _query(state)
    limit = min(int(state.get("limit") or 8), 10)
    try:
        items = search_github_repos(topic=topic, limit=limit)
        return {"github_results": items}
    except Exception as exc:
        return {"github_results": [], "errors": {"github": str(exc)}}


def gather_node(state: MultiSourceState) -> dict:
    """Join parallel sources, then enrich missing previews from real pages."""
    tavily = _normalize_items(state.get("tavily_results"), "tavily")
    news = _normalize_items(state.get("news_results"), "news")
    papers = _normalize_items(state.get("papers_results"), "papers")
    github = _normalize_items(state.get("github_results"), "github")

    tavily = enrich_items_with_previews(tavily, max_fetch=8)
    news = enrich_items_with_previews(news, max_fetch=8)
    papers = enrich_items_with_previews(papers, max_fetch=4)
    # GitHub already has owner avatars — light enrich only
    github = enrich_items_with_previews(github, max_fetch=2)

    media = collect_media_urls(
        tavily,
        news,
        papers,
        github,
        extra=list(state.get("media_urls") or []),
    )
    tavily = backfill_images_from_media(tavily, media)
    news = backfill_images_from_media(news, media)
    papers = backfill_images_from_media(papers, media)
    github = backfill_images_from_media(github, media)

    media = collect_media_urls(tavily, news, papers, github, extra=media)
    return {
        "tavily_results": tavily,
        "news_results": news,
        "papers_results": papers,
        "github_results": github,
        "media_urls": media,
    }


def synthesize_node(state: MultiSourceState) -> dict:
    if not state.get("with_report"):
        return {"report": None, "report_error": None}

    partial = MultiSourceResearchResult(
        topic=(state.get("topic") or "").strip(),
        tavily_results=_normalize_items(state.get("tavily_results"), "tavily"),
        news_results=_normalize_items(state.get("news_results"), "news"),
        papers_results=_normalize_items(state.get("papers_results"), "papers"),
        github_results=_normalize_items(state.get("github_results"), "github"),
        tavily_answer=state.get("tavily_answer"),
        errors=state.get("errors") or {},
    )
    report, err = synthesize_report(partial, use_llm=False)
    return {"report": report, "report_error": err}


def build_research_graph():
    workflow = StateGraph(MultiSourceState)

    workflow.add_node("tavily_research", tavily_node)
    workflow.add_node("news_research", news_node)
    workflow.add_node("papers_research", papers_node)
    workflow.add_node("github_research", github_node)
    workflow.add_node("gather", gather_node)
    workflow.add_node("synthesize_report", synthesize_node)

    workflow.add_edge(START, "tavily_research")
    workflow.add_edge(START, "news_research")
    workflow.add_edge(START, "papers_research")
    workflow.add_edge(START, "github_research")

    workflow.add_edge("tavily_research", "gather")
    workflow.add_edge("news_research", "gather")
    workflow.add_edge("papers_research", "gather")
    workflow.add_edge("github_research", "gather")
    workflow.add_edge("gather", "synthesize_report")
    workflow.add_edge("synthesize_report", END)

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
                    image_url=item.image_url,
                )
            )
        elif isinstance(item, dict):
            data = dict(item)
            data.setdefault("source", source)
            items.append(ResearchItem.model_validate(data))
    return items


def state_to_multi_source_result(
    final: dict,
    *,
    topic: str,
    category: str | None,
    routing: ResearchRoutingPlan | None,
    sources_used: List[str],
) -> MultiSourceResearchResult:
    """Assemble + reclassify a MultiSourceResearchResult from a graph state dict.

    Shared by run_multi_source_research (below) and the session graph
    (app/graphs/session_graph.py), so both call sites stay in sync.
    """
    errors = final.get("errors") or {}
    if not isinstance(errors, dict):
        errors = {}

    report = final.get("report")
    if report is not None and not isinstance(report, ResearchReport):
        try:
            report = ResearchReport.model_validate(report)
        except Exception:
            report = None

    return reclassify_results(
        MultiSourceResearchResult(
            topic=topic,
            category=category or "general",
            routing=routing,
            sources_used=list(sources_used),
            tavily_results=_normalize_items(final.get("tavily_results"), "tavily"),
            news_results=_normalize_items(final.get("news_results"), "news"),
            papers_results=_normalize_items(final.get("papers_results"), "papers"),
            github_results=_normalize_items(final.get("github_results"), "github"),
            tavily_answer=final.get("tavily_answer"),
            media_urls=[str(u) for u in (final.get("media_urls") or []) if u],
            errors={str(k): str(v) for k, v in errors.items()},
            report=report,
            report_error=final.get("report_error"),
            fetched_at=datetime.now(timezone.utc),
        )
    )


def run_multi_source_research(
    topic: str,
    limit: int = 8,
    with_report: bool = False,
    category: str | None = None,
    sources: List[str] | None = None,
    search_query: str | None = None,
    routing: ResearchRoutingPlan | None = None,
) -> MultiSourceResearchResult:
    resolved = resolve_sources(category=category, sources=sources)
    query = (search_query or topic).strip()
    papers_query = (
        routing.papers_search_query if routing and routing.papers_search_query else None
    )
    final = research_graph.invoke(
        {
            "topic": topic,
            "search_query": query,
            "papers_search_query": papers_query,
            "limit": limit,
            "with_report": with_report,
            "category": category or "general",
            "sources": list(resolved),
            "errors": {},
        }
    )

    return state_to_multi_source_result(
        final,
        topic=topic,
        category=category,
        routing=routing,
        sources_used=list(resolved),
    )


def run_research_report(
    topic: str,
    limit: int = 8,
    category: str | None = None,
    sources: List[str] | None = None,
) -> MultiSourceResearchResult:
    """Research sources then synthesize the structured report."""
    return run_multi_source_research(
        topic=topic,
        limit=limit,
        with_report=True,
        category=category,
        sources=sources,
    )
