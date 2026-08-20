"""
Re-route mixed Tavily hits (GitHub / YouTube URLs) into the right result buckets.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.schemas.research import MultiSourceResearchResult, ResearchItem
from app.services.github_utils import dedupe_github_items, filter_github_items, rank_github_items
from app.services.web_utils import filter_tavily_results


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


def _is_youtube(url: str) -> bool:
    h = _host(url)
    return h == "youtu.be" or h.endswith("youtube.com")


def _is_github(url: str) -> bool:
    return _host(url) == "github.com"


def _dedupe(existing: list[ResearchItem], new: list[ResearchItem]) -> list[ResearchItem]:
    return dedupe_github_items([*existing, *new])


def reclassify_results(result: MultiSourceResearchResult) -> MultiSourceResearchResult:
    """Keep YouTube in tavily for API compat; move GitHub URLs to github_results."""
    web: list[ResearchItem] = []
    github_moves: list[ResearchItem] = []

    for item in result.tavily_results:
        url = item.url or ""
        if _is_github(url):
            data = item.model_copy(update={"source": "github"})
            github_moves.append(data)
        else:
            web.append(item)

    data = result.model_copy(deep=True)
    data.tavily_results = filter_tavily_results(
        data.topic,
        web,
        limit=12,
        min_score=0.2,
    )
    merged_github = dedupe_github_items([*(data.github_results or []), *github_moves])
    data.github_results = rank_github_items(data.topic, merged_github)
    data.github_results = filter_github_items(
        data.topic,
        data.github_results,
        limit=12,
        min_relevance=0.15,
    )
    return data
