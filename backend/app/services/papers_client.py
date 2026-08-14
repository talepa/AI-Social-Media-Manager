"""
services/papers_client.py

Feature 2: academic paper search.
Tries Semantic Scholar first; falls back to OpenAlex (free, generous limits).
Optional: SEMANTIC_SCHOLAR_API_KEY in .env for higher S2 limits.
"""

from __future__ import annotations

import logging
import os
from typing import List
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv

from app.schemas.research import ResearchItem

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)

USER_AGENT = "AI-Social-Media-Manager/0.2 (Feature2 papers; mailto:dev@localhost)"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_WORKS = "https://api.openalex.org/works"


def _s2_headers() -> dict:
    headers = {"User-Agent": USER_AGENT}
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if key:
        headers["x-api-key"] = key
    return headers


def _from_semantic_scholar(topic: str, limit: int) -> List[ResearchItem]:
    url = (
        f"{S2_SEARCH}?query={quote_plus(topic)}&limit={limit}"
        "&fields=title,abstract,url,year,authors,citationCount,venue,externalIds"
    )
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers=_s2_headers())
        if response.status_code == 429:
            raise RuntimeError("Semantic Scholar rate limit")
        if response.status_code != 200:
            raise RuntimeError(
                f"Semantic Scholar failed ({response.status_code}): "
                f"{response.text[:200]}"
            )
        payload = response.json()

    papers: List[ResearchItem] = []
    for item in payload.get("data") or []:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        paper_url = (item.get("url") or "").strip()
        if not paper_url:
            ext = item.get("externalIds") or {}
            arxiv_id = ext.get("ArXiv")
            doi = ext.get("DOI")
            if arxiv_id:
                paper_url = f"https://arxiv.org/abs/{arxiv_id}"
            elif doi:
                paper_url = f"https://doi.org/{doi}"
            else:
                paper_id = item.get("paperId") or ""
                paper_url = (
                    f"https://www.semanticscholar.org/paper/{paper_id}"
                    if paper_id
                    else ""
                )

        authors_raw = item.get("authors") or []
        authors: List[str] = []
        for a in authors_raw:
            if isinstance(a, dict):
                name = a.get("name")
                if isinstance(name, str) and name.strip():
                    authors.append(name.strip())
            if len(authors) >= 5:
                break

        year = item.get("year")
        abstract = (item.get("abstract") or "").strip()
        venue = (item.get("venue") or "").strip() or None
        citations = item.get("citationCount")

        papers.append(
            ResearchItem(
                title=title,
                url=paper_url or "https://www.semanticscholar.org",
                content=(abstract[:600] if abstract else ""),
                source="papers",
                published=str(year) if year else None,
                authors=authors or None,
                venue=venue,
                citation_count=int(citations) if citations is not None else None,
            )
        )
    return papers


def _from_openalex(topic: str, limit: int) -> List[ResearchItem]:
    url = f"{OPENALEX_WORKS}?search={quote_plus(topic)}&per_page={limit}"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(
            url,
            headers={"User-Agent": USER_AGENT},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAlex failed ({response.status_code}): {response.text[:200]}"
            )
        payload = response.json()

    papers: List[ResearchItem] = []
    for item in payload.get("results") or []:
        title = (item.get("display_name") or item.get("title") or "").strip()
        if not title:
            continue

        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        landing = primary.get("landing_page_url") or ""
        pdf = primary.get("pdf_url") or ""
        openalex_id = (item.get("id") or "").strip()
        doi = item.get("doi") or ""
        paper_url = landing or pdf or doi or openalex_id or "https://openalex.org"

        authorships = item.get("authorships") or []
        authors = []
        for a in authorships[:5]:
            author = (a or {}).get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        year = item.get("publication_year")
        abstract_inverted = item.get("abstract_inverted_index")
        abstract = ""
        if isinstance(abstract_inverted, dict):
            # Reconstruct rough abstract from inverted index
            positions: list[tuple[int, str]] = []
            for word, idxs in abstract_inverted.items():
                for i in idxs:
                    positions.append((i, word))
            positions.sort(key=lambda x: x[0])
            abstract = " ".join(w for _, w in positions)[:600]

        venue = source.get("display_name") if isinstance(source, dict) else None
        citations = item.get("cited_by_count")

        papers.append(
            ResearchItem(
                title=title,
                url=paper_url,
                content=abstract,
                source="papers",
                published=str(year) if year else None,
                authors=authors or None,
                venue=venue,
                citation_count=int(citations) if citations is not None else None,
            )
        )
    return papers


def search_papers(topic: str, limit: int = 5) -> List[ResearchItem]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    try:
        papers = _from_semantic_scholar(topic, limit)
        if papers:
            return papers
    except Exception as exc:
        logger.warning("Semantic Scholar unavailable (%s); trying OpenAlex", exc)

    papers = _from_openalex(topic, limit)
    if not papers:
        raise RuntimeError("No academic papers found from Semantic Scholar or OpenAlex")
    return papers
