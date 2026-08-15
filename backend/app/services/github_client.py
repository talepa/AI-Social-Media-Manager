"""
services/github_client.py

Search public GitHub repositories for a research topic.
Uses the GitHub Search API (optional GITHUB_TOKEN for higher rate limits).
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

GITHUB_SEARCH = "https://api.github.com/search/repositories"
USER_AGENT = "AI-Social-Media-Manager/0.4 (research desk)"


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_github_repos(topic: str, limit: int = 8) -> List[ResearchItem]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 20:
        limit = 20

    # Prefer relevant repos: topic words + stars boost via sort
    query = f"{topic} in:name,description,readme"
    url = (
        f"{GITHUB_SEARCH}?q={quote_plus(query)}"
        f"&sort=stars&order=desc&per_page={limit}"
    )

    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        response = client.get(url, headers=_headers())
        if response.status_code == 403:
            raise RuntimeError(
                "GitHub rate limit — set GITHUB_TOKEN in .env for higher limits"
            )
        if response.status_code == 401:
            raise RuntimeError("GitHub auth failed — check GITHUB_TOKEN")
        if response.status_code != 200:
            raise RuntimeError(
                f"GitHub search failed ({response.status_code}): "
                f"{response.text[:200]}"
            )
        payload = response.json()

    items: List[ResearchItem] = []
    for repo in payload.get("items") or []:
        full_name = (repo.get("full_name") or "").strip()
        name = (repo.get("name") or full_name or "").strip()
        html_url = (repo.get("html_url") or "").strip()
        if not name or not html_url:
            continue

        description = (repo.get("description") or "").strip()
        language = (repo.get("language") or "").strip() or None
        stars = repo.get("stargazers_count")
        forks = repo.get("forks_count")
        updated = (repo.get("updated_at") or "")[:10] or None
        owner = ((repo.get("owner") or {}).get("login") or "").strip()
        topics = repo.get("topics") or []
        topic_bits = ", ".join(str(t) for t in topics[:6] if t)

        meta_parts = []
        if stars is not None:
            meta_parts.append(f"{stars} stars")
        if forks is not None:
            meta_parts.append(f"{forks} forks")
        if language:
            meta_parts.append(language)
        if topic_bits:
            meta_parts.append(topic_bits)

        content = description
        if meta_parts:
            content = f"{description} — {' · '.join(meta_parts)}".strip(" —")

        avatar = ((repo.get("owner") or {}).get("avatar_url") or "").strip() or None

        items.append(
            ResearchItem(
                title=full_name or name,
                url=html_url,
                content=content[:600],
                source="github",
                published=updated,
                authors=[owner] if owner else None,
                venue=f"{language} · GitHub" if language else "GitHub",
                citation_count=int(stars) if stars is not None else None,
                image_url=avatar,
                favicon_url="https://www.google.com/s2/favicons?domain=github.com&sz=64",
            )
        )

    return items
