"""
Filter irrelevant / low-quality web (Tavily) hits.
"""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse

from app.schemas.research import ResearchItem
from app.services.query_utils import topic_tokens, wants_youtube

_ADULT_RE = re.compile(
    r"\b(porno|porn|xxx|sex video|sex tube|nude|nsfw|adult video|"
    r"rahibe|jale sex|teen.*video)\b",
    re.I,
)

_GARBAGE_HOST_RE = re.compile(
    r"(porno|xxx|adult|sex-tube|xhamster|pornhub|xvideos)",
    re.I,
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


def _is_youtube(url: str) -> bool:
    h = _host(url)
    return h == "youtu.be" or h.endswith("youtube.com")


def _token_overlap(topic: str, item: ResearchItem) -> float:
    tokens = topic_tokens(topic)
    if not tokens:
        return 1.0
    blob = f"{item.title} {item.content} {item.url}".lower()
    hits = sum(1 for t in tokens if t in blob)
    return hits / len(tokens)


def filter_tavily_results(
    topic: str,
    items: List[ResearchItem],
    *,
    limit: int = 12,
    min_score: float = 0.22,
) -> List[ResearchItem]:
    """Drop spam, adult, and very low-relevance web hits."""
    if not items:
        return []

    yt_mode = wants_youtube(topic)
    min_score = 0.14 if yt_mode else min_score
    kept: list[ResearchItem] = []

    for item in items:
        url = item.url or ""
        title = item.title or ""
        content = item.content or ""
        blob = f"{title} {content} {url}"

        if _ADULT_RE.search(blob):
            continue
        if _GARBAGE_HOST_RE.search(_host(url)):
            continue

        score = item.score if item.score is not None else 0.0
        overlap = _token_overlap(topic, item)

        if _is_youtube(url):
            if score < 0.08 and overlap < 0.2:
                continue
            kept.append(item)
            continue

        if score < min_score and overlap < 0.25:
            continue
        if score < 0.35 and overlap < 0.15:
            continue
        if overlap < 0.1 and score < 0.5:
            continue

        kept.append(item)

    kept.sort(
        key=lambda i: (
            1 if (yt_mode and _is_youtube(i.url or "")) else 0,
            i.score if i.score is not None else 0.0,
            _token_overlap(topic, i),
        ),
        reverse=True,
    )
    return kept[:limit]
