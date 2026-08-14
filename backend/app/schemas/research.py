"""
schemas/research.py

Research result models for Feature 1 (Tavily) and Feature 2 (multi-source).
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

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


class ResearchItem(BaseModel):
    """Unified item used across web / news / papers sources."""

    title: str
    url: str
    content: str = ""
    source: Literal["tavily", "news", "papers"]
    score: Optional[float] = None
    published: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None


class MultiSourceResearchResult(BaseModel):
    topic: str
    tavily_results: List[ResearchItem] = Field(default_factory=list)
    news_results: List[ResearchItem] = Field(default_factory=list)
    papers_results: List[ResearchItem] = Field(default_factory=list)
    tavily_answer: Optional[str] = None
    errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-source error messages if a node failed",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
