"""
schemas/research.py

Research result models + structured research report.
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
    image_url: Optional[str] = Field(
        default=None,
        description="Optional preview / article image URL",
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
    image_url: Optional[str] = None


class RankedFinding(BaseModel):
    rank: int = Field(..., ge=1, description="1 = most important")
    title: str
    summary: str
    why_it_matters: str = ""
    source_urls: List[str] = Field(default_factory=list)
    source_types: List[Literal["tavily", "news", "papers"]] = Field(
        default_factory=list,
    )
    image_url: Optional[str] = None


class NewsHighlight(BaseModel):
    headline: str
    summary: str
    url: str
    published: Optional[str] = None
    image_url: Optional[str] = None


class AcademicInsight(BaseModel):
    title: str
    summary: str
    url: str
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None


class ReportSource(BaseModel):
    title: str
    url: str
    source: Literal["tavily", "news", "papers"]
    note: Optional[str] = None
    image_url: Optional[str] = None


class ReportStats(BaseModel):
    web: int = 0
    news: int = 0
    papers: int = 0
    total: int = 0


class ResearchReport(BaseModel):
    """Structured research report synthesized from multi-source findings."""

    topic: str
    executive_summary: str = Field(
        ...,
        description="2–4 short paragraphs summarizing the research",
    )
    key_findings: List[RankedFinding] = Field(default_factory=list)
    news_highlights: List[NewsHighlight] = Field(default_factory=list)
    academic_context: List[AcademicInsight] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    sources: List[ReportSource] = Field(default_factory=list)
    media_urls: List[str] = Field(
        default_factory=list,
        description="Preview images / figures collected during research",
    )
    stats: Optional[ReportStats] = None
    mode: Literal["compile", "llm"] = "compile"


class MultiSourceResearchResult(BaseModel):
    topic: str
    tavily_results: List[ResearchItem] = Field(default_factory=list)
    news_results: List[ResearchItem] = Field(default_factory=list)
    papers_results: List[ResearchItem] = Field(default_factory=list)
    tavily_answer: Optional[str] = None
    media_urls: List[str] = Field(
        default_factory=list,
        description="Gallery images from search (e.g. Tavily include_images)",
    )
    errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-source error messages if a node failed",
    )
    report: Optional[ResearchReport] = Field(
        default=None,
        description="Synthesized research report when requested",
    )
    report_error: Optional[str] = Field(
        default=None,
        description="Set when report synthesis failed but sources succeeded",
    )
    cached: bool = Field(
        default=False,
        description="True when this payload was served from disk cache",
    )
    cache_key: Optional[str] = Field(
        default=None,
        description="Cache fingerprint for this request",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
