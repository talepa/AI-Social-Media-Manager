"""
services/research_categories.py

Research category presets → which sources to run.
"""

from __future__ import annotations

from typing import List, Literal

ResearchCategory = Literal[
    "general",
    "ai_engineer",
    "founder",
    "academic",
    "news_desk",
]

ResearchSource = Literal["tavily", "news", "papers", "github"]

CATEGORY_SOURCES: dict[str, List[ResearchSource]] = {
    "general": ["tavily", "news", "papers"],
    "ai_engineer": ["tavily", "papers", "github"],
    "founder": ["tavily", "news", "papers"],
    "academic": ["papers", "tavily"],
    "news_desk": ["news", "tavily"],
}

CATEGORY_LABELS: dict[str, str] = {
    "general": "General",
    "ai_engineer": "AI Engineer",
    "founder": "Founder",
    "academic": "Academic",
    "news_desk": "News desk",
}

ALL_SOURCES: List[ResearchSource] = ["tavily", "news", "papers", "github"]


def resolve_sources(
    category: str | None = None,
    sources: List[str] | None = None,
) -> List[ResearchSource]:
    """
    Prefer explicit sources list when provided; otherwise use category preset.
    Always returns at least one valid source.
    """
    if sources:
        cleaned: List[ResearchSource] = []
        for s in sources:
            key = (s or "").strip().lower()
            if key in ALL_SOURCES and key not in cleaned:
                cleaned.append(key)  # type: ignore[arg-type]
        if cleaned:
            return cleaned

    cat = (category or "general").strip().lower()
    preset = CATEGORY_SOURCES.get(cat) or CATEGORY_SOURCES["general"]
    return list(preset)
