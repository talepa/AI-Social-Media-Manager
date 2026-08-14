"""
api/research.py

Feature 1: Tavily-only research
Feature 2: Multi-source research (Tavily + News + Papers) via LangGraph
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graphs.research_graph import run_multi_source_research
from app.graphs.tavily_graph import run_tavily_research
from app.schemas.research import MultiSourceResearchResult, WebResearchResult

router = APIRouter(prefix="/api", tags=["Research"])


class WebResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to research")
    limit: int = Field(default=8, ge=1, le=20)


@router.get("/health/research", summary="Research health check")
async def research_health():
    return {
        "status": "ok",
        "feature": 2,
        "orchestrator": "langgraph",
        "graph_nodes": [
            "tavily_research",
            "news_research",
            "papers_research",
            "gather",
        ],
        "sources": ["tavily", "news", "papers"],
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
    summary="Feature 2 — Multi-source research (Tavily + News + Papers)",
)
async def research_multi(request: WebResearchRequest):
    """
    Runs LangGraph with parallel nodes:
    START → tavily / news / papers → gather → END
    """
    try:
        result = run_multi_source_research(topic=request.topic, limit=request.limit)
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
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Multi-source research failed: {exc}",
        ) from exc
