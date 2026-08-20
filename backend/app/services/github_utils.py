"""
GitHub URL normalization, deduplication, and relevance helpers.
"""

from __future__ import annotations

import math
import re
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from app.schemas.research import ResearchItem

_GITHUB_NOISE = re.compile(
    r"\b(github|repository|repositories|repo|repos|project|projects|example|"
    r"examples|tutorial|tutorials|video|videos|youtube|learn|learning|best|"
    r"any|there|related|these|those|them|this|that|open.?source|codebase|"
    r"search|find|show|give|tell|how|what|is|are|the|and|for|with)\b",
    re.I,
)

_GENERIC_REPO_RE = re.compile(
    r"(^|/)(awesome[-_]?|starred|my[-_]?awesome|awesome[-_]?list|"
    r"awesome[-_]?stars|365days|daily[-_]?ai|goodness)(/|$|[-_])",
    re.I,
)

_STOP = {
    "the", "and", "for", "are", "what", "how", "does", "from", "with", "that",
    "this", "have", "any", "there", "about", "best", "way", "tell", "give",
}


def normalize_github_repo_url(url: str) -> Optional[str]:
    """Canonical repo URL: https://github.com/owner/repo"""
    raw = (url or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    except Exception:
        return None
    host = parsed.netloc.replace("www.", "").lower()
    if host != "github.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if owner in {"topics", "marketplace", "features", "login", "settings"}:
        return None
    return f"https://github.com/{owner}/{repo}"


def repo_key(url: str) -> Optional[str]:
    canon = normalize_github_repo_url(url)
    if not canon:
        return None
    return canon.lower()


def extract_github_search_terms(topic: str, max_terms: int = 4) -> List[str]:
    """Pull focused keywords for GitHub search from a natural-language topic."""
    cleaned = _GITHUB_NOISE.sub(" ", topic or "")
    words = re.findall(r"[a-z0-9][a-z0-9._-]{1,}", cleaned.lower())
    terms: list[str] = []
    seen: set[str] = set()
    for w in words:
        w = w.strip("._-")
        if len(w) < 3 or w in _STOP or w in seen:
            continue
        seen.add(w)
        terms.append(w)
        if len(terms) >= max_terms:
            break
    if terms:
        return terms
    for w in re.findall(r"[a-z0-9]{3,}", (topic or "").lower()):
        if w not in _STOP and w not in seen:
            seen.add(w)
            terms.append(w)
        if len(terms) >= max_terms:
            break
    return terms or ["open-source"]


def build_github_search_query(topic: str) -> str:
    terms = extract_github_search_terms(topic)
    core = " ".join(terms)
    return f"{core} in:name,description fork:false archived:false"


def _topic_tokens(topic: str) -> set[str]:
    return set(extract_github_search_terms(topic, max_terms=8))


def _repo_slug(item: ResearchItem) -> str:
    title = (item.title or "").lower()
    url = normalize_github_repo_url(item.url or "") or ""
    slug = url.split("github.com/")[-1] if "github.com/" in url else title
    return f"{title} {slug}".replace("/", " ").replace("-", " ")


def github_relevance(topic: str, item: ResearchItem) -> float:
    tokens = _topic_tokens(topic)
    if not tokens:
        return 1.0
    text = f"{item.title} {item.content or ''}".lower()
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens)


def _name_relevance(topic: str, item: ResearchItem) -> float:
    tokens = _topic_tokens(topic)
    if not tokens:
        return 1.0
    slug = _repo_slug(item)
    hits = sum(1 for t in tokens if t in slug)
    return hits / len(tokens)


def _is_generic_list(item: ResearchItem) -> bool:
    slug = _repo_slug(item)
    return bool(_GENERIC_REPO_RE.search(slug))


def rank_score(topic: str, item: ResearchItem) -> float:
    """Higher = more relevant to the research topic."""
    tokens = _topic_tokens(topic)
    rel = github_relevance(topic, item)
    name_rel = _name_relevance(topic, item)
    slug = _repo_slug(item)

    score = rel * 0.35 + name_rel * 0.5

    if tokens:
        matched = [t for t in tokens if t in slug]
        if len(matched) >= 2:
            score += 0.3
        if len(matched) >= 3:
            score += 0.15

    if _is_generic_list(item):
        score -= 0.45

    stars = item.citation_count or 0
    score += min(math.log1p(max(stars, 0)) / 20.0, 0.1)

    return score


def rank_github_items(topic: str, items: Iterable[ResearchItem]) -> List[ResearchItem]:
    """Dedupe by repo and sort best matches first."""
    best: dict[str, ResearchItem] = {}
    scores: dict[str, float] = {}

    for item in items:
        key = repo_key(item.url)
        if not key:
            continue
        canon = normalize_github_repo_url(item.url) or item.url
        normalized = item.model_copy(update={"url": canon, "source": "github"})
        s = rank_score(topic, normalized)
        prev = scores.get(key, -999.0)
        if s > prev or (
            s == prev
            and (normalized.citation_count or 0) > (best.get(key).citation_count or 0)
        ):
            scores[key] = s
            best[key] = normalized

    return sorted(
        best.values(),
        key=lambda i: (scores.get(repo_key(i.url) or "", 0), i.citation_count or 0),
        reverse=True,
    )


def filter_github_items(
    topic: str,
    items: Iterable[ResearchItem],
    *,
    limit: int = 8,
    min_relevance: float = 0.2,
) -> List[ResearchItem]:
    """Dedupe, drop weak/generic matches, return top-ranked repos."""
    ranked = rank_github_items(topic, items)
    kept: list[ResearchItem] = []
    for item in ranked:
        rel = github_relevance(topic, item)
        name_rel = _name_relevance(topic, item)
        score = rank_score(topic, item)
        if _is_generic_list(item) and name_rel < 0.34:
            continue
        if rel < min_relevance and name_rel < min_relevance and score < 0.35:
            continue
        kept.append(item)
        if len(kept) >= limit:
            break
    if not kept and ranked:
        kept = ranked[:limit]
    return kept


def dedupe_github_items(items: Iterable[ResearchItem]) -> List[ResearchItem]:
    """Merge duplicate repos; keep entry with most stars (order not guaranteed)."""
    best: dict[str, ResearchItem] = {}
    for item in items:
        key = repo_key(item.url)
        if not key:
            continue
        canon = normalize_github_repo_url(item.url) or item.url
        normalized = item.model_copy(update={"url": canon, "source": "github"})
        prev = best.get(key)
        if prev is None or (normalized.citation_count or 0) > (prev.citation_count or 0):
            best[key] = normalized
    return list(best.values())
