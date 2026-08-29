"""
services/source_quality.py

Filter scraped junk and off-topic sources before they become the user-facing answer.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from app.schemas.investigation import EvidenceClaim, ResearchFinding, SourceRecord

_JUNK_PHRASES = re.compile(
    r"(?i)\b("
    r"cookie|subscribe|newsletter|sign\s*up|log\s*in|discord|privacy policy|"
    r"terms of (use|service)|cc by|licensed under|all rights reserved|"
    r"share on|follow us|advertisement|sponsored|click here|add to cart|"
    r"official discord|for developers|revops|invoicing"
    r")\b"
)

_CAMEL_GLUE = re.compile(r"[a-z][A-Z]")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "what", "how", "why", "with", "from", "that", "this", "between", "vs",
    "versus", "into", "about", "their", "its", "be", "as", "by", "at",
}


def _tokens(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower())
        if w not in _STOP
    }


def is_junk_text(text: str) -> bool:
    """Heuristic: nav menus, license footers, glued UI chrome."""
    t = (text or "").strip()
    if not t:
        return True
    if len(t) < 40 and not re.search(r"[.!?]", t):
        # Very short non-sentence blurbs are usually titles-only; allow titles elsewhere
        pass
    if _JUNK_PHRASES.search(t) and len(t) < 280:
        return True
    # Dense CamelCase without spaces → scraped menu
    if len(_CAMEL_GLUE.findall(t)) >= 4 and t.count(" ") < 8:
        return True
    if re.search(r"(?i)^title:\s*", t) and "http" not in t.lower():
        # "Title: Foo # bar" study-site chrome often irrelevant
        if len(t) < 120:
            return True
    # German boilerplate / PDF front matter noise
    if re.search(r"(?i)\b(eine einführung|ressource erstellt|hochschuldidaktik)\b", t):
        return True
    return False


def relevance_score(query: str, *, title: str = "", content: str = "") -> float:
    q = _tokens(query)
    if not q:
        return 0.5
    doc = _tokens(f"{title} {content}")
    if not doc:
        return 0.0
    overlap = len(q & doc) / len(q)
    # Soft boost if any distinctive query term appears in title
    title_tok = _tokens(title)
    title_hit = len(q & title_tok) / max(1, min(4, len(q)))
    return min(1.0, 0.7 * overlap + 0.3 * title_hit)


def is_relevant_source(query: str, source: SourceRecord, *, min_score: float = 0.2) -> bool:
    text = f"{source.title or ''} {source.content or ''}"
    if is_junk_text(source.content or "") and is_junk_text(source.title or ""):
        return False
    if is_junk_text(source.content or "") and len((source.content or "")) > 80:
        # Junk body but maybe ok title — still require relevance
        pass
    if is_junk_text(source.content or "") and relevance_score(query, title=source.title or "", content="") < 0.35:
        return False
    return relevance_score(query, title=source.title or "", content=source.content or "") >= min_score


def filter_sources(
    query: str,
    sources: Sequence[SourceRecord],
    *,
    limit: int = 8,
    min_score: float = 0.22,
) -> List[SourceRecord]:
    scored: List[tuple[float, SourceRecord]] = []
    for s in sources:
        if is_junk_text(s.content or "") and len(_CAMEL_GLUE.findall(s.content or "")) >= 4:
            continue
        if is_junk_text(s.content or "") and _JUNK_PHRASES.search(s.content or ""):
            # Allow if title is strongly on-topic
            if relevance_score(query, title=s.title or "", content="") < 0.4:
                continue
        score = relevance_score(query, title=s.title or "", content=s.content or "")
        if score < min_score:
            continue
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Dedupe near-identical titles
    out: List[SourceRecord] = []
    seen_titles: set[str] = set()
    for _score, s in scored:
        key = re.sub(r"\W+", "", (s.title or "").lower())[:48]
        if key and key in seen_titles:
            continue
        if key:
            seen_titles.add(key)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def filter_findings(
    query: str,
    findings: Sequence[ResearchFinding],
    sources_by_id: dict[str, SourceRecord],
) -> List[ResearchFinding]:
    kept: List[ResearchFinding] = []
    for f in findings:
        if is_junk_text(f.claim) or is_junk_text(f.evidence_summary or ""):
            continue
        if relevance_score(query, title=f.claim, content=f.evidence_summary or "") < 0.18:
            continue
        # Drop findings whose sources were all filtered out
        if f.source_ids and not any(sid in sources_by_id for sid in f.source_ids):
            continue
        kept.append(f)
    return kept


def filter_claims(
    query: str,
    claims: Sequence[EvidenceClaim],
) -> List[EvidenceClaim]:
    kept: List[EvidenceClaim] = []
    for c in claims:
        if is_junk_text(c.claim):
            continue
        if relevance_score(query, title=c.claim, content="") < 0.18:
            continue
        kept.append(c)
    return kept
