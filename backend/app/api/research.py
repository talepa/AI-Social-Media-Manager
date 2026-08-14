"""
api/research.py

Research gather, on-demand report synthesize, and export.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from app.graphs.research_graph import run_multi_source_research, run_research_report
from app.graphs.tavily_graph import run_tavily_research
from app.schemas.research import (
    MultiSourceResearchResult,
    ResearchItem,
    ResearchReport,
    WebResearchResult,
)
from app.services.report_export import report_to_html, report_to_markdown
from app.services.report_synthesizer import synthesize_report
from app.services import research_cache

router = APIRouter(prefix="/api", tags=["Research"])


class WebResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to research")
    limit: int = Field(default=8, ge=1, le=20)
    force_refresh: bool = Field(
        default=False,
        description="Bypass cache and fetch fresh sources",
    )


class SynthesizeRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    tavily_results: list[ResearchItem] = Field(default_factory=list)
    news_results: list[ResearchItem] = Field(default_factory=list)
    papers_results: list[ResearchItem] = Field(default_factory=list)
    tavily_answer: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    use_llm: bool = Field(
        default=False,
        description="If true, enhance with Gemini; otherwise deterministic compile",
    )
    force_refresh: bool = Field(
        default=False,
        description="Bypass cached report for this source set",
    )


class ExportRequest(BaseModel):
    report: ResearchReport


@router.get("/health/research", summary="Research health check")
async def research_health():
    return {
        "status": "ok",
        "feature": 3,
        "orchestrator": "langgraph",
        "graph_nodes": [
            "tavily_research",
            "news_research",
            "papers_research",
            "gather",
            "synthesize_report",
        ],
        "sources": ["tavily", "news", "papers"],
        "report": True,
        "synthesize": True,
        "exports": ["markdown", "html", "json"],
        "cache": True,
    }


@router.post(
    "/research/tavily",
    response_model=WebResearchResult,
    summary="Feature 1 — Tavily web research only",
)
@router.post(
    "/research/web",
    response_model=WebResearchResult,
    include_in_schema=False,
)
async def research_tavily(request: WebResearchRequest):
    try:
        result = run_tavily_research(topic=request.topic, limit=request.limit)
        if result.error and not result.results:
            raise HTTPException(status_code=502, detail=result.error)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Tavily research failed: {exc}",
        ) from exc


@router.post(
    "/research/multi",
    response_model=MultiSourceResearchResult,
    summary="Multi-source research (no report)",
)
async def research_multi(request: WebResearchRequest):
    try:
        key = research_cache.multi_cache_key(request.topic, request.limit)
        if not request.force_refresh:
            hit = research_cache.get_cached(key, MultiSourceResearchResult)
            if hit is not None:
                hit.cached = True
                hit.cache_key = key
                # Don't return a stale nested report from an older payload shape
                hit.report = None
                hit.report_error = None
                return hit

        result = run_multi_source_research(
            topic=request.topic,
            limit=request.limit,
            with_report=False,
        )
        total = (
            len(result.tavily_results)
            + len(result.news_results)
            + len(result.papers_results)
        )
        if total == 0 and result.errors:
            raise HTTPException(
                status_code=502,
                detail=f"All research sources failed: {result.errors}",
            )

        result.cached = False
        result.cache_key = key
        # Cache sources only (strip report if any)
        to_store = result.model_copy(deep=True)
        to_store.report = None
        to_store.report_error = None
        to_store.cached = False
        research_cache.set_cached(key, to_store)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Multi-source research failed: {exc}",
        ) from exc


@router.post(
    "/research/synthesize",
    response_model=MultiSourceResearchResult,
    summary="Build report from existing sources (on demand)",
)
async def research_synthesize(request: SynthesizeRequest):
    """
    Does not re-scrape. Compiles (or optionally LLM-enhances) a report
    from sources the client already fetched via /research/multi.
    """
    try:
        partial = MultiSourceResearchResult(
            topic=request.topic.strip(),
            tavily_results=request.tavily_results,
            news_results=request.news_results,
            papers_results=request.papers_results,
            tavily_answer=request.tavily_answer,
            media_urls=request.media_urls,
        )
        total = (
            len(partial.tavily_results)
            + len(partial.news_results)
            + len(partial.papers_results)
        )
        if total == 0:
            raise HTTPException(status_code=400, detail="No sources to synthesize")

        key = research_cache.synthesize_cache_key(
            partial.topic,
            use_llm=request.use_llm,
            tavily_urls=[i.url for i in partial.tavily_results],
            news_urls=[i.url for i in partial.news_results],
            papers_urls=[i.url for i in partial.papers_results],
        )

        if not request.force_refresh:
            hit = research_cache.get_cached(key, MultiSourceResearchResult)
            if hit is not None and hit.report is not None:
                hit.cached = True
                hit.cache_key = key
                return hit

        report, err = synthesize_report(partial, use_llm=request.use_llm)
        partial.report = report
        partial.report_error = err
        partial.cached = False
        partial.cache_key = key
        if report is None:
            raise HTTPException(
                status_code=502,
                detail=err or "Report synthesis failed",
            )
        research_cache.set_cached(key, partial)
        return partial
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Synthesize failed: {exc}",
        ) from exc


@router.post(
    "/research/report",
    response_model=MultiSourceResearchResult,
    summary="One-shot: gather + report (legacy / convenience)",
)
async def research_report(request: WebResearchRequest):
    try:
        # Reuse multi cache when possible, then synthesize
        multi_key = research_cache.multi_cache_key(request.topic, request.limit)
        base: MultiSourceResearchResult | None = None
        if not request.force_refresh:
            base = research_cache.get_cached(multi_key, MultiSourceResearchResult)

        if base is None:
            base = run_multi_source_research(
                topic=request.topic,
                limit=request.limit,
                with_report=False,
            )
            total = (
                len(base.tavily_results)
                + len(base.news_results)
                + len(base.papers_results)
            )
            if total == 0 and base.errors:
                raise HTTPException(
                    status_code=502,
                    detail=f"All research sources failed: {base.errors}",
                )
            store = base.model_copy(deep=True)
            store.report = None
            store.report_error = None
            research_cache.set_cached(multi_key, store)

        synth_key = research_cache.synthesize_cache_key(
            base.topic,
            use_llm=False,
            tavily_urls=[i.url for i in base.tavily_results],
            news_urls=[i.url for i in base.news_results],
            papers_urls=[i.url for i in base.papers_results],
        )
        if not request.force_refresh:
            hit = research_cache.get_cached(synth_key, MultiSourceResearchResult)
            if hit is not None and hit.report is not None:
                hit.cached = True
                hit.cache_key = synth_key
                return hit

        report, err = synthesize_report(base, use_llm=False)
        base.report = report
        base.report_error = err
        base.cached = False
        base.cache_key = synth_key
        if report is None and err:
            raise HTTPException(
                status_code=502,
                detail=f"Report synthesis failed: {err}",
            )
        research_cache.set_cached(synth_key, base)
        return base
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Research report failed: {exc}",
        ) from exc


@router.post(
    "/research/export/markdown",
    summary="Download report as Markdown",
    response_class=PlainTextResponse,
)
async def export_markdown(request: ExportRequest):
    body = report_to_markdown(request.report)
    filename = "research-report.md"
    return PlainTextResponse(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/research/export/html",
    summary="Printable HTML (Save as PDF from the browser)",
    response_class=HTMLResponse,
)
async def export_html(request: ExportRequest):
    html = report_to_html(request.report)
    return HTMLResponse(
        content=html,
        headers={
            "Content-Disposition": 'inline; filename="research-report.html"',
        },
    )


@router.post(
    "/research/export/json",
    summary="Download report as JSON",
)
async def export_json(request: ExportRequest):
    payload = request.report.model_dump_json(indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="research-report.json"',
        },
    )
