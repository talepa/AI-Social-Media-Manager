"""
api/research.py

Feature 1 API: Tavily web research via LangGraph.
Optional Reddit endpoint kept for later if OAuth is approved.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graphs.tavily_graph import run_tavily_research
from app.schemas.research import WebResearchResult

router = APIRouter(prefix="/api", tags=["Research"])


class WebResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to research on the web")
    limit: int = Field(default=10, ge=1, le=20)


@router.get("/health/research", summary="Research health check")
async def research_health():
    return {
        "status": "ok",
        "feature": 1,
        "orchestrator": "langgraph",
        "graph_nodes": ["tavily_research"],
        "sources": ["tavily"],
    }


@router.post(
    "/research/tavily",
    response_model=WebResearchResult,
    summary="Feature 1 — Tavily web research (LangGraph)",
)
@router.post(
    "/research/web",
    response_model=WebResearchResult,
    summary="Feature 1 — Web research alias (Tavily)",
    include_in_schema=False,
)
async def research_tavily(request: WebResearchRequest):
    """
    Runs the LangGraph: START -> tavily_research -> END.

    Searches the web with Tavily and returns structured results + optional answer.
    """
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
