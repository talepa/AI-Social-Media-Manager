"""
agents/director.py

Research Director: turns a raw technical question into a structured,
bounded InvestigationPlan. First AI role in the Director -> Specialists ->
Evidence -> Synthesis pipeline (see graphs/investigation_graph.py).

Gemini decomposes the question into sub-questions and picks which
specialists are actually needed; budgets/depth are deterministic (from
DEPTH_BUDGETS), never LLM-decided, so they stay enforceable regardless of
what the model returns.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.schemas.investigation import (
    DEPTH_BUDGETS,
    InvestigationDepth,
    InvestigationMode,
    InvestigationPlan,
    SubQuestion,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Research Director for a technical intelligence system.
Given a technical question, decompose it into a small, bounded set of sub-questions
and decide which specialists are needed to answer it.

Specialists available:
- "web": general web search for articles, docs, blog posts, product pages
- "academic": papers, citations, methods, benchmarks (OpenAlex/Crossref/Semantic Scholar/arXiv)
- "repository": GitHub repository health, releases, activity, implementation maturity

Only include a specialist in required_specialists if the question genuinely needs it.
Most questions do NOT need academic sources -- only include "academic" when the
question is explicitly about research, papers, studies, or scientific evidence.

Reply with JSON only, matching this exact shape:
{{
  "objective": "one sentence restating what's being decided",
  "sub_questions": [
    {{"id": "Q1", "text": "...", "specialist": "web|academic|repository", "rationale": "..."}}
  ],
  "required_specialists": ["web", "repository"],
  "evidence_requirements": ["..."],
  "freshness_requirement": null,
  "success_criteria": ["..."],
  "reason": "one sentence explaining this plan"
}}

Produce at most {max_tasks} sub_questions total.
"""

_TECHNICAL_RE = re.compile(
    r"\b(framework|library|api|repo|repository|github|langgraph|database|"
    r"deploy|kubernetes|docker|sdk|package|open.?source)\b",
    re.I,
)


def _fallback_plan(
    question: str, mode: InvestigationMode, depth: InvestigationDepth
) -> InvestigationPlan:
    """Deterministic plan used when the LLM is unavailable or returns bad output."""
    max_tasks, tool_budget = DEPTH_BUDGETS[depth]
    is_technical = bool(_TECHNICAL_RE.search(question))
    specialists: list = ["web", "repository"] if is_technical else ["web"]

    sub_questions = [
        SubQuestion(
            id="Q1",
            text=question,
            specialist="web",
            rationale="Primary web evidence gather",
        ),
    ]
    if is_technical and max_tasks > 1:
        sub_questions.append(
            SubQuestion(
                id="Q2",
                text=f"Implementation/repository evidence for: {question}",
                specialist="repository",
                rationale="Assess implementation maturity",
            )
        )

    return InvestigationPlan(
        objective=question.strip(),
        mode=mode,
        depth=depth,
        sub_questions=sub_questions[:max_tasks],
        required_specialists=specialists,
        evidence_requirements=["primary sources", "recent evidence"],
        freshness_requirement=None,
        success_criteria=["question is answered with cited evidence"],
        max_iterations=1,
        tool_budget=tool_budget,
        max_tasks=max_tasks,
        reason="Fallback plan (LLM unavailable or returned invalid output).",
    )


def create_research_plan(
    question: str,
    *,
    mode: InvestigationMode = "explore",
    depth: InvestigationDepth = "standard",
) -> InvestigationPlan:
    """Turn a raw question into a bounded, structured InvestigationPlan."""
    question = question.strip()
    max_tasks, tool_budget = DEPTH_BUDGETS[depth]

    try:
        llm = get_llm(temperature=0.2)
        system = SystemMessage(content=_SYSTEM_PROMPT.format(max_tasks=max_tasks))
        human = HumanMessage(content=f"Question: {question}\nMode: {mode}\nDepth: {depth}")
        resp = llm.invoke([system, human])
        raw = (resp.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        sub_questions = [
            SubQuestion.model_validate(sq) for sq in (data.get("sub_questions") or [])
        ][:max_tasks]
        if not sub_questions:
            raise ValueError("LLM returned no sub_questions")

        required = [
            s
            for s in (data.get("required_specialists") or [])
            if s in ("web", "academic", "repository")
        ]
        if not required:
            required = sorted({sq.specialist for sq in sub_questions})

        return InvestigationPlan(
            objective=str(data.get("objective") or question),
            mode=mode,
            depth=depth,
            sub_questions=sub_questions,
            required_specialists=required,  # type: ignore[arg-type]
            evidence_requirements=list(data.get("evidence_requirements") or []),
            freshness_requirement=data.get("freshness_requirement"),
            success_criteria=list(data.get("success_criteria") or []),
            max_iterations=1,
            tool_budget=tool_budget,
            max_tasks=max_tasks,
            reason=str(data.get("reason") or "LLM-generated plan"),
        )
    except EnvironmentError:
        logger.info("director: no GOOGLE_API_KEY, using fallback plan")
    except Exception as exc:
        logger.warning("director: LLM plan failed (%s), using fallback", exc)

    return _fallback_plan(question, mode, depth)
