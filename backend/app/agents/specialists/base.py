"""
agents/specialists/base.py

Shared logic for all specialist agents. Each specialist:
1. Receives a SubQuestion from the Director's plan
2. Uses Gemini tool-calling to decide which searches to run
3. Collects sources and produces structured ResearchFindings
4. Respects a per-specialist tool-call budget
"""

from __future__ import annotations

import json
import logging
import re
from typing import List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.config import get_llm
from app.schemas.investigation import (
    ResearchFinding,
    SourceRecord,
    SpecialistName,
    SpecialistResult,
    SubQuestion,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*", re.I)

_FINDINGS_PROMPT = """Based on the search results above, produce your findings as a JSON array.
Each finding must have these fields:
- "claim": one-sentence factual claim (not a question)
- "evidence_summary": 1-2 sentences of supporting evidence from the sources
- "source_indices": list of 0-based indices into the sources you retrieved (e.g. [0, 2])
- "confidence": float 0-1, how well-supported this claim is
- "methodology_note": optional note on evidence quality (null if not needed)

Return ONLY a JSON array of findings. No other text."""


def run_specialist(
    sub_question: SubQuestion,
    specialist_name: SpecialistName,
    tools: List[BaseTool],
    system_prompt: str,
    max_tool_calls: int = 4,
) -> SpecialistResult:
    """
    Run a specialist agent on one sub-question.

    The agent loop:
    1. Send the sub-question to Gemini with bound tools
    2. If Gemini returns tool calls, execute them and feed results back
    3. Repeat until Gemini stops calling tools or budget is exhausted
    4. Ask Gemini to extract structured findings from the collected sources
    """
    tool_calls_used = 0
    llm_calls_used = 0
    collected_sources: List[SourceRecord] = []
    source_counter = 0

    try:
        llm = get_llm(temperature=0.2)
    except EnvironmentError as exc:
        logger.info("specialist %s: no API key, returning empty result", specialist_name)
        return SpecialistResult(
            specialist=specialist_name,
            sub_question_id=sub_question.id,
            error=str(exc),
        )

    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=(
            f"Sub-question: {sub_question.text}\n"
            f"Rationale: {sub_question.rationale}\n\n"
            f"You have a budget of {max_tool_calls} tool calls. "
            f"Use them wisely to gather the most relevant evidence."
        )),
    ]

    try:
        for _iteration in range(max_tool_calls + 2):
            resp: AIMessage = llm_with_tools.invoke(messages)
            llm_calls_used += 1
            messages.append(resp)

            if not resp.tool_calls:
                break

            for tc in resp.tool_calls:
                if tool_calls_used >= max_tool_calls:
                    messages.append(ToolMessage(
                        content="Budget exhausted — no more tool calls allowed.",
                        tool_call_id=tc["id"],
                    ))
                    continue

                tool_name = tc["name"]
                tool_fn = tool_map.get(tool_name)
                if not tool_fn:
                    messages.append(ToolMessage(
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tc["id"],
                    ))
                    continue

                try:
                    result = tool_fn.invoke(tc["args"])
                    tool_calls_used += 1
                except Exception as exc:
                    logger.warning("specialist %s: tool %s failed: %s", specialist_name, tool_name, exc)
                    messages.append(ToolMessage(
                        content=f"Tool error: {exc}",
                        tool_call_id=tc["id"],
                    ))
                    continue

                items = result if isinstance(result, list) else [result]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    source_counter += 1
                    prefix = _source_prefix(specialist_name)
                    collected_sources.append(SourceRecord(
                        id=f"{prefix}-{source_counter:03d}",
                        type=_source_type(specialist_name, tool_name),
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=(item.get("content", "") or "")[:600],
                        metadata={
                            k: v for k, v in item.items()
                            if k not in ("title", "url", "content") and v is not None
                        },
                        specialist=specialist_name,
                        sub_question_id=sub_question.id,
                    ))

                messages.append(ToolMessage(
                    content=json.dumps(result, default=str)[:4000],
                    tool_call_id=tc["id"],
                ))

            if tool_calls_used >= max_tool_calls:
                break

        findings = _extract_findings(
            llm, messages, sub_question, specialist_name, collected_sources,
        )
        llm_calls_used += 1

        return SpecialistResult(
            specialist=specialist_name,
            sub_question_id=sub_question.id,
            sources=collected_sources,
            findings=findings,
            tool_calls_used=tool_calls_used,
            llm_calls_used=llm_calls_used,
        )

    except Exception as exc:
        logger.exception("specialist %s failed", specialist_name)
        return SpecialistResult(
            specialist=specialist_name,
            sub_question_id=sub_question.id,
            sources=collected_sources,
            tool_calls_used=tool_calls_used,
            llm_calls_used=llm_calls_used,
            error=str(exc),
        )


def _extract_findings(
    llm,
    messages: list,
    sub_question: SubQuestion,
    specialist_name: SpecialistName,
    sources: List[SourceRecord],
) -> List[ResearchFinding]:
    """Ask Gemini to produce structured findings from the collected sources."""
    if not sources:
        return [
            ResearchFinding(
                id="F-001",
                sub_question_id=sub_question.id,
                specialist=specialist_name,
                claim=f"No sources found for: {sub_question.text}",
                evidence_summary="Search returned no results.",
                confidence=0.0,
            )
        ]

    messages_copy = list(messages)
    messages_copy.append(HumanMessage(content=_FINDINGS_PROMPT))
    resp = llm.invoke(messages_copy)
    raw = (resp.content or "").strip()

    raw = _FENCE_RE.sub("", raw).replace("```", "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("specialist %s: findings extraction returned invalid JSON", specialist_name)
        return [
            ResearchFinding(
                id="F-001",
                sub_question_id=sub_question.id,
                specialist=specialist_name,
                claim=f"Evidence gathered for: {sub_question.text}",
                evidence_summary=raw[:300] if raw else "Findings extraction failed.",
                source_ids=[s.id for s in sources[:3]],
                confidence=0.3,
            )
        ]

    if not isinstance(data, list):
        data = [data]

    findings: List[ResearchFinding] = []
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            continue
        source_indices = item.get("source_indices") or []
        source_ids = [
            sources[idx].id
            for idx in source_indices
            if isinstance(idx, int) and 0 <= idx < len(sources)
        ]
        findings.append(ResearchFinding(
            id=f"F-{i:03d}",
            sub_question_id=sub_question.id,
            specialist=specialist_name,
            claim=str(item.get("claim", "")),
            evidence_summary=str(item.get("evidence_summary", "")),
            source_ids=source_ids,
            confidence=min(1.0, max(0.0, float(item.get("confidence", 0.5)))),
            methodology_note=item.get("methodology_note"),
        ))

    return findings or [
        ResearchFinding(
            id="F-001",
            sub_question_id=sub_question.id,
            specialist=specialist_name,
            claim=f"Evidence gathered for: {sub_question.text}",
            source_ids=[s.id for s in sources[:3]],
            confidence=0.3,
        )
    ]


def _source_prefix(specialist: SpecialistName) -> str:
    return {"web": "WEB", "academic": "PAPER", "repository": "GH"}[specialist]


def _source_type(specialist: SpecialistName, tool_name: str) -> str:
    type_map = {
        "brave_search": "web",
        "news_search": "news",
        "papers_search": "papers",
        "github_search": "github",
    }
    return type_map.get(tool_name, "web")
