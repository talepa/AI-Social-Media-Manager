import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.investigation import router as investigation_router
from app.api.mcp import router as mcp_router
from app.api.research import router as research_router
from app.api.session import router as session_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Social Media Manager API",
    description=(
        "LangGraph research desk.\n\n"
        "**Gather:** `POST /api/research/multi`\n"
        "**Report on demand:** `POST /api/research/synthesize`\n"
        "**Export:** markdown · html/pdf · json\n"
    ),
    version="3.1.0-report-ondemand",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
# Session + investigation graphs use Postgres checkpointer when DATABASE_URL
# is reachable, otherwise MemorySaver (see app.services.checkpointer).
app.include_router(session_router)
app.include_router(investigation_router)
app.include_router(mcp_router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "AI Social Media Manager API",
        "feature": 2,
        "docs": "/docs",
        "tavily": "POST /api/research/tavily",
        "multi_research": "POST /api/research/multi",
        "mcp": "GET /api/mcp/capabilities",
    }


@app.get("/health")
async def health_check():
    from app.services.checkpointer import checkpointer_kind
    from app.services import investigation_store as store_mod
    from app.mcp.registry import mcp_enabled

    store_backend = getattr(store_mod.investigation_store, "backend", "unknown")
    return {
        "status": "ok",
        "service": "AI Social Media Manager Backend",
        "feature": 2,
        "checkpointer": checkpointer_kind(),
        "investigation_store": store_backend,
        "mcp": mcp_enabled(),
    }
