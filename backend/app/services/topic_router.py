"""
services/topic_router.py

Auto-route research prompts to sources + depth without user-picked categories.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from app.schemas.research import (
    ResearchDomain,
    ResearchIntent,
    ResearchRoutingPlan,
    ResearchRunMode,
    RoutingMethod,
)
from app.services.research_categories import ALL_SOURCES, ResearchSource
from app.services.query_utils import (
    build_web_search_query,
    build_plan_search_query,
    core_search_phrase,
    extract_plan_subject,
    normalize_topic,
    wants_tutorial,
    wants_youtube,
)

logger = logging.getLogger(__name__)

_COMPARE_RE = re.compile(
    r"\b(vs\.?|versus|compare|comparison|difference between|better than)\b",
    re.I,
)
_EVALUATE_RE = re.compile(
    r"\b(should i|is it worth|pros and cons|evaluate|assessment|suitable for)\b",
    re.I,
)
_NEWS_RE = re.compile(
    r"\b(latest|today|breaking|headline|news|this week|this month|202[4-9])\b",
    re.I,
)
_ACADEMIC_EXPLICIT_RE = re.compile(
    r"\b(study|studies|peer-reviewed|meta-analysis|clinical trial|"
    r"systematic review|research paper|citation|citations|"
    r"evidence-based|journal article|scholarly)\b",
    re.I,
)
_TECH_RE = re.compile(
    r"\b(github|repo|repository|implement|library|api|sdk|codebase|langgraph|"
    r"python|typescript|docker|kubernetes|llm|rag|agent)\b",
    re.I,
)

_DOMAIN_PATTERNS: list[tuple[ResearchDomain, re.Pattern[str]]] = [
    (
        "health",
        re.compile(
            r"\b(health|nutrition|diet|vitamin|wellness|exercise|beetroot|beet root|"
            r"medical|symptom|therapy|mental health|sleep|calories|protein)\b",
            re.I,
        ),
    ),
    (
        "software",
        re.compile(
            r"\b(software|programming|developer|github|api|framework|database|"
            r"langgraph|openai|gemini|machine learning|neural|deploy)\b",
            re.I,
        ),
    ),
    (
        "business",
        re.compile(
            r"\b(startup|founder|saas|pricing|b2b|revenue|market|invest|"
            r"enterprise|go-to-market|plg)\b",
            re.I,
        ),
    ),
    (
        "science",
        re.compile(
            r"\b(physics|chemistry|biology|experiment|hypothesis|scientific|"
            r"climate|ecosystem|genome)\b",
            re.I,
        ),
    ),
    (
        "current_events",
        re.compile(
            r"\b(election|policy|regulation|war|sanction|announcement|"
            r"government|eu act|fda)\b",
            re.I,
        ),
    ),
]

_RUN_MODE_LIMITS: dict[ResearchRunMode, int] = {
    "quick": 4,
    "research": 6,
    "deep": 10,
    "plan": 6,
}


def _wants_academic_sources(text: str, intent: ResearchIntent) -> bool:
    """Papers only when the user clearly wants scholarly evidence."""
    if intent == "academic":
        return True
    return bool(_ACADEMIC_EXPLICIT_RE.search(text))


def _detect_intent(text: str) -> tuple[ResearchIntent, float]:
    if _COMPARE_RE.search(text):
        return "compare", 0.9
    if _EVALUATE_RE.search(text):
        return "evaluate", 0.85
    if _NEWS_RE.search(text):
        return "news", 0.82
    if _ACADEMIC_EXPLICIT_RE.search(text) or re.search(
        r"\b(research on|arxiv|journal paper)\b", text, re.I
    ):
        return "academic", 0.88
    if _TECH_RE.search(text):
        return "technical", 0.8
    return "explore", 0.55


def _detect_domain(text: str) -> tuple[ResearchDomain, float]:
    best: ResearchDomain = "general"
    best_score = 0.0
    for domain, pattern in _DOMAIN_PATTERNS:
        hits = len(pattern.findall(text))
        if hits > best_score:
            best_score = hits
            best = domain
    if best_score == 0:
        return "general", 0.45
    confidence = min(0.95, 0.55 + best_score * 0.15)
    return best, confidence


def _sources_for(
    domain: ResearchDomain,
    intent: ResearchIntent,
    run_mode: ResearchRunMode,
    text: str,
) -> list[ResearchSource]:
    wants_papers = _wants_academic_sources(text, intent)

    if run_mode == "plan":
        if intent == "compare" or _COMPARE_RE.search(text):
            return ["tavily", "github", "news"]
        if domain == "software" or intent == "technical":
            return ["tavily", "github", "papers"]
        if domain == "health":
            return ["tavily", "papers"]
        if domain == "business" or domain == "current_events":
            return ["tavily", "news"]
        if intent == "academic" or domain == "science":
            return ["papers", "tavily"]
        return ["tavily", "news"]

    # Video / tutorial asks — web only, YouTube-targeted query (skip noisy news)
    if wants_youtube(text) or (wants_tutorial(text) and domain in ("software", "general")):
        return ["tavily"]

    if run_mode == "quick":
        return ["tavily"]

    if intent == "news" or domain == "current_events":
        return ["news", "tavily"]

    if intent == "academic" or domain == "science":
        return ["papers", "tavily"]

    if intent == "technical" or domain == "software":
        sources: list[ResearchSource] = ["tavily", "github"]
        if wants_papers:
            sources.insert(1, "papers")
        return sources

    # Lifestyle / wellness health — web first; papers only if explicitly requested
    if domain == "health":
        if wants_papers:
            return ["tavily", "papers"]
        if run_mode == "deep":
            return ["tavily", "news"]
        return ["tavily"]

    if domain == "business":
        sources = ["tavily", "news"]
        if wants_papers:
            sources.append("papers")
        return sources

    if intent in ("compare", "evaluate"):
        sources = ["tavily", "news"]
        if wants_papers or domain == "software":
            if "papers" not in sources:
                sources.append("papers")
        if domain == "software":
            sources.append("github")
        return sources

    # General explore — web (+ news on deep); skip papers unless scholarly ask
    if run_mode == "deep":
        sources = ["tavily", "news"]
        if wants_papers:
            sources.append("papers")
        return sources

    return ["tavily", "news"]


def _legacy_category(domain: ResearchDomain, intent: ResearchIntent) -> str:
    if intent == "academic" or domain == "science":
        return "academic"
    if intent == "news" or domain == "current_events":
        return "news_desk"
    if intent == "technical" or domain == "software":
        return "ai_engineer"
    if domain == "business":
        return "founder"
    return "general"


def _build_queries(
    topic: str,
    domain: ResearchDomain,
    sources: list[ResearchSource],
) -> tuple[str, Optional[str]]:
    """Web/news use a normalized query; papers get a tighter scholarly query."""
    youtube = wants_youtube(topic)
    web_query = build_web_search_query(topic, youtube=youtube)
    papers_query: Optional[str] = None
    if "papers" in sources:
        if domain == "health":
            papers_query = f"{core_search_phrase(topic)} nutrition health benefits clinical study"
        elif domain == "software":
            papers_query = f"{core_search_phrase(topic)} software systems evaluation"
        else:
            papers_query = core_search_phrase(topic)
    return web_query, papers_query


def _compose_reason(
    domain: ResearchDomain,
    intent: ResearchIntent,
    run_mode: ResearchRunMode,
    sources: list[ResearchSource],
) -> str:
    src_labels = ", ".join(sources)
    extra = ""
    if run_mode == "plan":
        return (
            f"Plan mode · {domain.replace('_', ' ')} · {intent} "
            f"→ gather {src_labels}, then structured action template"
        )
    if "papers" not in sources:
        extra = " (web-focused — no academic papers for this question)"
    return (
        f"{domain.replace('_', ' ').title()} · {intent} · {run_mode} mode "
        f"→ {src_labels}{extra}"
    )


def _llm_route(topic: str, run_mode: ResearchRunMode) -> Optional[ResearchRoutingPlan]:
    if os.getenv("RESEARCH_LLM_ROUTING", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.config import get_llm

        llm = get_llm(temperature=0.2)
        system = SystemMessage(
            content=(
                "You route research questions. Reply with JSON only:\n"
                '{"domain":"general|health|software|business|science|current_events",'
                '"intent":"explore|compare|evaluate|news|academic|technical",'
                '"sources":["tavily","news","papers","github"],'
                '"search_query":"short search phrase",'
                '"confidence":0.0-1.0,"reason":"one sentence"}'
            )
        )
        human = HumanMessage(content=f"Topic: {topic}\nRun mode: {run_mode}")
        resp = llm.invoke([system, human])
        raw = (resp.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        sources = [s for s in data.get("sources", []) if s in ALL_SOURCES]
        if not sources:
            sources = ["tavily", "news", "papers"]
        limit = _RUN_MODE_LIMITS.get(run_mode, 6)
        domain = data.get("domain", "general")
        if domain not in {
            "general",
            "health",
            "software",
            "business",
            "science",
            "current_events",
        }:
            domain = "general"
        intent = data.get("intent", "explore")
        if intent not in {
            "explore",
            "compare",
            "evaluate",
            "news",
            "academic",
            "technical",
        }:
            intent = "explore"
        return ResearchRoutingPlan(
            topic=topic,
            search_query=(data.get("search_query") or topic).strip() or topic,
            papers_search_query=(data.get("papers_search_query") or None),
            domain=domain,
            intent=intent,
            run_mode=run_mode,
            sources=sources,
            limit=limit,
            confidence=float(data.get("confidence") or 0.75),
            reason=str(data.get("reason") or "LLM routing"),
            method="llm",
            category=_legacy_category(domain, intent),
        )
    except Exception:
        logger.exception("LLM routing failed for topic=%r", topic[:80])
        return None


def route_topic(
    topic: str,
    *,
    run_mode: ResearchRunMode = "research",
    use_llm_if_low_confidence: bool = True,
) -> ResearchRoutingPlan:
    """Infer domain, intent, sources, and limit from the user prompt."""
    cleaned = normalize_topic(" ".join((topic or "").strip().split()))
    if not cleaned:
        raise ValueError("topic must not be empty")

    text = cleaned.lower()
    intent, intent_conf = _detect_intent(text)
    domain, domain_conf = _detect_domain(text)
    confidence = (intent_conf + domain_conf) / 2

    if (
        use_llm_if_low_confidence
        and confidence < 0.62
        and os.getenv("RESEARCH_LLM_ROUTING", "").strip().lower()
        in {"1", "true", "yes"}
    ):
        llm_plan = _llm_route(cleaned, run_mode)
        if llm_plan is not None:
            return llm_plan

    sources = _sources_for(domain, intent, run_mode, text)
    limit = _RUN_MODE_LIMITS.get(run_mode, 6)
    category = _legacy_category(domain, intent)
    reason = _compose_reason(domain, intent, run_mode, sources)
    search_query, papers_search_query = _build_queries(cleaned, domain, sources)
    if run_mode == "plan":
        search_query = build_plan_search_query(cleaned)
        if domain == "software" or intent == "technical":
            papers_search_query = f"{extract_plan_subject(cleaned)} machine learning career"

    if confidence < 0.55:
        method: RoutingMethod = "fallback"
        reason = f"Low confidence — using safe mix. {reason}"
    else:
        method = "rules"

    return ResearchRoutingPlan(
        topic=cleaned,
        search_query=search_query,
        papers_search_query=papers_search_query,
        domain=domain,
        intent=intent,
        run_mode=run_mode,
        sources=sources,
        limit=limit,
        confidence=round(confidence, 3),
        reason=reason,
        method=method,
        category=category,
    )
