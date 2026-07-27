import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Social Media Manager API",
    description="Backend API for managing AI agents and social media tasks.",
    version="1.0.0",
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

@app.get("/")
async def root():
    """
    Root endpoint serving as a welcome message.
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the AI Social Media Manager API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    logger.info("Health check endpoint accessed")
    return {"status": "ok", "service": "AI Social Media Manager Backend"}
