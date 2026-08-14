"""
services/news_client.py

Feature 2: fetch recent news via Google News RSS (free, no API key).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import quote_plus

import httpx

from app.schemas.research import ResearchItem
from app.services.preview_client import favicon_for_url

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; AI-Social-Media-Manager/0.3; +https://localhost)"
)
MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}


def _https_upgrade(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url or None


def _rss_media_image(item: ET.Element) -> Optional[str]:
    for tag in ("thumbnail", "content"):
        el = item.find(f"media:{tag}", MEDIA_NS)
        if el is None:
            continue
        src = (el.get("url") or "").strip()
        if src.startswith("http"):
            return _https_upgrade(src)
    return None


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
        source_homepage = (
            (source_el.get("url") or "").strip() if source_el is not None else ""
        )

        if not title:
            continue

        content = description
        image_url = _rss_media_image(item)
        if "<" in content:
            try:
                wrapped = ET.fromstring(f"<div>{description}</div>")
                content = "".join(wrapped.itertext())
                if not image_url:
                    for img in wrapped.iter("img"):
                        src = (img.get("src") or "").strip()
                        if src.startswith("http"):
                            image_url = _https_upgrade(src)
                            break
            except ET.ParseError:
                content = description

        if source_name and source_name not in content:
            content = f"{source_name}: {content}".strip(": ")

        # Prefer publisher homepage favicon over news.google.com
        favicon = favicon_for_url(source_homepage or link)

        items.append(
            ResearchItem(
                title=title,
                url=link or url,
                content=content[:500],
                source="news",
                published=pub_date,
                image_url=image_url,
                favicon_url=favicon,
            )
        )
        if len(items) >= limit:
            break

    return items
