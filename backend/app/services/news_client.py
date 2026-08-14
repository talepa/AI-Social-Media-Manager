"""
services/news_client.py

Feature 2: fetch recent news via Google News RSS (free, no API key).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import quote_plus

import httpx

from app.schemas.research import ResearchItem

logger = logging.getLogger(__name__)

USER_AGENT = "AI-Social-Media-Manager/0.2 (Feature2 news research)"


def search_news(topic: str, limit: int = 8) -> List[ResearchItem]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    )

    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        if response.status_code != 200:
            raise RuntimeError(
                f"Google News RSS failed ({response.status_code}): "
                f"{response.text[:200]}"
            )
        payload = response.text

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise RuntimeError(f"Failed to parse Google News RSS: {exc}") from exc

    items: List[ResearchItem] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip() or None
        source_el = item.find("source")
        source_name = (source_el.text or "").strip() if source_el is not None else ""

        if not title:
            continue

        # Strip crude HTML from description if present
        content = description
        if "<" in content:
            try:
                content = "".join(ET.fromstring(f"<div>{description}</div>").itertext())
            except ET.ParseError:
                content = description

        if source_name and source_name not in content:
            content = f"{source_name}: {content}".strip(": ")

        items.append(
            ResearchItem(
                title=title,
                url=link or url,
                content=content[:500],
                source="news",
                published=pub_date,
            )
        )
        if len(items) >= limit:
            break

    return items
