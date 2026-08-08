import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
# WHY import here? main.py is the FastAPI application entry point.
# Each router is registered here to keep route registration centralized and explicit.
from app.api.agents import router as agents_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Social Media Manager API",
    description=(
        "Backend API for the AI Social Media Manager agent pipeline.\n\n"
        "**Modules Built:**\n"
        "- Module 1: Project Setup\n"
        "- Module 2: Backend Foundation\n"
        "- Module 3: LangGraph Foundation\n"
        "- Module 4: Research Agent\n"
        "- Module 5: Planner Agent\n"
        "- Module 6: Writer Agent\n\n"
        "Use `/api/showcase/plan` to run the full pipeline end-to-end."
    ),
    version="1.6.0",
)

# CORS configuration
# Using a wildcard or env variables in production, here we allow the local Next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
# WHY include_router? This mounts all endpoints defined in agents.py under the app.
# The prefix "/api" is already defined in the router itself.
app.include_router(agents_router)


@app.get("/")
async def root():
    """
    Root endpoint serving as a welcome message.
    """
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to the AI Social Media Manager API",
        "docs": "Visit /docs for the interactive API showcase",
        "modules_built": 6,
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    logger.info("Health check endpoint accessed")
    return {"status": "ok", "service": "AI Social Media Manager Backend"}
