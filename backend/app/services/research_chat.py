"""
Follow-up chat: answer from gathered sources or propose targeted research expansion.
"""

from __future__ import annotations

import logging
import re
from typing import List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import get_llm
from app.graphs.research_graph import run_multi_source_research
from app.schemas.research import MultiSourceResearchResult, ResearchItem, SourceType
from app.services.github_utils import (
    dedupe_github_items,
    extract_github_search_terms,
    filter_github_items,
    rank_github_items,
)
from app.services.result_classifier import reclassify_results
from app.services.plan_synthesizer import synthesize_plan
from app.services.topic_router import route_topic

logger = logging.getLogger(__name__)

RunMode = Literal["quick", "research", "deep", "plan"]

ChatTurn = dict[str, str]

_GITHUB_RE = re.compile(
    r"\b(github|repo|repos|repository|repositories|open.?source|sample project|codebase)\b",
    re.I,
)
_YOUTUBE_RE = re.compile(
    r"\b(youtube|youtu\.be|video|videos|watch|tutorial video|video tutorial)\b",
    re.I,
)
_LEARN_RE = re.compile(
    r"\b(learn|learning|tutorial|tutorials|course|courses|best way|how to start|"
    r"getting started|certification|study path|roadmap)\b",
    re.I,
)
_PLAN_RE = re.compile(
    r"\b(plan|roadmap|step by step|action plan|learning path|syllabus|"
    r"milestones|outline|strategy|steps to|how should i)\b",
    re.I,
)
_DEEP_RE = re.compile(
    r"\b(deep dive|comprehensive|thorough|in depth|full research|"
    r"detailed research|more sources|all sources|dig deeper)\b",
    re.I,
)
_SOURCES_RE = re.compile(
    r"\b(articles?|videos?|sources|repos?|github|youtube|find me|search for|"
    r"show me links|evidence|papers)\b",
    re.I,
)
_QUICK_RE = re.compile(
    r"\b(quick|brief|short answer|tl;dr|just tell me|summary only|keep it short)\b",
    re.I,
)
_STOP = {
    "the", "and", "for", "are", "what", "how", "does", "from", "with", "that",
    "this", "have", "any", "there", "about", "best", "way", "tell", "give",
}


class ResearchProposal(BaseModel):
    query: str
    sources: List[SourceType]
    reason: str


class ModeSwitchProposal(BaseModel):
    suggested_mode: RunMode
    reason: str
    query: str = ""


class ResearchChatResponse(BaseModel):
    answer: str
    action: Literal["none", "propose_research", "propose_mode_switch"] = "none"
    proposal: Optional[ResearchProposal] = None
    mode_proposal: Optional[ModeSwitchProposal] = None
    related: bool = True
    research: Optional[MultiSourceResearchResult] = None
    plan: Optional[dict] = None
    plan_markdown: Optional[str] = None


class FollowupAnalysis(BaseModel):
    mode: Literal["answer", "propose_research", "off_topic"] = "answer"
    query: str = ""
    sources: List[SourceType] = Field(default_factory=list)
    reason: str = ""
    user_message: str = ""


def _trim(text: str | None, n: int = 320) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOP}


def _format_items(label: str, items: List[ResearchItem], limit: int = 6) -> str:
    if not items:
        return ""
    lines = [f"{label} ({len(items)}):"]
    for item in items[:limit]:
        score = f" score={item.score:.2f}" if item.score is not None else ""
        lines.append(
            f"- {item.title}{score}\n  {_trim(item.content, 220)}\n  {item.url}"
        )
    return "\n".join(lines)


def build_research_context(result: MultiSourceResearchResult) -> str:
    parts = [f"Original question: {result.topic}"]
    if result.tavily_answer:
        parts.append(f"Web synthesis:\n{result.tavily_answer}")
    for block in (
        _format_items("Web sources", result.tavily_results),
        _format_items("News", result.news_results, 4),
        _format_items("Papers", result.papers_results, 4),
        _format_items("GitHub", result.github_results or [], 4),
    ):
        if block:
            parts.append(block)
    if result.report and result.report.executive_summary:
        parts.append(f"Report summary:\n{result.report.executive_summary}")
    return "\n\n".join(parts)


