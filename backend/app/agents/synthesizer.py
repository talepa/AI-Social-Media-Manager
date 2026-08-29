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
    short_answer = ""

    if evidence.claims:
        claim_ids = [c.id for c in evidence.claims]
        source_ids: List[str] = []
        for c in evidence.claims:
            source_ids.extend(c.supporting_source_ids)

        # Short answer: 1–3 clean sentences, no raw source IDs in the prose
        short_bits = [
            c.claim.strip().rstrip(".")
            for c in evidence.claims[:3]
            if c.claim.strip()
        ]
        short_answer = ". ".join(short_bits)
        if short_answer and not short_answer.endswith("."):
            short_answer += "."

        # Encode footnote source ids after each paragraph as [[WEB-001,WEB-002]]
        # so the UI can render Wikipedia-style superscripts (not shown as raw IDs).
        detail_blocks = []
        for c in evidence.claims[:12]:
            text = c.claim.strip()
            if not text:
                continue
            refs = ",".join(c.supporting_source_ids[:4])
            detail_blocks.append(f"{text}[[{refs}]]" if refs else text)

        sections.append(
            ReportSection(
                title="Short answer",
                body=short_answer,
                claim_ids=claim_ids[:3],
                source_ids=sorted(set(source_ids)),
            )
        )
        sections.append(
            ReportSection(
                title="Details",
                body="\n\n".join(detail_blocks),
                claim_ids=claim_ids,
                source_ids=sorted(set(source_ids)),
            )
        )
    elif sources:
        # Last resort: summarize from retrieved sources if claims missing
        lines = []
        sids = []
        for s in sources[:10]:
            sids.append(s.id)
            bit = (s.content or "").strip()
            if bit:
                lines.append(f"**{s.title or s.id}** — {bit[:280]}")
            else:
                lines.append(f"**{s.title or s.id}** — {s.url}")
        sections.append(
            ReportSection(
                title="Answer",
                body=(
                    "Structured claims were incomplete, so here is what the "
                    "retrieved sources say:\n\n" + "\n\n".join(lines)
                ),
                source_ids=sids,
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

    if evidence.gaps and evidence.claims:
        # Only surface gaps when we also have some answer — avoid gap-only memos
        body = "\n".join(f"- {g.description}" for g in evidence.gaps[:6])
        sections.append(ReportSection(title="Open questions", body=body))

    cited_sources = sorted(
        {
            sid
            for c in evidence.claims
            for sid in c.supporting_source_ids
            if sid in by_src
        }
    )
    if not cited_sources:
        cited_sources = [s.id for s in sources if s.id][:20]

    if cited_sources:
        lines = []
        for sid in cited_sources[:20]:
            s = by_src.get(sid)
            if not s:
                continue
            lines.append(f"- **{sid}** ({s.type}): {s.title} — {s.url}")
        sections.append(
            ReportSection(
                title="Sources",
                body="\n".join(lines),
                source_ids=cited_sources,
            )
        )

    headline = plan.objective if plan.objective else "Investigation report"

    if short_answer:
        exec_summary = short_answer
    else:
        exec_summary = evidence.summary or (
            f"Retrieved {len(sources)} sources for: {plan.objective}"
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
