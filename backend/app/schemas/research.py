"""
schemas/research.py

Pydantic models for Feature 1 research results (Tavily web).
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WebResult(BaseModel):
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Source URL")
    content: str = Field(default="", description="Snippet / summary content")
    score: Optional[float] = Field(
        default=None,
        description="Tavily relevance score (0-1) when available",
    )


class WebResearchResult(BaseModel):
    topic: str
    source: Literal["tavily"] = "tavily"
    results: List[WebResult] = Field(default_factory=list)
    answer: Optional[str] = Field(
        default=None,
        description="Optional short Tavily answer summary",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    error: Optional[str] = None
