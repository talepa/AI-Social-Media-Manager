"""
services/papers_client.py

Academic paper search across multiple free libraries in parallel:
  - Semantic Scholar
  - OpenAlex
  - Crossref
  - arXiv

Results are merged and deduped by title / DOI.
Optional: SEMANTIC_SCHOLAR_API_KEY for higher S2 rate limits.
"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv

from app.schemas.research import ResearchItem

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AI-Social-Media-Manager/0.3 (multi-library papers; mailto:dev@localhost)"
)
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_WORKS = "https://api.openalex.org/works"
CROSSREF_WORKS = "https://api.crossref.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"

_ATOM = "{http://www.w3.org/2005/Atom}"


def _s2_headers() -> dict:
    headers = {"User-Agent": USER_AGENT}
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if key:
        headers["x-api-key"] = key
    return headers


def _norm_title(title: str) -> str:
    t = (title or "").lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t)


def _doi_key(url: str) -> Optional[str]:
    u = (url or "").lower()
    if "doi.org/" in u:
        return u.split("doi.org/", 1)[-1].strip("/")
    if u.startswith("10."):
        return u.strip()
    return None


def _from_semantic_scholar(topic: str, limit: int) -> List[ResearchItem]:
    url = (
        f"{S2_SEARCH}?query={quote_plus(topic)}&limit={limit}"
        "&fields=title,abstract,url,year,authors,citationCount,venue,externalIds"
    )
    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
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
        if venue:
            venue = f"{venue} · Semantic Scholar"
        else:
            venue = "Semantic Scholar"

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

    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
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
            positions: list[tuple[int, str]] = []
            for word, idxs in abstract_inverted.items():
                for i in idxs:
                    positions.append((i, word))
            positions.sort(key=lambda x: x[0])
            abstract = " ".join(w for _, w in positions)[:600]

        venue = source.get("display_name") if isinstance(source, dict) else None
        if venue:
            venue = f"{venue} · OpenAlex"
        else:
            venue = "OpenAlex"
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


def _from_crossref(topic: str, limit: int) -> List[ResearchItem]:
    url = (
        f"{CROSSREF_WORKS}?query={quote_plus(topic)}&rows={limit}"
        "&select=DOI,title,author,published-print,published-online,"
        "container-title,abstract,is-referenced-by-count,URL"
    )
    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        if response.status_code != 200:
            raise RuntimeError(
                f"Crossref failed ({response.status_code}): {response.text[:200]}"
            )
        payload = response.json()

    papers: List[ResearchItem] = []
    for item in (payload.get("message") or {}).get("items") or []:
        titles = item.get("title") or []
        title = (titles[0] if titles else "").strip()
        if not title:
            continue

        doi = (item.get("DOI") or "").strip()
        paper_url = (item.get("URL") or "").strip()
        if not paper_url and doi:
            paper_url = f"https://doi.org/{doi}"

        authors = []
        for a in (item.get("author") or [])[:5]:
            given = (a.get("given") or "").strip()
            family = (a.get("family") or "").strip()
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        year = None
        for key in ("published-print", "published-online"):
            date_parts = ((item.get(key) or {}).get("date-parts") or [[]])[0]
            if date_parts:
                year = str(date_parts[0])
                break

        containers = item.get("container-title") or []
        venue = containers[0] if containers else None
        if venue:
            venue = f"{venue} · Crossref"
        else:
            venue = "Crossref"

        abstract = (item.get("abstract") or "").strip()
        if abstract.startswith("<"):
            try:
                abstract = "".join(ET.fromstring(f"<div>{abstract}</div>").itertext())
            except ET.ParseError:
                abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()[:600]

        cites = item.get("is-referenced-by-count")

        papers.append(
            ResearchItem(
                title=title,
                url=paper_url or "https://www.crossref.org",
                content=abstract,
                source="papers",
                published=year,
                authors=authors or None,
                venue=venue,
                citation_count=int(cites) if cites is not None else None,
            )
        )
    return papers


def _from_arxiv(topic: str, limit: int) -> List[ResearchItem]:
    url = (
        f"{ARXIV_API}?search_query=all:{quote_plus(topic)}"
        f"&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending"
    )
    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        if response.status_code != 200:
            raise RuntimeError(
                f"arXiv failed ({response.status_code}): {response.text[:200]}"
            )
        root = ET.fromstring(response.text)

    papers: List[ResearchItem] = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = (entry.findtext(f"{_ATOM}title") or "").strip()
        title = re.sub(r"\s+", " ", title)
        if not title:
            continue
        paper_url = (entry.findtext(f"{_ATOM}id") or "").strip()
        summary = (entry.findtext(f"{_ATOM}summary") or "").strip()
        summary = re.sub(r"\s+", " ", summary)[:600]
        published = (entry.findtext(f"{_ATOM}published") or "")[:4] or None

        authors = []
        for a in entry.findall(f"{_ATOM}author"):
            name = (a.findtext(f"{_ATOM}name") or "").strip()
            if name:
                authors.append(name)
            if len(authors) >= 5:
                break

        cats = entry.findall(f"{_ATOM}category")
        cat = cats[0].get("term") if cats else None
        venue = f"{cat} · arXiv" if cat else "arXiv"

        papers.append(
            ResearchItem(
                title=title,
                url=paper_url or "https://arxiv.org",
                content=summary,
                source="papers",
                published=published,
                authors=authors or None,
                venue=venue,
                citation_count=None,
            )
        )
    return papers


def _merge_papers(groups: List[List[ResearchItem]], limit: int) -> List[ResearchItem]:
    """Dedupe by DOI or normalized title; keep higher citation / richer abstract."""
    best: dict[str, ResearchItem] = {}
    order: List[str] = []

    for group in groups:
        for item in group:
            doi = _doi_key(item.url)
            key = f"doi:{doi}" if doi else f"title:{_norm_title(item.title)}"
            if not key.endswith(":") and key not in ("doi:", "title:"):
                existing = best.get(key)
                if existing is None:
                    best[key] = item
                    order.append(key)
                    continue
                # Prefer more citations, then longer abstract
                ex_c = existing.citation_count or -1
                new_c = item.citation_count or -1
                if new_c > ex_c or (
                    new_c == ex_c and len(item.content or "") > len(existing.content or "")
                ):
                    best[key] = item

    merged = [best[k] for k in order]
    merged.sort(
        key=lambda p: (
            p.citation_count if p.citation_count is not None else -1,
            len(p.content or ""),
        ),
        reverse=True,
    )
    return merged[:limit]


def search_papers(topic: str, limit: int = 5) -> List[ResearchItem]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    # Pull a bit more from each library, then merge down to `limit`
    per_source = max(limit, min(limit + 2, 10))

    fetchers = [
        ("semantic_scholar", _from_semantic_scholar),
        ("openalex", _from_openalex),
        ("crossref", _from_crossref),
        ("arxiv", _from_arxiv),
    ]

    groups: List[List[ResearchItem]] = []
    errors: List[str] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fn, topic, per_source): name for name, fn in fetchers
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                papers = fut.result()
                if papers:
                    groups.append(papers)
                    logger.info("papers/%s returned %s", name, len(papers))
            except Exception as exc:
                logger.warning("papers/%s failed: %s", name, exc)
                errors.append(f"{name}: {exc}")

    merged = _merge_papers(groups, limit)
    if not merged:
        detail = "; ".join(errors) if errors else "no results"
        raise RuntimeError(f"No academic papers found ({detail})")
    return merged
