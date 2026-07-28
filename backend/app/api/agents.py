"""
api/agents.py

Showcase API Router for AI Social Media Manager Pipeline

WHY a separate router?
- FastAPI routers allow us to organize endpoints by feature area (agents, auth, analytics).
- This file specifically showcases the agent pipeline built in Modules 1-5.
- Keeping routes separate from main.py keeps the codebase scalable and clean.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import agents from Modules 4 and 5
from app.agents.research_agent import run_research_agent, ResearchReport
from app.agents.planner_agent import run_planner_agent
from app.schemas.plan import WeeklyContentPlan

# WHY prefix="/api"?
# All agent-related endpoints are namespaced under /api to distinguish them
# from static routes or future websocket endpoints.
router = APIRouter(prefix="/api", tags=["Agent Pipeline Showcase"])


# ==========================================
# 1. Request/Response Models
# ==========================================
class ResearchRequest(BaseModel):
    """Request body for triggering the Research Agent."""
    topic: str


class ShowcaseResponse(BaseModel):
    """
    Combined response showing the full pipeline output from Modules 1-5.
    WHY return both? During showcase, we want to demonstrate each agent's
    individual output so reviewers can see the data transformation clearly.
    """
    module: str
    research_report: ResearchReport
    content_plan: WeeklyContentPlan


# ==========================================
# 2. Individual Agent Endpoints (for isolated testing)
# ==========================================
@router.get("/health/agents", summary="Agent Health Check")
async def agent_health():
    """
    Verifies that the agent modules are imported and available.
    Use this to quickly confirm the agent pipeline is wired up correctly.
    """
    return {
        "status": "ok",
        "modules_loaded": [
            "Module 1: Project Setup",
            "Module 2: Backend Foundation",
            "Module 3: LangGraph Foundation",
            "Module 4: Research Agent",
            "Module 5: Planner Agent",
        ],
    }


@router.post(
    "/research",
    response_model=ResearchReport,
    summary="Module 4 — Run Research Agent",
)
async def run_research(request: ResearchRequest):
    """
    Triggers only the Research Agent (Module 4).

    Useful for isolating and testing the research phase of the pipeline
    before passing results to the Planner Agent.
    """
    try:
        result = run_research_agent(topic=request.topic)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research Agent failed: {str(e)}")


@router.post(
    "/plan",
    response_model=WeeklyContentPlan,
    summary="Module 5 — Run Planner Agent (needs research input)",
)
async def run_plan(research_report: ResearchReport):
    """
    Triggers only the Planner Agent (Module 5).
    Expects a ResearchReport JSON body as input.
    
    Useful for testing the Planner Agent in isolation by providing
    a pre-built research report.
    """
    try:
        result = run_planner_agent(research_report=research_report)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planner Agent failed: {str(e)}")


# ==========================================
# 3. Full Pipeline Showcase Endpoint
# ==========================================
@router.post(
    "/showcase/plan",
    response_model=ShowcaseResponse,
    summary="🚀 Showcase — Full Pipeline (Modules 1-5)",
)
async def showcase_full_pipeline(request: ResearchRequest):
    """
    **SHOWCASE ENDPOINT** — Runs the full agent pipeline from research to planning.

    Pipeline:
    1. Takes a `topic` string as input.
    2. Runs the **Research Agent** (Module 4) to gather trends, news, and insights.
    3. Passes the research report to the **Planner Agent** (Module 5).
    4. Returns both the research report AND the weekly content plan in one response.

    This single endpoint demonstrates all 5 modules working together end-to-end.
    """
    try:
        # Step 1: Research Agent (Module 4)
        research_report = run_research_agent(topic=request.topic)

        # Step 2: Planner Agent (Module 5)
        # WHY pass the full research_report object?
        # The Planner Agent is designed to consume the entire typed ResearchReport,
        # not just the topic string. This allows it to use all research fields
        # (trends, sentiment, news) to create a well-informed plan.
        content_plan = run_planner_agent(research_report=research_report)

        return ShowcaseResponse(
            module="Modules 1-5: Project Setup → Backend Foundation → LangGraph → Research Agent → Planner Agent",
            research_report=research_report,
            content_plan=content_plan,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )
