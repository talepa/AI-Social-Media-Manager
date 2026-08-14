"""
services/tavily_client.py

Feature 1: web research via Tavily Search API.
Production-friendly: official API, structured results for LLM agents.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

from dotenv import load_dotenv

from app.schemas.research import WebResult

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)


def _api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "").strip()


def _require_api_key() -> str:
    key = _api_key()
    if not key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Get a free key at https://app.tavily.com "
            "and add it to your .env file."
        )
    return key


def search_web(
    topic: str,
    limit: int = 10,
    *,
    search_depth: str = "basic",
    include_answer: bool = True,
    time_range: Optional[str] = "month",
) -> Tuple[List[WebResult], Optional[str], List[str]]:
    """
    Search the web with Tavily for `topic`.

    Returns (results, optional_answer_summary, image_urls).
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    api_key = _require_api_key()

    try:
        from tavily import TavilyClient
    except ImportError as exc:
        raise RuntimeError(
            "tavily-python is not installed. Run: pip install tavily-python"
        ) from exc

    client = TavilyClient(api_key=api_key)

    kwargs = {
        "query": topic,
        "max_results": limit,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_images": True,
        "topic": "general",
    }
    if time_range:
        kwargs["time_range"] = time_range

    try:
        response = client.search(**kwargs)
    except Exception as exc:
        logger.exception("Tavily search failed")
        raise RuntimeError(f"Tavily search failed: {exc}") from exc

    raw_results = response.get("results") or []
    results: List[WebResult] = []
    for item in raw_results:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        if not title and not url:
            continue
        score = item.get("score")
        image = item.get("image") or item.get("img_src") or item.get("thumbnail")
        if isinstance(image, dict):
            image = image.get("url") or image.get("src")
        results.append(
            WebResult(
                title=title or url,
                url=url,
                content=(item.get("content") or "").strip(),
                score=float(score) if score is not None else None,
                image_url=(str(image).strip() if image else None) or None,
            )
        )

    answer = response.get("answer")
    if isinstance(answer, str):
        answer = answer.strip() or None
    else:
        answer = None

    raw_images = response.get("images") or []
    image_urls: List[str] = []
    for img in raw_images:
        if isinstance(img, str) and img.strip():
            image_urls.append(img.strip())
        elif isinstance(img, dict):
            u = img.get("url") or img.get("src")
            if u:
                image_urls.append(str(u).strip())

    return results, answer, image_urls[:12]
