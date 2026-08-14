"""
services/reddit_client.py

Feature 1: fetch real Reddit posts via the official OAuth API.

Public *.reddit.com/search.json returns 403 for automated clients.
Create a free app at https://www.reddit.com/prefs/apps and set in .env:
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USER_AGENT (optional)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Set
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv

from app.schemas.research import RedditPost

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = (
    "startups",
    "entrepreneur",
    "SaaS",
    "smallbusiness",
    "artificial",
)

_EXCERPT_MAX = 400
_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _user_agent() -> str:
    return os.getenv(
        "REDDIT_USER_AGENT",
        "AI-Social-Media-Manager/0.1 (dev; Feature1 Reddit research)",
    )


def _client_id() -> str:
    return os.getenv("REDDIT_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("REDDIT_CLIENT_SECRET", "").strip()


def _excerpt(text: str) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= _EXCERPT_MAX:
        return text
    return text[: _EXCERPT_MAX - 1] + "…"


def _require_credentials() -> None:
    if not _client_id() or not _client_secret():
        raise RuntimeError(
            "Reddit OAuth credentials are required. "
            "Create a free app at https://www.reddit.com/prefs/apps "
            "(choose 'script'), then set REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET in your .env file."
        )


def _get_access_token(client: httpx.Client) -> str:
    now = time.time()
    cached = _token_cache.get("access_token")
    expires_at = float(_token_cache.get("expires_at") or 0)
    if cached and now < expires_at - 30:
        return str(cached)

    _require_credentials()
    response = client.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        auth=(_client_id(), _client_secret()),
        headers={"User-Agent": _user_agent()},
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Reddit OAuth token failed ({response.status_code}): {response.text[:300]}"
        )
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Reddit OAuth response missing access_token")
    expires_in = int(payload.get("expires_in") or 3600)
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + expires_in
    return str(token)


def _oauth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": _user_agent(),
        "Accept": "application/json",
    }


def _parse_listing(payload: Dict[str, Any]) -> List[RedditPost]:
    children = (payload.get("data") or {}).get("children") or []
    posts: List[RedditPost] = []
    for child in children:
        data = child.get("data") or {}
        if not data.get("title"):
            continue
        permalink = data.get("permalink") or ""
        if permalink and not permalink.startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"
        posts.append(
            RedditPost(
                title=data["title"],
                subreddit=data.get("subreddit") or "",
                score=int(data.get("score") or 0),
                num_comments=int(data.get("num_comments") or 0),
                url=data.get("url") or permalink,
                permalink=permalink or (data.get("url") or ""),
                selftext_excerpt=_excerpt(data.get("selftext") or ""),
                created_utc=data.get("created_utc"),
            )
        )
    return posts


def _get_oauth_json(client: httpx.Client, token: str, path: str) -> Dict[str, Any]:
    url = f"https://oauth.reddit.com{path}"
    response = client.get(url, headers=_oauth_headers(token))
    if response.status_code != 200:
        raise RuntimeError(
            f"Reddit API failed ({response.status_code}) for {path}: "
            f"{response.text[:200]}"
        )
    return response.json()


def search_reddit(topic: str, limit: int = 10) -> List[RedditPost]:
    """
    Search Reddit globally for `topic`, plus niche founder/startup subs.
    Dedupes by permalink and returns up to `limit` posts sorted by score desc.
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 50:
        limit = 50

    _require_credentials()

    encoded = quote_plus(topic)
    per_source = max(limit, 10)
    paths = [
        f"/search?q={encoded}&sort=relevance&t=month&limit={per_source}&raw_json=1",
    ]
    for sub in DEFAULT_SUBREDDITS:
        paths.append(
            f"/r/{sub}/search?q={encoded}&restrict_sr=1&sort=relevance"
            f"&t=month&limit=5&raw_json=1"
        )

    seen: Set[str] = set()
    collected: List[RedditPost] = []

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        token = _get_access_token(client)
        errors: List[str] = []
        for path in paths:
            try:
                payload = _get_oauth_json(client, token, path)
                for post in _parse_listing(payload):
                    key = post.permalink or post.url
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append(post)
            except Exception as exc:
                logger.warning("Reddit fetch failed for %s: %s", path, exc)
                errors.append(str(exc))

        if not collected and errors:
            raise RuntimeError(
                "All Reddit requests failed. Last error: " + errors[-1]
            )

    collected.sort(key=lambda p: (p.score, p.num_comments), reverse=True)
    return collected[:limit]
