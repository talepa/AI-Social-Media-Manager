import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.research import router as research_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Social Media Manager API",
    description=(
        "LangGraph-first content pipeline.\n\n"
        "**Feature 1:** `POST /api/research/tavily`\n"
        "**Feature 2:** `POST /api/research/multi` "
        "(Tavily + News + Papers in parallel)\n\n"
        "Later: rate insights, write posts, human approval, publish."
    ),
    version="2.2.0-feature2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "AI Social Media Manager API",
        "feature": 2,
        "docs": "/docs",
        "tavily": "POST /api/research/tavily",
        "multi_research": "POST /api/research/multi",
    }


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok", "service": "AI Social Media Manager Backend", "feature": 2}
