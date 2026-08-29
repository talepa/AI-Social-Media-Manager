"""
graphs/investigation_graph.py

Director -> Specialists -> Evidence -> Synthesis pipeline
(see ~/Downloads/ATELIER_FINAL_ARCHITECTURE.md).

Current shape:

    START -> initialize_run -> director -> specialists -> evidence_analyst
          -> synthesis -> END

This is a new, additive graph. research_graph.py and session_graph.py are
untouched.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Annotated, Dict, List, NotRequired, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.director import create_research_plan
from app.agents.evidence_analyst import analyze_evidence
from app.agents.specialists import run_for_sub_question
from app.agents.synthesizer import synthesize_report
from app.schemas.investigation import (
    EvidenceAnalysis,
    InvestigationDepth,
    InvestigationMode,
    InvestigationPlan,
    InvestigationReport,
    ResearchFinding,
    SourceRecord,
    SpecialistResult,
    SubQuestion,
    VerificationResult,
)


def _merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    return {**(left or {}), **(right or {})}


def _append_events(left: List[dict], right: List[dict]) -> List[dict]:
    return [*(left or []), *(right or [])]


class InvestigationState(TypedDict):
    run_id: str
    question: str
    mode: InvestigationMode
    depth: InvestigationDepth

    plan: NotRequired[Optional[dict]]  # InvestigationPlan.model_dump()

    specialist_results: NotRequired[List[dict]]
    sources: NotRequired[List[dict]]
    findings: NotRequired[List[dict]]

    evidence: NotRequired[Optional[dict]]
    report: NotRequired[Optional[dict]]
    verification: NotRequired[Optional[dict]]

    tool_calls_used: NotRequired[int]
    llm_calls_used: NotRequired[int]

    errors: Annotated[Dict[str, str], _merge_dicts]
    events: Annotated[List[dict], _append_events]


def initialize_run_node(state: InvestigationState) -> dict:
    return {
        "events": [{"event_type": "run_started", "run_id": state["run_id"]}],
        "tool_calls_used": 0,
        "llm_calls_used": 0,
        "errors": {},
        "specialist_results": [],
        "sources": [],
        "findings": [],
        "evidence": None,
        "report": None,
        "verification": None,
    }


def director_node(state: InvestigationState) -> dict:
    plan = create_research_plan(
        state["question"],
        mode=state.get("mode", "explore"),
        depth=state.get("depth", "standard"),
    )
    return {
        "plan": plan.model_dump(mode="json"),
        "llm_calls_used": state.get("llm_calls_used", 0) + 1,
        "events": [
            {
                "event_type": "plan_created",
                "run_id": state["run_id"],
                "required_specialists": plan.required_specialists,
                "sub_question_count": len(plan.sub_questions),
            }
        ],
    }


def _allocate_budgets(plan: InvestigationPlan) -> dict[str, int]:
    """Split plan.tool_budget across sub-questions (at least 1 each when possible)."""
    tasks = plan.sub_questions
    n = len(tasks)
    if n == 0:
        return {}
    if plan.tool_budget <= 0:
        return {sq.id: 0 for sq in tasks}

    base = max(1, plan.tool_budget // n)
    remainder = max(0, plan.tool_budget - base * n)
    budgets: dict[str, int] = {}
    for i, sq in enumerate(tasks):
        budgets[sq.id] = base + (1 if i < remainder else 0)
    return budgets


def _aggregate_results(
    results: List[SpecialistResult],
) -> tuple[List[SourceRecord], List[ResearchFinding], List[SpecialistResult]]:
    """Re-ID sources/findings so IDs are unique across parallel specialist runs."""
    prefix = {"web": "WEB", "academic": "PAPER", "repository": "GH"}
    counters = {"web": 0, "academic": 0, "repository": 0}
    finding_n = 0
    all_sources: List[SourceRecord] = []
    all_findings: List[ResearchFinding] = []
    rewritten: List[SpecialistResult] = []

    for result in results:
        id_map: dict[str, str] = {}
        new_sources: List[SourceRecord] = []
        for src in result.sources:
            counters[result.specialist] = counters.get(result.specialist, 0) + 1
            new_id = f"{prefix[result.specialist]}-{counters[result.specialist]:03d}"
            id_map[src.id] = new_id
            rewritten_src = src.model_copy(update={"id": new_id})
            new_sources.append(rewritten_src)
            all_sources.append(rewritten_src)

        new_findings: List[ResearchFinding] = []
        for finding in result.findings:
            finding_n += 1
            rewritten_finding = finding.model_copy(
                update={
                    "id": f"F-{finding_n:03d}",
                    "source_ids": [id_map.get(sid, sid) for sid in finding.source_ids],
                }
            )
            new_findings.append(rewritten_finding)
            all_findings.append(rewritten_finding)

        rewritten.append(
            result.model_copy(update={"sources": new_sources, "findings": new_findings})
        )

    return all_sources, all_findings, rewritten


def specialists_node(state: InvestigationState) -> dict:
    plan_dict = state.get("plan")
    if not plan_dict:
        return {
            "errors": {"specialists": "no plan to execute"},
            "events": [
                {
                    "event_type": "specialists_skipped",
                    "run_id": state["run_id"],
                    "reason": "no plan",
                }
            ],
        }

    plan = InvestigationPlan.model_validate(plan_dict)
    budgets = _allocate_budgets(plan)
    if not plan.sub_questions:
        return {
            "specialist_results": [],
            "sources": [],
            "findings": [],
            "events": [
                {
                    "event_type": "specialists_completed",
                    "run_id": state["run_id"],
                    "sub_question_count": 0,
                    "source_count": 0,
                    "finding_count": 0,
                }
            ],
        }

    results: List[SpecialistResult] = []
    errors: Dict[str, str] = {}
    max_workers = min(4, len(plan.sub_questions))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                run_for_sub_question,
                sq,
                max_tool_calls=budgets.get(sq.id, 1),
            ): sq
            for sq in plan.sub_questions
        }
        for fut in as_completed(futures):
            sq: SubQuestion = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                errors[f"specialist:{sq.id}"] = str(exc)
                results.append(
                    SpecialistResult(
                        specialist=sq.specialist,
                        sub_question_id=sq.id,
                        error=str(exc),
                    )
                )

    # Stable order matching the plan
    by_id = {r.sub_question_id: r for r in results}
    ordered = [by_id[sq.id] for sq in plan.sub_questions if sq.id in by_id]

    sources, findings, rewritten = _aggregate_results(ordered)
    tool_used = sum(r.tool_calls_used for r in rewritten)
    llm_used = sum(r.llm_calls_used for r in rewritten)

    for r in rewritten:
        if r.error:
            errors[f"specialist:{r.sub_question_id}"] = r.error

    return {
        "specialist_results": [r.model_dump(mode="json") for r in rewritten],
        "sources": [s.model_dump(mode="json") for s in sources],
        "findings": [f.model_dump(mode="json") for f in findings],
        "tool_calls_used": state.get("tool_calls_used", 0) + tool_used,
        "llm_calls_used": state.get("llm_calls_used", 0) + llm_used,
        "errors": errors,
        "events": [
            {
                "event_type": "specialists_completed",
                "run_id": state["run_id"],
                "sub_question_count": len(ordered),
                "source_count": len(sources),
                "finding_count": len(findings),
                "tool_calls_used": tool_used,
            }
        ],
    }


def evidence_analyst_node(state: InvestigationState) -> dict:
    plan_dict = state.get("plan")
    if not plan_dict:
        return {
            "errors": {"evidence": "no plan to analyze"},
            "events": [
                {
                    "event_type": "evidence_analysis_skipped",
                    "run_id": state["run_id"],
                    "reason": "no plan",
                }
            ],
        }

    plan = InvestigationPlan.model_validate(plan_dict)
    findings = [
        ResearchFinding.model_validate(item) for item in (state.get("findings") or [])
    ]
    sources = [
        SourceRecord.model_validate(item) for item in (state.get("sources") or [])
    ]

    # Deterministic by default for speed/reliability; set use_llm=True later if desired
    analysis = analyze_evidence(
        plan=plan,
        findings=findings,
        sources=sources,
        use_llm=False,
    )
    return {
        "evidence": analysis.model_dump(mode="json"),
        "llm_calls_used": state.get("llm_calls_used", 0) + analysis.llm_calls_used,
        "events": [
            {
                "event_type": "evidence_analysis_completed",
                "run_id": state["run_id"],
                "claim_count": len(analysis.claims),
                "conflict_count": len(analysis.conflicts),
                "gap_count": len(analysis.gaps),
            }
        ],
    }


def synthesis_node(state: InvestigationState) -> dict:
    plan_dict = state.get("plan")
    evidence_dict = state.get("evidence")
    if not plan_dict or not evidence_dict:
        return {
            "errors": {"synthesis": "missing plan or evidence"},
            "events": [
                {
                    "event_type": "synthesis_skipped",
                    "run_id": state["run_id"],
                    "reason": "missing plan or evidence",
                }
            ],
        }

    plan = InvestigationPlan.model_validate(plan_dict)
    evidence = EvidenceAnalysis.model_validate(evidence_dict)
    sources = [
        SourceRecord.model_validate(item) for item in (state.get("sources") or [])
    ]

    report, verification = synthesize_report(
        plan=plan,
        evidence=evidence,
        sources=sources,
        use_llm=False,
    )
    return {
        "report": report.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
        "events": [
            {
                "event_type": "synthesis_completed",
                "run_id": state["run_id"],
                "section_count": len(report.sections),
                "citation_validation_passed": verification.passed,
            },
            {
                "event_type": "citation_validated",
                "run_id": state["run_id"],
                "passed": verification.passed,
                "invalid_count": len(verification.invalid_citations),
            },
        ],
    }


def build_investigation_graph():
    g = StateGraph(InvestigationState)
    g.add_node("initialize_run", initialize_run_node)
    g.add_node("director", director_node)
    g.add_node("specialists", specialists_node)
    g.add_node("evidence_analyst", evidence_analyst_node)
    g.add_node("synthesis", synthesis_node)

    g.add_edge(START, "initialize_run")
    g.add_edge("initialize_run", "director")
    g.add_edge("director", "specialists")
    g.add_edge("specialists", "evidence_analyst")
    g.add_edge("evidence_analyst", "synthesis")
    g.add_edge("synthesis", END)

    return g.compile(checkpointer=MemorySaver())


investigation_graph = build_investigation_graph()


def state_to_plan(state: dict) -> Optional[InvestigationPlan]:
    plan_dict = state.get("plan")
    if not plan_dict:
        return None
    return InvestigationPlan.model_validate(plan_dict)


def state_to_specialist_results(state: dict) -> List[SpecialistResult]:
    return [
        SpecialistResult.model_validate(item)
        for item in (state.get("specialist_results") or [])
    ]


def state_to_sources(state: dict) -> List[SourceRecord]:
    return [SourceRecord.model_validate(item) for item in (state.get("sources") or [])]


def state_to_findings(state: dict) -> List[ResearchFinding]:
    return [
        ResearchFinding.model_validate(item) for item in (state.get("findings") or [])
    ]


def state_to_evidence(state: dict) -> Optional[EvidenceAnalysis]:
    raw = state.get("evidence")
    if not raw:
        return None
    return EvidenceAnalysis.model_validate(raw)


def state_to_report(state: dict) -> Optional[InvestigationReport]:
    raw = state.get("report")
    if not raw:
        return None
    return InvestigationReport.model_validate(raw)


def state_to_verification(state: dict) -> Optional[VerificationResult]:
    raw = state.get("verification")
    if not raw:
        return None
    return VerificationResult.model_validate(raw)
