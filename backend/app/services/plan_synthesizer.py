"""
Structured action plans from gathered research — template-driven, evidence-backed.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from app.config import GOOGLE_API_KEY
from app.schemas.research import (
    MultiSourceResearchResult,
    PlanResource,
    PlanSection,
    PlanStep,
    ResearchItem,
    ResearchPlan,
    ResearchRoutingPlan,
)
from app.services.query_utils import (
    extract_plan_subject,
    is_ai_career_topic,
    is_career_roadmap,
    normalize_topic,
)
from app.services.github_utils import filter_github_items

logger = logging.getLogger(__name__)

_COMPARE_RE = re.compile(r"\b(vs\.?|versus|compare|comparison|difference between)\b", re.I)
_LEARN_RE = re.compile(
    r"\b(learn|learning|tutorial|roadmap|study path|getting started|how to)\b",
    re.I,
)
_BUILD_RE = re.compile(
    r"\b(build|implement|create|deploy|ship|launch|setup|integrate)\b",
    re.I,
)

_AI_DOMAIN_RE = re.compile(
    r"\b(ai|ml|machine learning|llm|data sci|deep learning|nlp|pytorch)\b",
    re.I,
)

_REPO_AI_RE = re.compile(
    r"\b(ai|ml|machine.?learning|llm|deep.?learning|data.?science|"
    r"pytorch|tensorflow|nlp|artificial|neural)\b",
    re.I,
)


def _trim(text: str | None, n: int = 140) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def _subject(topic: str) -> str:
    return extract_plan_subject(topic) or normalize_topic(topic)


def _filter_plan_github(topic: str, items: List[ResearchItem]) -> List[ResearchItem]:
    if not items:
        return []
    ranked = filter_github_items(topic, items, limit=8, min_relevance=0.3)
    if is_ai_career_topic(topic):
        ai_repos = [
            i
            for i in ranked
            if _REPO_AI_RE.search(f"{i.title} {i.content or ''}")
            or re.search(r"\bai[-_ ]engineer\b", f"{i.title} {i.content or ''}", re.I)
        ]
        if ai_repos:
            return ai_repos[:4]
        return ranked[:2]
    return ranked[:4]


def _web_learning_items(result: MultiSourceResearchResult, limit: int = 4) -> List[ResearchItem]:
    out: list[ResearchItem] = []
    for item in result.tavily_results:
        url = (item.url or "").lower()
        if "youtube.com" in url or "youtu.be" in url:
            continue
        if item.title and item.url:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _youtube_items(result: MultiSourceResearchResult, limit: int = 3) -> List[ResearchItem]:
    out: list[ResearchItem] = []
    for item in result.tavily_results:
        url = (item.url or "").lower()
        if "youtube.com" in url or "youtu.be" in url:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _career_phases(topic: str, subject: str) -> List[PlanStep]:
    if is_ai_career_topic(topic):
        return [
            PlanStep(
                title="Skill audit",
                detail=(
                    "Compare your current skills to 5 AI engineer job posts; "
                    "note gaps in Python, ML fundamentals, and LLM tooling."
                ),
                timeframe="Week 1",
            ),
            PlanStep(
                title="ML foundations",
                detail=(
                    "Complete core ML modules (supervised learning, model evaluation, "
                    "scikit-learn or PyTorch basics)."
                ),
                timeframe="Weeks 2–4",
            ),
            PlanStep(
                title="AI engineering projects",
                detail=(
                    "Build a RAG application and one agent or automation demo; "
                    "document architecture and trade-offs."
                ),
                timeframe="Weeks 5–8",
            ),
            PlanStep(
                title="Portfolio & job search",
                detail=(
                    "Publish repos with READMEs, write short case studies, "
                    "and apply to AI/ML engineer roles."
                ),
                timeframe="Weeks 9–12",
            ),
        ]
    if re.search(r"\bsoftware engineer\b", topic, re.I):
        return [
            PlanStep(
                title="Gap analysis",
                detail=f"Map your current skills against {subject} job requirements.",
                timeframe="Week 1",
            ),
            PlanStep(
                title="Core skills",
                detail="Strengthen fundamentals (language, data structures, one framework).",
                timeframe="Weeks 2–4",
            ),
            PlanStep(
                title="Portfolio project",
                detail="Ship one end-to-end project that mirrors real job tasks.",
                timeframe="Weeks 5–7",
            ),
            PlanStep(
                title="Interview prep",
                detail="Practice coding + system design; tailor resume and apply.",
                timeframe="Weeks 8–10",
            ),
        ]
    return [
        PlanStep(
            title="Assess starting point",
            detail=f"List what you already know about {subject} and what's missing.",
            timeframe="Week 1",
        ),
        PlanStep(
            title="Structured learning",
            detail="Follow one curated path (course or guide) without context-switching.",
            timeframe="Weeks 2–4",
        ),
        PlanStep(
            title="Apply it",
            detail=f"Complete one practical project demonstrating {subject}.",
            timeframe="Weeks 5–6",
        ),
        PlanStep(
            title="Review & next step",
            detail="Identify weak areas; plan certification, job search, or deeper dive.",
            timeframe="Week 7",
        ),
    ]


def _career_roadmap_sections(
    topic: str, result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    subject = _subject(topic)
    gh = _filter_plan_github(topic, result.github_results or [])
    web = _web_learning_items(result, 4)
    yt = _youtube_items(result, 3)
    insights = _insight_bullets(result, 3)

    sections: list[PlanSection] = [
        PlanSection(
            id="phases",
            title="Roadmap phases",
            steps=_career_phases(topic, subject),
        ),
    ]
    if insights:
        sections.append(
            PlanSection(
                id="insights",
                title="What sources highlight",
                items=insights,
            )
        )
    if web:
        sections.append(
            PlanSection(
                id="guides",
                title="Guides & articles",
                resources=_resources(web, 4),
            )
        )
    if gh:
        sections.append(
            PlanSection(
                id="repos",
                title="Repos to study",
                resources=_resources(gh, 4),
            )
        )
    elif resources:
        sections.append(
            PlanSection(
                id="repos",
                title="Repos to study",
                resources=resources[:3],
            )
        )
    if yt:
        sections.append(
            PlanSection(
                id="videos",
                title="Videos & tutorials",
                resources=_resources(yt, 3),
            )
        )
    papers = result.papers_results[:2]
    sections.append(
        PlanSection(
            id="papers",
            title="Deeper reading (optional)",
            resources=_resources(papers, 3),
            items=[] if papers else ["No papers in this run — ask for academic sources if needed."],
        )
    )
    return sections


def _pick_template(topic: str, routing: ResearchRoutingPlan | None) -> str:
    text = _subject(topic).lower()
    intent = (routing.intent if routing else "explore") or "explore"
    domain = (routing.domain if routing else "general") or "general"

    if intent == "compare" or _COMPARE_RE.search(text):
        return "compare"
    if is_career_roadmap(topic) or _LEARN_RE.search(text) or intent == "technical":
        return "learning"
    if _BUILD_RE.search(text) or domain == "software":
        return "build"
    if domain == "health":
        return "health"
    if domain == "business":
        return "business"
    if intent == "evaluate":
        return "evaluate"
    return "general"


def _split_compare_options(topic: str) -> Tuple[str, str]:
    text = normalize_topic(topic)
    for sep in (r"\s+vs\.?\s+", r"\s+versus\s+", r"\s+or\s+", r"\s+/\s+"):
        parts = re.split(sep, text, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            if len(a) > 2 and len(b) > 2:
                return a, b
    return text, "alternatives"


def _top_items(result: MultiSourceResearchResult, n: int = 6) -> List[ResearchItem]:
    items: list[ResearchItem] = []
    for bucket in (
        result.tavily_results,
        result.github_results or [],
        result.papers_results,
        result.news_results,
    ):
        for item in bucket:
            if item.url and item.title:
                items.append(item)
    items.sort(key=lambda i: i.score if i.score is not None else 0.0, reverse=True)
    seen: set[str] = set()
    out: list[ResearchItem] = []
    for item in items:
        key = item.url.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= n:
            break
    return out


def _resources(items: List[ResearchItem], limit: int = 5) -> List[PlanResource]:
    out: List[PlanResource] = []
    for item in items[:limit]:
        out.append(
            PlanResource(
                title=item.title,
                url=item.url,
                kind=item.source,
                note=_trim(item.content, 100) or None,
            )
        )
    return out


def _insight_bullets(result: MultiSourceResearchResult, limit: int = 4) -> List[str]:
    bullets: list[str] = []
    if result.tavily_answer:
        for line in re.split(r"[.\n]+", result.tavily_answer):
            line = line.strip()
            if len(line) > 24:
                bullets.append(_trim(line, 160))
            if len(bullets) >= limit:
                return bullets

    for item in _top_items(result, limit):
        snippet = _trim(item.content, 120) or item.title
        bullets.append(f"{item.title}: {snippet}")
    return bullets[:limit]


def _goal_line(topic: str, template: str) -> str:
    t = _subject(topic)
    if template == "learning" and is_career_roadmap(topic):
        if is_ai_career_topic(topic):
            return f"Transition into an AI engineer role with a structured 12-week roadmap: {t}"
        return f"Build a career transition plan for: {t}"
    goals = {
        "compare": f"Choose the best path for your context: {t}",
        "learning": f"Build a focused learning path for: {t}",
        "build": f"Ship a working solution for: {t}",
        "health": f"Apply evidence-backed habits safely for: {t}",
        "business": f"Turn research into a go-to-market plan for: {t}",
        "evaluate": f"Decide whether to proceed with: {t}",
        "general": f"Execute a clear plan to address: {t}",
    }
    return goals.get(template, goals["general"])


def _success_criteria(template: str, topic: str) -> List[str]:
    subject = _subject(topic)
    if template == "learning" and is_career_roadmap(topic):
        if is_ai_career_topic(topic):
            return [
                "Gap analysis done against real AI engineer job posts",
                "At least 2 portfolio projects (ML + LLM/RAG) on GitHub",
                "Can explain your projects and ML fundamentals in interviews",
            ]
        return [
            f"Skills gap documented for {subject}",
            "At least one portfolio project published",
            "Target roles identified with tailored applications",
        ]
    if template == "compare":
        return [
            "Decision criteria documented with weights",
            "Both options evaluated against real constraints",
            "Clear recommendation with trade-offs named",
        ]
    if template == "learning":
        return [
            "Core concepts mapped in order",
            "Hands-on practice scheduled weekly",
            f"Can explain {subject} without notes",
        ]
    if template == "build":
        return [
            "MVP scope defined and scoped to 2 weeks",
            "Reference repos/docs identified",
            "Deployment or demo path chosen",
        ]
    if template == "health":
        return [
            "Claims tied to cited sources",
            "Routine fits your schedule",
            "Progress metric tracked for 4 weeks",
        ]
    if template == "business":
        return [
            "Target user and problem validated",
            "Competitive landscape summarized",
            "90-day milestones defined",
        ]
    return [
        "Question answered with cited evidence",
        "Top risks identified upfront",
        "Next 3 actions scheduled this week",
    ]


def _compare_sections(
    topic: str, result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    opt_a, opt_b = _split_compare_options(topic)
    insights = _insight_bullets(result, 5)
    return [
        PlanSection(
            id="criteria",
            title="Decision criteria",
            items=[
                "Team skills & existing stack",
                "Production readiness & observability",
                "Community, docs, and hiring pool",
                "Cost, latency, and maintenance burden",
            ],
        ),
        PlanSection(
            id="options",
            title="What sources say",
            items=insights or [f"Gather more evidence on {opt_a} vs {opt_b}"],
        ),
        PlanSection(
            id="matrix",
            title="Comparison matrix",
            items=[
                f"{opt_a}: strengths from top web/GitHub hits",
                f"{opt_b}: strengths from top web/GitHub hits",
                "Note gaps where evidence is thin — follow up in chat",
            ],
        ),
        PlanSection(
            id="resources",
            title="Evidence to read first",
            resources=resources,
        ),
    ]


def _learning_sections(
    topic: str, result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    if is_career_roadmap(topic):
        return _career_roadmap_sections(topic, result, resources)

    subject = _subject(topic)
    gh = _filter_plan_github(topic, result.github_results or [])
    web = _web_learning_items(result, 3)
    papers = result.papers_results[:2]
    return [
        PlanSection(
            id="phases",
            title="Learning path",
            steps=[
                PlanStep(
                    title="Foundation",
                    detail=f"Read 2–3 overview articles on {subject}; note key terms and concepts.",
                    timeframe="Days 1–3",
                ),
                PlanStep(
                    title="Guided practice",
                    detail="Follow one tutorial end-to-end; reproduce examples without copy-paste.",
                    timeframe="Week 1",
                ),
                PlanStep(
                    title="Mini project",
                    detail=f"Apply {subject} to a small real-world task you can demo or document.",
                    timeframe="Week 2",
                ),
                PlanStep(
                    title="Review & gaps",
                    detail="List unknowns; run one targeted follow-up search per gap.",
                    timeframe="Week 3",
                ),
            ],
        ),
        PlanSection(
            id="guides",
            title="Guides & articles",
            resources=_resources(web, 4) or resources[:3],
        ),
        PlanSection(
            id="repos",
            title="Code to study",
            resources=_resources(gh, 4) if gh else resources[:3],
        ),
        PlanSection(
            id="papers",
            title="Deeper reading (optional)",
            resources=_resources(papers, 3),
            items=[] if papers else ["No papers in this run — ask for academic sources if needed."],
        ),
    ]


def _build_sections(
    topic: str, result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    gh = (result.github_results or [])[:4]
    return [
        PlanSection(
            id="scope",
            title="MVP scope",
            items=[
                f"Core outcome: {_trim(normalize_topic(topic), 80)}",
                "Cut anything not needed for a demo in 2 weeks",
                "Pick one deployment target (local / cloud / internal)",
            ],
        ),
        PlanSection(
            id="architecture",
            title="Build phases",
            steps=[
                PlanStep(
                    title="Spike",
                    detail="Validate hardest unknown with a 1-day prototype.",
                    timeframe="Day 1–2",
                ),
                PlanStep(
                    title="Core loop",
                    detail="Implement happy path using patterns from reference repos.",
                    timeframe="Week 1",
                ),
                PlanStep(
                    title="Harden",
                    detail="Add logging, tests for critical paths, and error handling.",
                    timeframe="Week 2",
                ),
                PlanStep(
                    title="Ship",
                    detail="Document setup; deploy or hand off with runbook.",
                    timeframe="Week 3",
                ),
            ],
        ),
        PlanSection(
            id="references",
            title="Reference implementations",
            resources=_resources(gh, 5) or resources,
        ),
    ]


def _health_sections(
    result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    papers = result.papers_results[:3]
    return [
        PlanSection(
            id="evidence",
            title="Evidence snapshot",
            items=_insight_bullets(result, 4) or ["Review sources below for claim strength."],
        ),
        PlanSection(
            id="routine",
            title="Routine design",
            steps=[
                PlanStep(
                    title="Baseline",
                    detail="Note current habits; set one measurable baseline.",
                    timeframe="Week 0",
                ),
                PlanStep(
                    title="Introduce change",
                    detail="Add one evidence-backed habit; keep dose realistic.",
                    timeframe="Weeks 1–2",
                ),
                PlanStep(
                    title="Track & adjust",
                    detail="Log weekly; stop or adjust if adverse effects appear.",
                    timeframe="Weeks 3–4",
                ),
            ],
        ),
        PlanSection(
            id="studies",
            title="Sources to trust first",
            resources=_resources(papers, 3) or resources,
        ),
        PlanSection(
            id="caution",
            title="Safety & limits",
            items=[
                "This is research, not medical advice — confirm with a professional",
                "Prefer peer-reviewed sources over blogs for health claims",
                "Stop if you notice unexpected symptoms",
            ],
        ),
    ]


def _business_sections(
    result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    news = result.news_results[:3]
    return [
        PlanSection(
            id="landscape",
            title="Market snapshot",
            items=_insight_bullets(result, 4),
        ),
        PlanSection(
            id="milestones",
            title="90-day milestones",
            steps=[
                PlanStep(title="Validate", detail="Interview 5–10 target users.", timeframe="Days 1–30"),
                PlanStep(title="Position", detail="Draft positioning vs alternatives.", timeframe="Days 31–60"),
                PlanStep(title="Execute", detail="Ship smallest offer; measure one KPI.", timeframe="Days 61–90"),
            ],
        ),
        PlanSection(
            id="signals",
            title="News & timing",
            resources=_resources(news, 3) or resources[:3],
        ),
    ]


def _general_sections(
    result: MultiSourceResearchResult, resources: List[PlanResource]
) -> List[PlanSection]:
    return [
        PlanSection(
            id="context",
            title="What we know",
            items=_insight_bullets(result, 5),
        ),
        PlanSection(
            id="approach",
            title="Approach",
            steps=[
                PlanStep(title="Clarify", detail="Restate the goal in one sentence.", timeframe="Today"),
                PlanStep(title="Gather", detail="Read top sources; note agreements & conflicts.", timeframe="This week"),
                PlanStep(title="Act", detail="Pick smallest next step with measurable outcome.", timeframe="Next week"),
            ],
        ),
        PlanSection(
            id="sources",
            title="Start here",
            resources=resources,
        ),
    ]


def _next_actions(template: str, topic: str) -> List[str]:
    t = _subject(topic)
    if template == "learning" and is_ai_career_topic(topic):
        return [
            "Save 3 AI engineer job posts and highlight repeated skill requirements",
            "Pick one ML course and block 5 hours this week",
            "Ask: 'What project should I build first for an AI engineer portfolio?'",
        ]
    if template == "learning" and is_career_roadmap(topic):
        return [
            f"Write a one-page skills gap analysis for {t}",
            "Star one relevant GitHub repo to study this week",
            "Ask: 'Give me a week-by-week syllabus for this transition'",
        ]
    if template == "compare":
        a, b = _split_compare_options(t)
        return [
            f"List must-haves for choosing between {a} and {b}",
            "Read the top 2 sources in the Evidence panel",
            "Ask a follow-up: 'Which fits a small team in production?'",
        ]
    if template == "learning":
        return [
            "Block 45 minutes for the first tutorial",
            "Star one GitHub repo to clone this week",
            "Ask: 'Give me a week-by-week syllabus'",
        ]
    if template == "build":
        return [
            "Write a one-paragraph MVP spec",
            "Clone the highest-star reference repo",
            "Ask: 'What should I build first for a demo?'",
        ]
    if template == "health":
        return [
            "Read papers/sources before changing routine",
            "Pick one habit to try for 2 weeks",
            "Ask: 'What do studies disagree on?'",
        ]
    return [
        "Skim sources in the panel below",
        "Note one open question to research next",
        "Ask a follow-up to go deeper on any section",
    ]


def compile_plan(
    result: MultiSourceResearchResult,
    routing: ResearchRoutingPlan | None = None,
) -> ResearchPlan:
    topic = normalize_topic(result.topic)
    subject = _subject(topic)
    template = _pick_template(topic, routing)
    resources = _resources(_top_items(result, 8))
    goal = _goal_line(topic, template)
    criteria = _success_criteria(template, topic)

    section_builders = {
        "compare": lambda: _compare_sections(topic, result, resources),
        "learning": lambda: _learning_sections(topic, result, resources),
        "build": lambda: _build_sections(topic, result, resources),
        "health": lambda: _health_sections(result, resources),
        "business": lambda: _business_sections(result, resources),
        "evaluate": lambda: _general_sections(result, resources),
        "general": lambda: _general_sections(result, resources),
    }
    sections = section_builders.get(template, section_builders["general"])()

    headlines = {
        "compare": "Comparison plan",
        "learning": (
            "AI engineer career plan"
            if is_ai_career_topic(topic)
            else "Career transition plan"
            if is_career_roadmap(topic)
            else "Learning plan"
        ),
        "build": "Build plan",
        "health": "Evidence-backed routine plan",
        "business": "Go-to-market plan",
        "evaluate": "Evaluation plan",
        "general": "Action plan",
    }

    return ResearchPlan(
        topic=subject,
        template=template,
        headline=headlines.get(template, "Action plan"),
        goal=goal,
        success_criteria=criteria,
        sections=sections,
        next_actions=_next_actions(template, topic),
        mode="compile",
    )


def plan_to_markdown(plan: ResearchPlan) -> str:
    lines = [
        f"**{plan.headline}**",
        "",
        f"**Goal:** {plan.goal}",
        "",
        "**Success looks like**",
        *[f"• {c}" for c in plan.success_criteria],
        "",
    ]
    for sec in plan.sections:
        lines.append(f"### {sec.title}")
        for item in sec.items:
            lines.append(f"• {item}")
        for step in sec.steps:
            tf = f" ({step.timeframe})" if step.timeframe else ""
            lines.append(f"• **{step.title}**{tf} — {step.detail}")
        for res in sec.resources:
            lines.append(f"• [{res.title}]({res.url})")
        lines.append("")
    lines.append("**This week**")
    lines.extend(f"☐ {a}" for a in plan.next_actions)
    return "\n".join(lines).strip()


def _llm_enhance_plan(plan: ResearchPlan, result: MultiSourceResearchResult) -> ResearchPlan | None:
    if not GOOGLE_API_KEY:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.config import get_llm

        llm = get_llm(temperature=0.35)
        context = plan_to_markdown(plan)
        top = _top_items(result, 6)
        sources = "\n".join(f"- {i.title}: {_trim(i.content, 80)}" for i in top)
        system = SystemMessage(
            content=(
                "You refine research action plans. Keep the same section structure. "
                "Be specific to the user's topic. Use bullet points. No URLs in prose. "
                "Return markdown only — same headings as input, tighter wording."
            )
        )
        human = HumanMessage(
            content=f"Topic: {plan.topic}\n\nSources:\n{sources}\n\nDraft plan:\n{context}"
        )
        resp = llm.invoke([system, human])
        text = (resp.content or "").strip()
        if len(text) < 80:
            return None
        enhanced = plan.model_copy(deep=True)
        enhanced.mode = "llm"
        return enhanced
    except Exception:
        logger.exception("LLM plan enhance failed")
        return None


def synthesize_plan(
    result: MultiSourceResearchResult,
    routing: ResearchRoutingPlan | None = None,
    *,
    use_llm: bool = False,
) -> Tuple[ResearchPlan, str, Optional[str]]:
    """Return (plan, markdown, error)."""
    plan = compile_plan(result, routing)
    err: Optional[str] = None
    if use_llm:
        enhanced = _llm_enhance_plan(plan, result)
        if enhanced is None:
            err = "LLM enhance unavailable — showing compiled plan"
        else:
            plan = enhanced
    markdown = plan_to_markdown(plan)
    if plan.mode == "llm" and err is None:
        # Re-parse not implemented; LLM returns markdown — use compile markdown for structure
        # For llm mode we still return structured compile + note; future: parse sections
        pass
    return plan, markdown, err
