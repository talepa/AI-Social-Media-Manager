"""
mcp/servers/research.py — Research Discovery MCP.

Wraps Tavily + Google News (+ light page fetch) behind MCP tools.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from mcp.server.mcpserver import MCPServer

from app.services.news_client import search_news as news_search_client
from app.services.tavily_client import search_web as tavily_search_web

logger = logging.getLogger(__name__)

research_mcp = MCPServer(
    "research",
    instructions=(
        "Research Discovery MCP: web search, news search, and page fetch tools. "
        "Prefer search_web for general technical evidence; search_news for recent coverage."
    ),
)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)


def _items_payload(items: List[Any]) -> Dict[str, Any]:
    return {
        "items": [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in items
        ]
    }


@research_mcp.tool()
def search_web(query: str, limit: int = 8) -> Dict[str, Any]:
    """Search the web via Tavily. Returns titles, URLs, snippets, and scores."""
    results, _answer, _images = tavily_search_web(
        topic=query, limit=max(1, min(limit, 15))
    )
    return _items_payload(results)


@research_mcp.tool()
def search_news(query: str, limit: int = 8) -> Dict[str, Any]:
    """Search recent news via Google News RSS."""
    results = news_search_client(topic=query, limit=max(1, min(limit, 15)))
    return _items_payload(results)


@research_mcp.tool()
def fetch_url(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Fetch a URL and return truncated plain-text content."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    max_chars = max(200, min(int(max_chars), 12000))
    with httpx.Client(timeout=12.0, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "AtelierResearch/1.0"})
        resp.raise_for_status()
        final_url = str(resp.url)
        status = resp.status_code
        text = resp.text
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "url": final_url,
        "status_code": status,
        "content": text[:max_chars],
        "title": "",
    }


@research_mcp.tool()
def extract_content(url: str, max_chars: int = 3000) -> Dict[str, Any]:
    """Extract readable text content from a page URL (alias of fetch_url)."""
    return fetch_url(url=url, max_chars=max_chars)


@research_mcp.tool()
def get_page_metadata(url: str) -> Dict[str, Any]:
    """Fetch page metadata (title, description, host) without full body extraction."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "AtelierResearch/1.0"})
        resp.raise_for_status()
        html = resp.text[:200_000]
    title_m = _OG_TITLE_RE.search(html) or _TITLE_RE.search(html)
    desc_m = _META_DESC_RE.search(html)
    title = (title_m.group(1) if title_m else "").strip()
    title = re.sub(r"\s+", " ", title)
    description = (desc_m.group(1) if desc_m else "").strip()
    host = urlparse(str(resp.url)).hostname or ""
    return {
        "url": str(resp.url),
        "title": title,
        "description": description[:500],
        "host": host,
        "status_code": resp.status_code,
    }
