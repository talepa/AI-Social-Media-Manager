"""
services/brave_client.py

Web research via Brave Search API. Drop-in alternative to tavily_client.py
for the investigation pipeline's Web Intelligence Agent.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

import httpx
from dotenv import load_dotenv

from app.schemas.research import WebResult

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.search.brave.com/res/v1/web/search"


def _api_key() -> str:
    return os.getenv("BRAVE_API_KEY", "").strip()


def _require_api_key() -> str:
    key = _api_key()
    if not key:
        raise RuntimeError(
            "BRAVE_API_KEY is not set. Get a free key at "
            "https://api.search.brave.com and add it to your .env file."
        )
    return key


def _https_upgrade(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url or None


def search_web(
    topic: str,
    limit: int = 10,
    *,
    freshness: Optional[str] = None,
) -> Tuple[List[WebResult], Optional[str], List[str]]:
    """
    Search the web with Brave Search for ``topic``.

    Args:
        topic: Search query string.
        limit: Maximum number of results (1-20, clamped).
        freshness: Optional recency filter — "pd" (past day), "pw" (past week),
                   "pm" (past month), "py" (past year), or None for all time.

    Returns:
        (results, None, image_urls) — the ``None`` slot keeps the same
        3-tuple signature as ``tavily_client.search_web`` for compatibility.
        Brave does not return an answer summary.
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    api_key = _require_api_key()

    params: dict = {
        "q": topic,
        "count": limit,
        "text_decorations": False,
        "search_lang": "en",
    }
    if freshness:
        params["freshness"] = freshness

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    try:
        with httpx.Client(timeout=25.0, follow_redirects=True) as client:
            resp = client.get(_BASE_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300] if exc.response else ""
        raise RuntimeError(
            f"Brave Search API error {exc.response.status_code}: {body}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Brave Search request failed: {exc}") from exc

    raw_results = (data.get("web") or {}).get("results") or []
    results: List[WebResult] = []
    image_urls: List[str] = []

    for item in raw_results:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        if not title and not url:
            continue

        thumbnail = item.get("thumbnail") or {}
        image = _https_upgrade(thumbnail.get("src") if isinstance(thumbnail, dict) else None)

        profile = item.get("profile") or {}
        favicon = _https_upgrade(profile.get("img") if isinstance(profile, dict) else None)
        if not favicon:
            favicon = _https_upgrade(item.get("favicon_url"))

        results.append(
            WebResult(
                title=title or url,
                url=url,
                content=(item.get("description") or "").strip()[:600],
                score=None,
                image_url=image,
                favicon_url=favicon,
            )
        )

        if image and image not in image_urls:
            image_urls.append(image)

    return results, None, image_urls[:12]
