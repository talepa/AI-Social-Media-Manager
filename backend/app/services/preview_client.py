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
    "Mozilla/5.0 (compatible; AI-Social-Media-Manager/0.3; "
    "preview; +https://localhost; research desk)"
)
_OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
    re.I,
)
_TWITTER_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_TWITTER_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
    re.I,
)
_ICON_RE = re.compile(
    r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\']+)["\']',
    re.I,
)


def _https_upgrade(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url or None


def favicon_for_url(page_url: str) -> Optional[str]:
    try:
        host = urlparse(page_url).hostname
        if not host:
            return None
        return f"https://www.google.com/s2/favicons?domain={host}&sz=128"
    except Exception:
        return None


def _absolutize(base: str, maybe: str) -> str:
    maybe = (maybe or "").strip()
    if not maybe:
        return ""
    return urljoin(base, maybe)


def resolve_article_url(page_url: str, *, timeout: float = 6.0) -> str:
    """
    Follow redirects for Google News / link wrappers to the publisher URL.
    Returns the original URL if resolution fails.
    """
    page_url = (page_url or "").strip()
    if not page_url.startswith("http"):
        return page_url
    host = (urlparse(page_url).hostname or "").lower()
    if "news.google.com" not in host and "news.google." not in host:
        return page_url
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        ) as client:
            # GET is more reliable than HEAD for Google News article links
            with client.stream("GET", page_url) as response:
                final = str(response.url)
                # Consume a tiny bit so redirects settle
                for _ in response.iter_bytes():
                    break
                if final.startswith("http") and "news.google." not in (
                    urlparse(final).hostname or ""
                ):
                    return final
    except Exception:
        logger.debug("resolve_article_url failed for %s", page_url, exc_info=True)
    return page_url


def fetch_og_image(page_url: str, *, timeout: float = 4.0) -> Optional[str]:
    """
    GET the page (capped) and parse og:image / twitter:image.
    Returns absolute https image URL or None.
    """
    page_url = (page_url or "").strip()
    if not page_url.startswith("http"):
        return None

    # Resolve Google News wrappers first so we scrape the publisher page
    page_url = resolve_article_url(page_url)

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        ) as client:
            with client.stream("GET", page_url) as response:
                if response.status_code >= 400:
                    return None
                ctype = (response.headers.get("content-type") or "").lower()
                if ctype and "html" not in ctype and "text/" not in ctype and "xml" not in ctype:
                    return None
                final_url = str(response.url)
                chunks: List[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= 120_000:
                        break
                html = b"".join(chunks).decode("utf-8", errors="ignore")
    except Exception:
        logger.debug("preview fetch failed for %s", page_url, exc_info=True)
        return None

    for pattern in (_OG_RE, _OG_RE_ALT, _TWITTER_RE, _TWITTER_RE_ALT):
        m = pattern.search(html)
        if m:
            abs_url = _https_upgrade(_absolutize(final_url, m.group(1)))
            if abs_url and abs_url.startswith("http"):
                return abs_url
    return None


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

    prepared: List[ResearchItem] = []
    need_fetch: List[Tuple[int, ResearchItem]] = []
    for idx, item in enumerate(items_list):
        url = item.url
        # Prefer resolved publisher URLs for news wrappers
        if "news.google." in (urlparse(url).hostname or ""):
            resolved = resolve_article_url(url)
            if resolved != url:
                url = resolved
        fav = item.favicon_url or favicon_for_url(url)
        image = _https_upgrade(item.image_url)
        updated = item.model_copy(
            update={"url": url, "image_url": image, "favicon_url": fav}
        )
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
                results[idx] = base.model_copy(update={"image_url": _https_upgrade(image)})

    out: List[ResearchItem] = []
    for i, item in enumerate(prepared):
        out.append(results.get(i, item))
    return out


def backfill_images_from_media(
    items: List[ResearchItem],
    media_urls: List[str],
) -> List[ResearchItem]:
    """
    Assign leftover gallery images to items still missing thumbnails.
    Prefer same-domain matches when possible.
    """
    if not items or not media_urls:
        return items

    used = {i.image_url for i in items if i.image_url}
    pool = [_https_upgrade(u) for u in media_urls if u]
    pool = [u for u in pool if u and u not in used]

    def domain(u: str) -> str:
        return (urlparse(u).hostname or "").lower().removeprefix("www.")

    out: List[ResearchItem] = []
    for item in items:
        if item.image_url:
            out.append(item)
            continue
        item_host = domain(item.url)
        pick: Optional[str] = None
        for i, media in enumerate(pool):
            if item_host and item_host in domain(media):
                pick = pool.pop(i)
                break
        if not pick and pool:
            pick = pool.pop(0)
        if pick:
            out.append(item.model_copy(update={"image_url": pick}))
        else:
            out.append(item)
    return out


def collect_media_urls(
    *groups: List[ResearchItem],
    extra: Optional[List[str]] = None,
    limit: int = 18,
) -> List[str]:
    seen = set()
    urls: List[str] = []
    for u in extra or []:
        u = _https_upgrade(u)
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    for group in groups:
        for item in group:
            img = _https_upgrade(item.image_url)
            if img and img not in seen:
                seen.add(img)
                urls.append(img)
            if len(urls) >= limit:
                return urls
    return urls
