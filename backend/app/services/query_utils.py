"""
Normalize user queries and build focused search strings.
"""

from __future__ import annotations

import re
from typing import List

_TYPO_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpyton\b", re.I), "python"),
    (re.compile(r"\bteh\b", re.I), "the"),
    (re.compile(r"\bjavscript\b", re.I), "javascript"),
    (re.compile(r"\btypscript\b", re.I), "typescript"),
    (re.compile(r"\bstar\s+print\b", re.I), "star pattern print"),
]

_YOUTUBE_RE = re.compile(
    r"\b(youtube|youtu\.be|video|videos|watch|tutorial video|video tutorial)\b",
    re.I,
)

_TUTORIAL_RE = re.compile(
    r"\b(tutorial|how to|how do i|learn|walkthrough|step by step|guide to)\b",
    re.I,
)

_LEADING_NOISE = re.compile(
    r"^(?:please\s+)?(?:find|show|get|give me|search for|look for|any|some|"
    r"i need|i want|can you)\s+",
    re.I,
)

_TRAILING_NOISE = re.compile(
    r"\s+(?:please|thanks|thank you)\.?$",
    re.I,
)

_BOILERPLATE = re.compile(
    r"\b(youtube|video|videos|for|the|a|an|me|some|any|on|about)\b",
    re.I,
)

_STOP = {
    "the", "and", "for", "are", "what", "how", "does", "from", "with", "that",
    "this", "have", "any", "there", "about", "best", "way", "tell", "give",
    "youtube", "video", "videos", "tutorial", "watch", "find", "show",
}


def normalize_topic(topic: str) -> str:
    t = " ".join((topic or "").strip().split())
    if not t:
        return t
    for pattern, repl in _TYPO_FIXES:
        t = pattern.sub(repl, t)
    t = _LEADING_NOISE.sub("", t)
    t = _TRAILING_NOISE.sub("", t)
    return " ".join(t.split())


def wants_youtube(topic: str) -> bool:
    return bool(_YOUTUBE_RE.search(topic or ""))


def wants_tutorial(topic: str) -> bool:
    return bool(_TUTORIAL_RE.search(topic or ""))


def extract_search_terms(topic: str, *, max_terms: int = 6) -> List[str]:
    normalized = normalize_topic(topic)
    cleaned = _BOILERPLATE.sub(" ", normalized)
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
    return terms


def core_search_phrase(topic: str) -> str:
    terms = extract_search_terms(topic)
    if terms:
        return " ".join(terms)
    return normalize_topic(topic)


def build_web_search_query(topic: str, *, youtube: bool = False) -> str:
    core = core_search_phrase(topic)
    if youtube or wants_youtube(topic):
        return f"{core} tutorial site:youtube.com"
    if wants_tutorial(topic) and re.search(r"\b(python|javascript|typescript|react|langgraph|docker)\b", core, re.I):
        return f"{core} tutorial"
    return core or normalize_topic(topic)


def topic_tokens(topic: str) -> set[str]:
    return set(extract_search_terms(topic, max_terms=8))
