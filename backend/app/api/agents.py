"""
api/agents.py

Showcase API Router for AI Social Media Manager Pipeline

WHY a separate router?
- FastAPI routers allow us to organize endpoints by feature area (agents, auth, analytics).
- This file showcases the agent pipeline built in Modules 1-6.
- Keeping routes separate from main.py keeps the codebase scalable and clean.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import agents from Modules 4, 5, and 6
from app.agents.research_agent import run_research_agent, ResearchReport
from app.agents.planner_agent import run_planner_agent
from app.agents.writer_agent import run_writer_agent
from app.schemas.plan import WeeklyContentPlan
from app.schemas.content import WrittenContentBatch

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


class WriteRequest(BaseModel):
    """Request body for triggering the Writer Agent in isolation."""
    content_plan: WeeklyContentPlan
    brand_voice: str = "professional"


class ShowcaseRequest(BaseModel):
    """Request body for the full pipeline showcase endpoint."""
    topic: str
    brand_voice: str = "professional"


class ShowcaseResponse(BaseModel):
    """
    Combined response showing the full pipeline output from Modules 1-6.
    WHY return all three? During showcase, each agent's output is returned
    so reviewers can trace the exact data transformation at every stage.
    """
    module: str
    research_report: ResearchReport
    content_plan: WeeklyContentPlan
    written_content: WrittenContentBatch


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
            "Module 6: Writer Agent",
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
# 3. Module 6 — Writer Agent Endpoint
# ==========================================
@router.post(
    "/write",
    response_model=WrittenContentBatch,
    summary="Module 6 — Run Writer Agent",
)
async def run_write(request: WriteRequest):
    """
    Triggers only the Writer Agent (Module 6).
    Expects a WeeklyContentPlan JSON body plus an optional brand_voice.

    Brand voice presets: 'professional', 'casual', 'witty', 'inspirational'
    Or pass any custom voice description string.
    """
    try:
        result = run_writer_agent(
            content_plan=request.content_plan,
            brand_voice=request.brand_voice,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Writer Agent failed: {str(e)}")


# ==========================================
# 4. Full Pipeline Showcase Endpoint (Modules 1-6)
# ==========================================
@router.post(
    "/showcase/plan",
    response_model=ShowcaseResponse,
    summary="🚀 Showcase — Full Pipeline (Modules 1-6)",
)
async def showcase_full_pipeline(request: ShowcaseRequest):
    """
    **SHOWCASE ENDPOINT** — Runs the full agent pipeline from research to written content.

    Pipeline:
    1. Takes a `topic` and `brand_voice` as input.
    2. **Research Agent** (Module 4) — gathers trends, news, and insights.
    3. **Planner Agent** (Module 5) — transforms research into a WeeklyContentPlan.
    4. **Writer Agent** (Module 6) — writes a platform-specific post for each PostIdea.
    5. Returns all three outputs so you can trace every transformation.

    Brand voice presets: 'professional', 'casual', 'witty', 'inspirational'
    """
    try:
        # Step 1: Research Agent (Module 4)
        research_report = run_research_agent(topic=request.topic)

        # Step 2: Planner Agent (Module 5)
        content_plan = run_planner_agent(research_report=research_report)

        # Step 3: Writer Agent (Module 6)
        # WHY iterate inside the agent rather than here?
        # The writer agent owns the per-post iteration logic so the API layer
        # stays thin. The agent can later be swapped for an async parallel version
        # without changing this endpoint at all.
        written_content = run_writer_agent(
            content_plan=content_plan,
            brand_voice=request.brand_voice,
        )

        return ShowcaseResponse(
            module="Modules 1-6: Setup → Foundation → LangGraph → Research → Planner → Writer",
            research_report=research_report,
            content_plan=content_plan,
            written_content=written_content,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )
