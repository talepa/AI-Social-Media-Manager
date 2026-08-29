"""
agents/synthesizer.py

Synthesis Agent: builds a cited report from EvidenceAnalysis only, then
runs citation validation so the report cannot invent evidence IDs.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.schemas.investigation import (
    EvidenceAnalysis,
    EvidenceClaim,
    InvestigationPlan,
    InvestigationReport,
    ReportSection,
    SourceRecord,
    VerificationResult,
)

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(
    r"\b((?:CLAIM|WEB|PAPER|GH|NEWS|DOC|F|CONFLICT|GAP)-\d{3,})\b"
)


def _source_lookup(sources: List[SourceRecord]) -> dict[str, SourceRecord]:
    return {s.id: s for s in sources if s.id}


def compile_report(
    *,
    plan: InvestigationPlan,
    evidence: EvidenceAnalysis,
    sources: List[SourceRecord],
) -> InvestigationReport:
    """Deterministic report from claims/gaps/conflicts — no LLM."""
    by_src = _source_lookup(sources)
    sections: List[ReportSection] = []

    if evidence.claims:
        lines = []
        claim_ids = []
        source_ids: List[str] = []
        for c in evidence.claims:
            claim_ids.append(c.id)
            src_bits = ", ".join(c.supporting_source_ids[:4]) or "no sources"
            lines.append(
                f"- **{c.id}** ({c.strength}, conf={c.confidence:.2f}, "
                f"agreement={c.agreement_count}): {c.claim} [{src_bits}]"
            )
            source_ids.extend(c.supporting_source_ids)
        sections.append(
            ReportSection(
                title="Key claims",
                body="\n".join(lines),
                claim_ids=claim_ids,
                source_ids=sorted(set(source_ids)),
            )
        )

    if evidence.conflicts:
        body = "\n".join(
            f"- **{c.id}**: {c.summary} ({c.claim_a_id} ↔ {c.claim_b_id})"
            for c in evidence.conflicts
        )
        sections.append(
            ReportSection(
                title="Conflicts",
                body=body,
                claim_ids=[c.claim_a_id for c in evidence.conflicts]
                + [c.claim_b_id for c in evidence.conflicts],
            )
        )

    if evidence.gaps:
        body = "\n".join(f"- **{g.id}**: {g.description}" for g in evidence.gaps)
        sections.append(ReportSection(title="Evidence gaps", body=body))

    # Source appendix (cited only)
    cited_sources = sorted(
        {
            sid
            for c in evidence.claims
            for sid in c.supporting_source_ids
            if sid in by_src
        }
    )
    if cited_sources:
        lines = []
        for sid in cited_sources[:20]:
            s = by_src[sid]
            lines.append(f"- **{sid}** ({s.type}): {s.title} — {s.url}")
        sections.append(
            ReportSection(
                title="Sources",
                body="\n".join(lines),
                source_ids=cited_sources,
            )
        )

    headline = (
        f"Investigation report: {plan.objective}"
        if plan.objective
        else "Investigation report"
    )

    exec_summary = evidence.summary or (
        f"Reviewed {len(evidence.claims)} claims across {len(cited_sources)} sources."
    )

    cited_claim_ids = [c.id for c in evidence.claims]
    markdown = _to_markdown(headline, exec_summary, sections)

    return InvestigationReport(
        headline=headline,
        executive_summary=exec_summary,
        sections=sections,
        cited_claim_ids=cited_claim_ids,
        cited_source_ids=cited_sources,
        markdown=markdown,
        mode="compile",
    )


def _to_markdown(headline: str, summary: str, sections: List[ReportSection]) -> str:
    lines = [f"# {headline}", "", summary, ""]
    for sec in sections:
        lines.append(f"## {sec.title}")
        lines.append("")
        lines.append(sec.body)
        lines.append("")
    return "\n".join(lines).strip()


def validate_citations(
    report: InvestigationReport,
    *,
    evidence: EvidenceAnalysis,
    sources: List[SourceRecord],
) -> VerificationResult:
    """Ensure every cited ID in the report exists in the evidence state."""
    valid_claims = {c.id for c in evidence.claims}
    valid_sources = {s.id for s in sources}
    valid_conflicts = {c.id for c in evidence.conflicts}
    valid_gaps = {g.id for g in evidence.gaps}
    valid_all = valid_claims | valid_sources | valid_conflicts | valid_gaps

    text_blob = "\n".join(
        [
            report.headline,
            report.executive_summary,
            report.markdown,
            *[sec.body for sec in report.sections],
            *report.cited_claim_ids,
            *report.cited_source_ids,
        ]
    )
    found_ids = set(_CITATION_RE.findall(text_blob))

    invalid = sorted(found_ids - valid_all)
    # Also flag declared citations that aren't in evidence
    missing_declared_claims = sorted(set(report.cited_claim_ids) - valid_claims)
    missing_declared_sources = sorted(set(report.cited_source_ids) - valid_sources)

    notes: List[str] = []
    if not found_ids and evidence.claims:
        notes.append("Report text contains no explicit evidence IDs (CLAIMS/sources).")
    if missing_declared_claims:
        notes.append(f"cited_claim_ids missing from evidence: {missing_declared_claims}")
    if missing_declared_sources:
        notes.append(f"cited_source_ids missing from sources: {missing_declared_sources}")

    invalid_all = sorted(set(invalid) | set(missing_declared_claims))
    missing_sources = missing_declared_sources

    passed = not invalid_all and not missing_sources
    if passed:
        notes.append("All citations resolve to known evidence IDs.")

    return VerificationResult(
        passed=passed,
        invalid_citations=invalid_all,
        missing_sources=missing_sources,
        notes=notes,
    )


def _llm_polish_report(
    report: InvestigationReport,
    plan: InvestigationPlan,
    evidence: EvidenceAnalysis,
) -> Optional[InvestigationReport]:
    try:
        llm = get_llm(temperature=0.3)
    except EnvironmentError:
        return None

    allowed_claims = ", ".join(c.id for c in evidence.claims[:20]) or "(none)"
    allowed_sources = ", ".join(report.cited_source_ids[:20]) or "(none)"
    system = SystemMessage(
        content=(
            "You polish an investigation report. Keep the same section titles. "
            "You may ONLY cite these IDs: "
            f"claims=[{allowed_claims}] sources=[{allowed_sources}]. "
            "Do not invent IDs, URLs, or statistics. Return markdown only with "
            f"headline '# {report.headline}' then sections as ## headings."
        )
    )
    human = HumanMessage(
        content=(
            f"Objective: {plan.objective}\n\n"
            f"Draft:\n{report.markdown[:6000]}"
        )
    )
    try:
        resp = llm.invoke([system, human])
        text = (resp.content or "").strip()
        if len(text) < 80:
            return None
        polished = report.model_copy(deep=True)
        polished.markdown = text
        polished.mode = "llm"
        # Keep structured sections from compile; markdown is the LLM narrative
        return polished
    except Exception as exc:
        logger.warning("synthesizer LLM polish failed: %s", exc)
        return None


def synthesize_report(
    *,
    plan: InvestigationPlan,
    evidence: EvidenceAnalysis,
    sources: List[SourceRecord],
    use_llm: bool = False,
) -> Tuple[InvestigationReport, VerificationResult]:
    report = compile_report(plan=plan, evidence=evidence, sources=sources)
    if use_llm:
        polished = _llm_polish_report(report, plan, evidence)
        if polished is not None:
            report = polished

    verification = validate_citations(report, evidence=evidence, sources=sources)
    if not verification.passed and report.mode == "llm":
        # Fall back to deterministic compile if LLM invented citations
        logger.info("synthesizer: LLM report failed citation validation — using compile")
        report = compile_report(plan=plan, evidence=evidence, sources=sources)
        verification = validate_citations(report, evidence=evidence, sources=sources)
        verification.notes.append("Fell back to compile mode after invalid LLM citations.")

    return report, verification
