"""
mcp/servers/repository.py — Repository Intelligence MCP.

Wraps GitHub search + repository detail endpoints.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

import httpx
from mcp.server.mcpserver import MCPServer

from app.services.github_client import search_github_repos

logger = logging.getLogger(__name__)

repository_mcp = MCPServer(
    "repository",
    instructions=(
        "Repository Intelligence MCP: GitHub search and repository health signals. "
        "Use search_repositories to find projects, then get_repository / "
        "get_release_history / get_activity / get_issue_summary for a specific repo."
    ),
)

GITHUB_API = "https://api.github.com"
USER_AGENT = "AtelierResearch/1.0 (repository-mcp)"
_REPO_RE = re.compile(
    r"^(?:https?://github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_repo(repo: str) -> tuple[str, str]:
    repo = (repo or "").strip()
    m = _REPO_RE.match(repo)
    if not m:
        raise ValueError(
            "repo must be 'owner/name' or a github.com URL (e.g. openai/whisper)"
        )
    return m.group(1), m.group(2)


def _items_payload(items: List[Any]) -> Dict[str, Any]:
    return {
        "items": [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in items
        ]
    }


@repository_mcp.tool()
def search_repositories(query: str, limit: int = 8) -> Dict[str, Any]:
    """Search GitHub repositories by topic/query."""
    results = search_github_repos(topic=query, limit=max(1, min(limit, 15)))
    return _items_payload(results)


@repository_mcp.tool()
def get_repository(repo: str) -> Dict[str, Any]:
    """Get repository metadata (stars, forks, language, topics, description)."""
    owner, name = _parse_repo(repo)
    url = f"{GITHUB_API}/repos/{owner}/{name}"
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_headers())
        if resp.status_code == 404:
            return {"error": "repository not found", "repo": f"{owner}/{name}"}
        resp.raise_for_status()
        data = resp.json()
    return {
        "title": data.get("full_name") or f"{owner}/{name}",
        "url": data.get("html_url") or f"https://github.com/{owner}/{name}",
        "content": (data.get("description") or "")[:600],
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "language": data.get("language"),
        "topics": data.get("topics") or [],
        "license": ((data.get("license") or {}) or {}).get("spdx_id"),
        "pushed_at": data.get("pushed_at"),
        "created_at": data.get("created_at"),
        "archived": data.get("archived"),
        "default_branch": data.get("default_branch"),
    }


@repository_mcp.tool()
def get_release_history(repo: str, limit: int = 5) -> Dict[str, Any]:
    """List recent GitHub releases for a repository."""
    owner, name = _parse_repo(repo)
    limit = max(1, min(int(limit), 20))
    url = f"{GITHUB_API}/repos/{owner}/{name}/releases?per_page={limit}"
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_headers())
        if resp.status_code == 404:
            return {"items": [], "error": "repository not found"}
        resp.raise_for_status()
        releases = resp.json()
    items = []
    for rel in releases or []:
        items.append(
            {
                "title": rel.get("name") or rel.get("tag_name") or "",
                "url": rel.get("html_url") or "",
                "content": (rel.get("body") or "")[:400],
                "tag": rel.get("tag_name"),
                "published": (rel.get("published_at") or "")[:10] or None,
                "prerelease": rel.get("prerelease"),
            }
        )
    return {"items": items, "repo": f"{owner}/{name}"}


@repository_mcp.tool()
def get_activity(repo: str, limit: int = 8) -> Dict[str, Any]:
    """Recent commit activity on the default branch."""
    owner, name = _parse_repo(repo)
    limit = max(1, min(int(limit), 20))
    url = f"{GITHUB_API}/repos/{owner}/{name}/commits?per_page={limit}"
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_headers())
        if resp.status_code == 404:
            return {"items": [], "error": "repository not found"}
        resp.raise_for_status()
        commits = resp.json()
    items = []
    for c in commits or []:
        commit = c.get("commit") or {}
        author = (commit.get("author") or {}).get("name") or ""
        message = (commit.get("message") or "").split("\n", 1)[0]
        date = ((commit.get("author") or {}).get("date") or "")[:10] or None
        items.append(
            {
                "title": message[:120],
                "url": c.get("html_url") or "",
                "content": f"{author} · {date}" if author or date else "",
                "sha": (c.get("sha") or "")[:7],
                "author": author,
                "published": date,
            }
        )
    return {"items": items, "repo": f"{owner}/{name}"}


@repository_mcp.tool()
def get_issue_summary(repo: str, limit: int = 5) -> Dict[str, Any]:
    """Summarize open issues (count + recent titles)."""
    owner, name = _parse_repo(repo)
    limit = max(1, min(int(limit), 20))
    meta = get_repository(repo=f"{owner}/{name}")
    url = (
        f"{GITHUB_API}/repos/{owner}/{name}/issues"
        f"?state=open&per_page={limit}&sort=updated"
    )
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_headers())
        if resp.status_code == 404:
            return {"items": [], "error": "repository not found"}
        resp.raise_for_status()
        issues = resp.json()
    items = []
    for issue in issues or []:
        # Pull requests also appear in /issues — skip them
        if issue.get("pull_request"):
            continue
        items.append(
            {
                "title": issue.get("title") or "",
                "url": issue.get("html_url") or "",
                "content": (issue.get("body") or "")[:300],
                "number": issue.get("number"),
                "labels": [lb.get("name") for lb in (issue.get("labels") or []) if lb.get("name")],
                "published": (issue.get("updated_at") or "")[:10] or None,
            }
        )
    return {
        "items": items,
        "repo": f"{owner}/{name}",
        "open_issues": meta.get("open_issues"),
        "title": f"{owner}/{name} open issues",
        "url": f"https://github.com/{owner}/{name}/issues",
        "content": f"{meta.get('open_issues', '?')} open issues",
    }
