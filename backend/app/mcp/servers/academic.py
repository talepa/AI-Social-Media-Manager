"""
mcp/servers/academic.py — Academic Knowledge MCP.

Wraps papers_client + Semantic Scholar detail endpoints.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List
from urllib.parse import quote

import httpx
from mcp.server.mcpserver import MCPServer

from app.services.papers_client import search_papers as papers_search_client

logger = logging.getLogger(__name__)

academic_mcp = MCPServer(
    "academic",
    instructions=(
        "Academic Knowledge MCP: search and inspect research papers. "
        "Use search_papers first; then get_paper / get_citations / get_related_papers "
        "for deeper inspection of a paper id."
    ),
)

S2_GRAPH = "https://api.semanticscholar.org/graph/v1"
USER_AGENT = "AtelierResearch/1.0 (academic-mcp)"


def _s2_headers() -> dict:
    headers = {"User-Agent": USER_AGENT}
    key = (os.getenv("SEMANTIC_SCHOLAR_API_KEY") or "").strip()
    if key:
        headers["x-api-key"] = key
    return headers


def _items_payload(items: List[Any]) -> Dict[str, Any]:
    return {
        "items": [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in items
        ]
    }


@academic_mcp.tool()
def search_papers(query: str, limit: int = 8) -> Dict[str, Any]:
    """Search academic papers (Semantic Scholar, OpenAlex, Crossref, arXiv)."""
    results = papers_search_client(topic=query, limit=max(1, min(limit, 15)))
    return _items_payload(results)


@academic_mcp.tool()
def get_paper(paper_id: str) -> Dict[str, Any]:
    """
    Get paper details by Semantic Scholar paperId, DOI, or arXiv id.
    Example ids: '649def34f8be52c8b66281af98ae884c09aef001', 'DOI:10.1234/x', 'ARXIV:1706.03762'
    """
    paper_id = (paper_id or "").strip()
    if not paper_id:
        raise ValueError("paper_id is required")
    fields = (
        "title,abstract,url,year,citationCount,authors,venue,externalIds,"
        "publicationDate,influentialCitationCount"
    )
    url = f"{S2_GRAPH}/paper/{quote(paper_id, safe='')}?fields={fields}"
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_s2_headers())
        if resp.status_code == 404:
            return {"error": "paper not found", "paper_id": paper_id}
        resp.raise_for_status()
        data = resp.json()
    authors = [a.get("name") for a in (data.get("authors") or []) if a.get("name")]
    return {
        "title": data.get("title") or "",
        "url": data.get("url") or "",
        "content": (data.get("abstract") or "")[:800],
        "year": data.get("year"),
        "citation_count": data.get("citationCount"),
        "authors": authors,
        "venue": data.get("venue"),
        "paper_id": data.get("paperId") or paper_id,
        "external_ids": data.get("externalIds") or {},
    }


@academic_mcp.tool()
def get_citations(paper_id: str, limit: int = 8) -> Dict[str, Any]:
    """List papers that cite the given Semantic Scholar paper id."""
    paper_id = (paper_id or "").strip()
    if not paper_id:
        raise ValueError("paper_id is required")
    limit = max(1, min(int(limit), 20))
    fields = "title,url,year,citationCount,authors,abstract"
    url = (
        f"{S2_GRAPH}/paper/{quote(paper_id, safe='')}/citations"
        f"?fields={fields}&limit={limit}"
    )
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_s2_headers())
        if resp.status_code == 404:
            return {"items": [], "error": "paper not found", "paper_id": paper_id}
        resp.raise_for_status()
        payload = resp.json()
    items = []
    for row in payload.get("data") or []:
        citing = row.get("citingPaper") or {}
        authors = [a.get("name") for a in (citing.get("authors") or []) if a.get("name")]
        items.append(
            {
                "title": citing.get("title") or "",
                "url": citing.get("url") or "",
                "content": (citing.get("abstract") or "")[:400],
                "year": citing.get("year"),
                "citation_count": citing.get("citationCount"),
                "authors": authors,
            }
        )
    return {"items": items, "paper_id": paper_id}


@academic_mcp.tool()
def get_related_papers(paper_id: str, limit: int = 5) -> Dict[str, Any]:
    """Get related / recommended papers for a Semantic Scholar paper id."""
    paper_id = (paper_id or "").strip()
    if not paper_id:
        raise ValueError("paper_id is required")
    limit = max(1, min(int(limit), 15))
    fields = "title,url,year,citationCount,authors,abstract"
    url = (
        f"{S2_GRAPH}/recommendations/v1/papers/forpaper/"
        f"{quote(paper_id, safe='')}?fields={fields}&limit={limit}"
    )
    # Recommendations API is under a different path in some versions —
    # fall back to search on title if this fails.
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/"
                f"{quote(paper_id, safe='')}?fields={fields}&limit={limit}",
                headers=_s2_headers(),
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"recommendations {resp.status_code}")
            payload = resp.json()
        items = []
        for paper in payload.get("recommendedPapers") or []:
            authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
            items.append(
                {
                    "title": paper.get("title") or "",
                    "url": paper.get("url") or "",
                    "content": (paper.get("abstract") or "")[:400],
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount"),
                    "authors": authors,
                }
            )
        return {"items": items, "paper_id": paper_id}
    except Exception as exc:
        logger.info("get_related_papers fallback: %s", exc)
        detail = get_paper(paper_id=paper_id)
        title = (detail.get("title") or "").strip()
        if not title:
            return {"items": [], "paper_id": paper_id, "error": str(exc)}
        return search_papers(query=title, limit=limit)
