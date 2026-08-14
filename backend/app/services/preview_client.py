"""
services/preview_client.py

Fetch real page previews: Open Graph images + favicons.
No LLM — HTML meta tags / well-known icon endpoints only.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

from app.schemas.research import ResearchItem

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AI-Social-Media-Manager/0.3 (preview; +https://localhost; research desk)"
)
_OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.I,
)
_TWITTER_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_ICON_RE = re.compile(
    r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\']+)["\']',
    re.I,
)


def favicon_for_url(page_url: str) -> Optional[str]:
    try:
        host = urlparse(page_url).hostname
        if not host:
            return None
        return f"https://www.google.com/s2/favicons?domain={host}&sz=64"
    except Exception:
        return None


def _absolutize(base: str, maybe: str) -> str:
    maybe = (maybe or "").strip()
    if not maybe:
        return ""
    return urljoin(base, maybe)


def fetch_og_image(page_url: str, *, timeout: float = 2.5) -> Optional[str]:
    """
    GET the page (capped) and parse og:image / twitter:image.
    Returns absolute image URL or None.
    """
    page_url = (page_url or "").strip()
    if not page_url.startswith("http"):
        return None
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        ) as client:
            with client.stream("GET", page_url) as response:
                if response.status_code >= 400:
                    return None
                ctype = (response.headers.get("content-type") or "").lower()
                if "html" not in ctype and "text/" not in ctype and ctype:
                    return None
                final_url = str(response.url)
                chunks: List[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= 80_000:
                        break
                html = b"".join(chunks).decode("utf-8", errors="ignore")
    except Exception:
        logger.debug("preview fetch failed for %s", page_url, exc_info=True)
        return None

    for pattern in (_OG_RE, _OG_RE_ALT, _TWITTER_RE):
        m = pattern.search(html)
        if m:
            abs_url = _absolutize(final_url, m.group(1))
            if abs_url.startswith("http"):
                return abs_url
    return None


def _enrich_one(item: ResearchItem) -> ResearchItem:
    fav = item.favicon_url or favicon_for_url(item.url)
    image = item.image_url
    if not image:
        image = fetch_og_image(item.url)
    return item.model_copy(update={"image_url": image, "favicon_url": fav})


def enrich_items_with_previews(
    items: Iterable[ResearchItem],
    *,
    max_workers: int = 6,
    max_fetch: int = 10,
) -> List[ResearchItem]:
    """
    Attach favicons to all items; fetch og:image for items missing image_url
    (capped for speed).
    """
    items_list = list(items)
    if not items_list:
        return []

    # Always set favicon without network to page
    prepared: List[ResearchItem] = []
    need_fetch: List[Tuple[int, ResearchItem]] = []
    for idx, item in enumerate(items_list):
        fav = item.favicon_url or favicon_for_url(item.url)
        updated = item.model_copy(update={"favicon_url": fav})
        prepared.append(updated)
        if not updated.image_url and len(need_fetch) < max_fetch:
            need_fetch.append((idx, updated))

    if not need_fetch:
        return prepared

    results: Dict[int, ResearchItem] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fetch_og_image, item.url): idx for idx, item in need_fetch
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                image = fut.result()
            except Exception:
                image = None
            base = prepared[idx]
            if image:
                results[idx] = base.model_copy(update={"image_url": image})

    out: List[ResearchItem] = []
    for i, item in enumerate(prepared):
        out.append(results.get(i, item))
    return out


def collect_media_urls(
    *groups: List[ResearchItem],
    extra: Optional[List[str]] = None,
    limit: int = 18,
) -> List[str]:
    seen = set()
    urls: List[str] = []
    for u in extra or []:
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    for group in groups:
        for item in group:
            if item.image_url and item.image_url not in seen:
                seen.add(item.image_url)
                urls.append(item.image_url)
            if len(urls) >= limit:
                return urls
    return urls