def _strip_urls(text: str) -> str:
    cleaned = re.sub(r"https?://\S+", "", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def build_opening_summary(result: MultiSourceResearchResult) -> str:
    if result.tavily_answer:
        return _strip_urls(result.tavily_answer.strip())[:900]

    top = (
        result.tavily_results[:3]
        + result.news_results[:2]
        + (result.github_results or [])[:2]
    )
    if not top:
        return (
            "Research is ready. Ask a follow-up — I'll keep chat short; "
            "links stay in the Evidence panel."
        )

    chunks = ["Quick take from sources:"]
    for item in top[:4]:
        chunks.append(f"• {item.title}")
    chunks.append("\nAsk a follow-up or check the tabs on the right for links.")
    return "\n".join(chunks)


def _all_text(result: MultiSourceResearchResult) -> str:
    parts = [result.topic, result.tavily_answer or ""]
    for items in (
        result.tavily_results,
        result.news_results,
        result.papers_results,
        result.github_results or [],
    ):
        for item in items:
            parts.extend([item.title, item.content or ""])
    return " ".join(parts).lower()


def _context_covers(question: str, research: MultiSourceResearchResult) -> bool:
    q_tokens = _tokens(question)
    if not q_tokens:
        return True
    blob = _all_text(research)
    hits = sum(1 for t in q_tokens if t in blob)
    return hits >= max(1, len(q_tokens) // 3)


_REFERS_SESSION_RE = re.compile(
    r"\b(these|those|them|their|it|this|that|same|above|"
    r"related to (?:these|this|them|it))\b",
    re.I,
)


def _refers_to_session(question: str) -> bool:
    return bool(_REFERS_SESSION_RE.search(question))


def _is_related(question: str, research: MultiSourceResearchResult) -> bool:
    if _refers_to_session(question):
        return True
    topic_t = _tokens(research.topic)
    q_t = _tokens(question)
    if topic_t & q_t:
        return True
    blob = _all_text(research)
    return any(t in blob for t in q_t if len(t) >= 4)


def _extract_subject(question: str, research: MultiSourceResearchResult) -> str:
    q_t = _tokens(question)
    topic_t = _tokens(research.topic)
    shared = sorted(q_t & topic_t, key=len, reverse=True)
    if shared:
        return " ".join(shared[:3])
    return research.topic


def _has_learning_snippets(research: MultiSourceResearchResult, subject: str) -> bool:
    blob = _all_text(research)
    subj = subject.lower()
    return subj in blob and bool(
        re.search(r"\b(tutorial|course|learn|certification|documentation|docs)\b", blob, re.I)
    )


_MODE_LABELS: dict[str, str] = {
    "quick": "Quick",
    "research": "Research",
    "deep": "Deep",
    "plan": "Plan",
}


def detect_mode_switch(question: str, current_mode: RunMode) -> Optional[ModeSwitchProposal]:
    q = question.strip()
    if not q:
        return None

    if _PLAN_RE.search(q) and current_mode != "plan":
        return ModeSwitchProposal(
            suggested_mode="plan",
            reason=(
                "You asked for a structured plan or roadmap. Plan mode focuses on "
                "steps and milestones instead of article summaries."
            ),
            query=q,
        )

    if current_mode == "plan" and (_SOURCES_RE.search(q) or _DEEP_RE.search(q)):
        return ModeSwitchProposal(
            suggested_mode="deep",
            reason=(
                "You asked for articles, videos, or deeper sources. Plan mode keeps "
                "evidence collapsed — Deep mode surfaces full source cards."
            ),
            query=q,
        )

    if _DEEP_RE.search(q) and current_mode in ("quick", "plan"):
        return ModeSwitchProposal(
            suggested_mode="deep",
            reason="This follow-up needs a broader, deeper source gather.",
            query=q,
        )

    if _QUICK_RE.search(q) and current_mode in ("deep", "research", "plan"):
        return ModeSwitchProposal(
            suggested_mode="quick",
            reason="You asked for a brief answer without a full evidence pass.",
            query=q,
        )

    if _SOURCES_RE.search(q) and current_mode == "quick":
        return ModeSwitchProposal(
            suggested_mode="research",
            reason="Finding articles and links works better in Research or Deep mode.",
            query=q,
        )

    return None


def _plan_followup_answer(question: str, research: MultiSourceResearchResult) -> tuple[str, dict, str]:
    plan, markdown, _err = synthesize_plan(research, research.routing, use_llm=False)
    headline = plan.headline or research.topic
    answer = (
        f"Updated plan for your follow-up — see structured sections below.\n\n"
        f"**{headline}**"
    )
    return answer, plan.model_dump(), markdown


def analyze_followup(
    question: str,
    research: MultiSourceResearchResult,
    *,
    current_mode: RunMode = "research",
) -> FollowupAnalysis:
    q = question.strip()
    if not _is_related(q, research):
        return FollowupAnalysis(
            mode="off_topic",
            query=q,
            sources=["tavily"],
            reason="This looks like a new topic outside the current research.",
            user_message=(
                "That seems like a new direction from your original question. "
                "I can run a fresh search — allow once, or start a new question from home."
            ),
        )

    if current_mode == "plan" and _PLAN_RE.search(q):
        return FollowupAnalysis(mode="answer")

    if _YOUTUBE_RE.search(q) and _GITHUB_RE.search(q):
        subject = _extract_subject(q, research)
        terms = " ".join(extract_github_search_terms(subject))
        return FollowupAnalysis(
            mode="propose_research",
            query=f"{terms} youtube tutorial".strip() if terms else subject,
            sources=["github", "tavily"],
            reason="Need separate YouTube and GitHub passes.",
            user_message=(
                f"I can search for **{subject}** YouTube tutorials and GitHub repos — "
                "allow once to add both tabs on the right."
            ),
        )

    if current_mode == "plan" and (_SOURCES_RE.search(q) or _YOUTUBE_RE.search(q) or _GITHUB_RE.search(q)):
        return FollowupAnalysis(
            mode="off_topic",
            query=q,
            sources=["tavily"],
            reason="Sources request in plan mode",
            user_message=(
                "You're in **Plan** mode — I can refine the plan, or switch to **Deep** "
                "mode to pull articles and videos. Allow a mode switch below if you want sources."
            ),
        )

    if _GITHUB_RE.search(q):
        github_n = len(research.github_results or [])
        if github_n > 1 and _context_covers(q, research):
            return FollowupAnalysis(mode="answer")
        subject = _extract_subject(q, research)
        terms = " ".join(extract_github_search_terms(subject))
        return FollowupAnalysis(
            mode="propose_research",
            query=terms or subject,
            sources=["github", "tavily"],
            reason="GitHub project search was not in the first gather (or returned too little).",
            user_message=(
                f"GitHub repos weren't in the first search. "
                f"I can fetch **{subject}** repositories — allow once or always allow."
            ),
        )

    if _YOUTUBE_RE.search(q):
        subject = _extract_subject(q, research)
        yt_in_web = sum(
            1
            for i in research.tavily_results
            if "youtube.com" in (i.url or "").lower() or "youtu.be" in (i.url or "").lower()
        )
        if yt_in_web >= 1 and _context_covers(q, research):
            return FollowupAnalysis(mode="answer")
        return FollowupAnalysis(
            mode="propose_research",
            query=f"{subject} youtube tutorial video learn",
            sources=["tavily"],
            reason="YouTube tutorials need a targeted video search.",
            user_message=(
                f"No YouTube videos in the current sources yet. "
                f"Search for **{subject}** tutorial videos?"
            ),
        )

    if _LEARN_RE.search(q):
        subject = _extract_subject(q, research)
        if _has_learning_snippets(research, subject) and _context_covers(q, research):
            return FollowupAnalysis(mode="answer")
        return FollowupAnalysis(
            mode="propose_research",
            query=f"how to learn {subject} best tutorials courses roadmap",
            sources=["tavily"],
            reason="Learning paths and tutorials need a focused web search.",
            user_message=(
                f"The current sources don't include learning resources for **{subject}**. "
                "Want me to search for tutorials, courses, and the best way to get started?"
            ),
        )

    if not _context_covers(q, research):
        plan = route_topic(q, run_mode="research")
        return FollowupAnalysis(
            mode="propose_research",
            query=q,
            sources=list(plan.sources),
            reason="Follow-up is on-topic but missing from gathered sources.",
            user_message=(
                "That's related to your research, but not in the sources we fetched yet. "
                f"Switch to a focused search for: “{q}”?"
            ),
        )

    return FollowupAnalysis(mode="answer")


def _dedupe_items(existing: List[ResearchItem], new: List[ResearchItem]) -> List[ResearchItem]:
    github_existing = [i for i in existing if i.source == "github"]
    github_new = [i for i in new if i.source == "github"]
    other_existing = [i for i in existing if i.source != "github"]
    other_new = [i for i in new if i.source != "github"]

    seen = {i.url.strip().lower() for i in other_existing if i.url}
    merged_other = list(other_existing)
    for item in other_new:
        key = item.url.strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged_other.append(item)

    merged_github = dedupe_github_items([*github_existing, *github_new])
    return merged_other + merged_github


def merge_research(
    base: MultiSourceResearchResult,
    extra: MultiSourceResearchResult,
) -> MultiSourceResearchResult:
    data = base.model_copy(deep=True)
    data.tavily_results = _dedupe_items(data.tavily_results, extra.tavily_results)
    data.news_results = _dedupe_items(data.news_results, extra.news_results)
    data.papers_results = _dedupe_items(data.papers_results, extra.papers_results)
    data.github_results = _dedupe_items(
        data.github_results or [], extra.github_results or []
    )
    if data.github_results:
        data.github_results = rank_github_items(data.topic, data.github_results)
        data.github_results = filter_github_items(
            data.topic,
            data.github_results,
            limit=12,
            min_relevance=0.15,
        )
    if extra.tavily_answer and not data.tavily_answer:
        data.tavily_answer = extra.tavily_answer
    for src in ("tavily", "news", "papers", "github"):
        if extra.errors.get(src):
            data.errors[src] = extra.errors[src]
    used = set(data.sources_used or [])
    used.update(extra.sources_used or [])
    data.sources_used = sorted(used)  # type: ignore[assignment]
    data.cached = False
    data.cache_key = None
    return reclassify_results(data)


def expand_research(
    *,
    research: MultiSourceResearchResult,
    query: str,
    sources: List[SourceType],
    limit: int = 6,
) -> MultiSourceResearchResult:
    extra = run_multi_source_research(
        topic=query.strip(),
        limit=limit,
        with_report=False,
        sources=list(sources),
        search_query=query.strip(),
    )
    return merge_research(research, extra)


def answer_from_context(
    *,
    question: str,
    research: MultiSourceResearchResult,
    history: Optional[List[ChatTurn]] = None,
    current_mode: RunMode = "research",
) -> str:
    history = history or []
    context = build_research_context(research)
    plan_hint = (
        "The user is in Plan mode. Focus on actionable steps, phases, and milestones. "
        "Do NOT push them to open article tabs — supporting sources stay collapsed.\n"
        if current_mode == "plan"
        else ""
    )
    ending_hint = (
        "End with one short line like: 'Ask if you want the plan refined or to switch to Deep mode for sources.'\n"
        if current_mode == "plan"
        else "End with one short line like: 'Open the YouTube or GitHub tab on the right for links.'\n"
    )
    system = SystemMessage(
        content=(
            "You are Atelier Research — a helpful research assistant in an ongoing session.\n"
            "Answer the user's follow-up using the research context below.\n"
            "Keep it SHORT: 2-5 bullet points, one line each when possible.\n"
            "Do NOT include URLs or markdown links — links appear in the Evidence panel.\n"
            "Name videos, repos, and articles by title only.\n"
            f"{plan_hint}"
            "When GitHub or YouTube results exist, summarize what each is for in plain language.\n"
            f"{ending_hint}"
            "Do not invent titles or stats not in the context.\n"
            "Never tell the user to ask a 'sharper follow-up question'.\n\n"
            f"--- Research context ---\n{context}"
        )
    )
    msgs = [system]
    for turn in history[-8:]:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant":
            msgs.append(AIMessage(content=content))
        else:
            msgs.append(HumanMessage(content=content))
    msgs.append(HumanMessage(content=question.strip()))

    try:
        llm = get_llm(temperature=0.35)
        resp = llm.invoke(msgs)
        text = (resp.content or "").strip()
        if text:
            return _strip_urls(text)
    except EnvironmentError:
        logger.info("research_chat: no GOOGLE_API_KEY, using fallback")
    except Exception as exc:
        logger.warning("research_chat LLM failed: %s", exc)

    return _fallback_answer(question, research)


def _fallback_answer(question: str, research: MultiSourceResearchResult) -> str:
    lines: list[str] = []
    yt = [
        i for i in research.tavily_results
        if "youtube.com" in (i.url or "").lower() or "youtu.be" in (i.url or "").lower()
    ]
    if yt:
        lines.append("YouTube:")
        for item in yt[:3]:
            lines.append(f"• {item.title}")
    if research.github_results:
        lines.append("GitHub:")
        for item in research.github_results[:4]:
            lines.append(f"• {item.title}")
    web = [
        i for i in research.tavily_results
        if i not in yt
    ]
    if web:
        lines.append("Web:")
        for item in web[:3]:
            lines.append(f"• {item.title}")
    if not lines:
        return "Browse the Evidence panel on the right for sources."
    lines.append("\nOpen the matching tab on the right for links.")
    return "\n".join(lines)


def handle_followup(
    *,
    question: str,
    research: MultiSourceResearchResult,
    history: Optional[List[ChatTurn]] = None,
    auto_expand: bool = False,
    current_mode: RunMode = "research",
) -> ResearchChatResponse:
    mode_switch = detect_mode_switch(question, current_mode)
    if mode_switch and mode_switch.suggested_mode != current_mode:
        label = _MODE_LABELS.get(mode_switch.suggested_mode, mode_switch.suggested_mode)
        return ResearchChatResponse(
            answer=(
                f"Your follow-up fits **{label}** mode better than "
                f"**{_MODE_LABELS.get(current_mode, current_mode)}**. "
                f"{mode_switch.reason} Allow a one-time switch?"
            ),
            action="propose_mode_switch",
            mode_proposal=mode_switch,
            related=True,
        )

    analysis = analyze_followup(question, research, current_mode=current_mode)

    if analysis.mode == "propose_research":
        if auto_expand and analysis.query and analysis.sources:
            expanded = expand_research(
                research=research,
                query=analysis.query,
                sources=analysis.sources,
            )
            answer = answer_from_context(
                question=question,
                research=expanded,
                history=history,
                current_mode=current_mode,
            )
            return ResearchChatResponse(
                answer=answer,
                action="none",
                related=analysis.mode != "off_topic",
                research=expanded,
            )
        return ResearchChatResponse(
            answer=analysis.user_message,
            action="propose_research",
            related=analysis.mode != "off_topic",
            proposal=ResearchProposal(
                query=analysis.query or question,
                sources=analysis.sources or ["tavily"],
                reason=analysis.reason,
            ),
        )

    if current_mode == "plan" and _PLAN_RE.search(question):
        answer, plan_data, markdown = _plan_followup_answer(question, research)
        return ResearchChatResponse(
            answer=answer,
            action="none",
            related=True,
            plan=plan_data,
            plan_markdown=markdown,
        )

    answer = answer_from_context(
        question=question,
        research=research,
        history=history,
        current_mode=current_mode,
    )
    return ResearchChatResponse(answer=answer, action="none", related=True)


# Backward-compatible alias
def answer_followup(
    *,
    question: str,
    research: MultiSourceResearchResult,
    history: Optional[List[ChatTurn]] = None,
) -> str:
    return handle_followup(
        question=question, research=research, history=history
    ).answer
