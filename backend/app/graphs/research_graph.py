"""
graphs/research_graph.py

Multi-source research + optional report synthesis.

Flow:
  START → tavily_research  ─┐
  START → news_research    ─┼→ gather → synthesize_report → END
  START → papers_research  ─┘
"""

from datetime import datetime, timezone
from typing import Annotated, Dict, List, NotRequired, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.research import (
    MultiSourceResearchResult,
    ResearchItem,
    ResearchReport,
    WebResult,
)
from app.services.news_client import search_news
from app.services.papers_client import search_papers
from app.services.preview_client import (
    backfill_images_from_media,
    collect_media_urls,
    enrich_items_with_previews,
)
from app.services.report_synthesizer import synthesize_report
from app.services.tavily_client import search_web


def _merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    return {**(left or {}), **(right or {})}


class MultiSourceState(TypedDict):
    topic: str
    limit: NotRequired[int]
    with_report: NotRequired[bool]
    tavily_results: NotRequired[List[ResearchItem]]
    news_results: NotRequired[List[ResearchItem]]
    papers_results: NotRequired[List[ResearchItem]]
    tavily_answer: NotRequired[Optional[str]]
    media_urls: NotRequired[List[str]]
    # Parallel nodes may each report an error — merge instead of overwrite
    errors: Annotated[Dict[str, str], _merge_dicts]
    report: NotRequired[Optional[ResearchReport]]
    report_error: NotRequired[Optional[str]]


def tavily_node(state: MultiSourceState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = int(state.get("limit") or 8)
    try:
        results, answer, images = search_web(topic=topic, limit=limit)
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
        # Prefer result thumbnails, then Tavily gallery images
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
    """Join parallel sources, then enrich missing previews from real pages."""
    tavily = _normalize_items(state.get("tavily_results"), "tavily")
    news = _normalize_items(state.get("news_results"), "news")
    papers = _normalize_items(state.get("papers_results"), "papers")

    # Prefer fetching previews for web + news (visual); papers less often have og:image
    tavily = enrich_items_with_previews(tavily, max_fetch=8)
    news = enrich_items_with_previews(news, max_fetch=8)
    papers = enrich_items_with_previews(papers, max_fetch=4)

    media = collect_media_urls(
        tavily,
        news,
        papers,
        extra=list(state.get("media_urls") or []),
    )
    # Use leftover gallery images for any items still missing thumbnails
    tavily = backfill_images_from_media(tavily, media)
    news = backfill_images_from_media(news, media)
    papers = backfill_images_from_media(papers, media)

    media = collect_media_urls(tavily, news, papers, extra=media)
    return {
        "tavily_results": tavily,
        "news_results": news,
        "papers_results": papers,
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
    workflow.add_node("gather", gather_node)
    workflow.add_node("synthesize_report", synthesize_node)

    # Fan-out from START (LangGraph runs these in parallel)
    workflow.add_edge(START, "tavily_research")
    workflow.add_edge(START, "news_research")
    workflow.add_edge(START, "papers_research")

    # Fan-in to gather → synthesize → END
    workflow.add_edge("tavily_research", "gather")
    workflow.add_edge("news_research", "gather")
    workflow.add_edge("papers_research", "gather")
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


def run_multi_source_research(
    topic: str,
    limit: int = 8,
    with_report: bool = False,
) -> MultiSourceResearchResult:
    final = research_graph.invoke(
        {
            "topic": topic,
            "limit": limit,
            "with_report": with_report,
            "errors": {},
        }
    )

    errors = final.get("errors") or {}
    if not isinstance(errors, dict):
        errors = {}

    report = final.get("report")
    if report is not None and not isinstance(report, ResearchReport):
        try:
            report = ResearchReport.model_validate(report)
        except Exception:
            report = None

    return MultiSourceResearchResult(
        topic=topic,
        tavily_results=_normalize_items(final.get("tavily_results"), "tavily"),
        news_results=_normalize_items(final.get("news_results"), "news"),
        papers_results=_normalize_items(final.get("papers_results"), "papers"),
        tavily_answer=final.get("tavily_answer"),
        media_urls=[str(u) for u in (final.get("media_urls") or []) if u],
        errors={str(k): str(v) for k, v in errors.items()},
        report=report,
        report_error=final.get("report_error"),
        fetched_at=datetime.now(timezone.utc),
    )


def run_research_report(topic: str, limit: int = 8) -> MultiSourceResearchResult:
    """Research sources then synthesize the structured report."""
    return run_multi_source_research(topic=topic, limit=limit, with_report=True)
