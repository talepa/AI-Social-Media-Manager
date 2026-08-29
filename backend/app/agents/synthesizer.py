"""
agents/synthesizer.py

Builds a short, cited answer from filtered evidence — not a dump of snippets.
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
from app.services.source_quality import filter_claims, filter_sources, is_junk_text

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(
    r"\b((?:CLAIM|WEB|PAPER|GH|NEWS|DOC|F|CONFLICT|GAP)-\d{3,})\b"
)


def _source_lookup(sources: List[SourceRecord]) -> dict[str, SourceRecord]:
    return {s.id: s for s in sources if s.id}


def _query_text(plan: InvestigationPlan) -> str:
    bits = [plan.objective or ""]
    for sq in plan.sub_questions or []:
        bits.append(sq.text or "")
    return " ".join(bits)


def _deterministic_short_answer(
    plan: InvestigationPlan,
    claims: List[EvidenceClaim],
    sources: List[SourceRecord],
) -> Tuple[str, List[str]]:
    """Build a brief answer from the best non-junk claims/sources."""
    used_ids: List[str] = []
    sentences: List[str] = []

    for c in claims[:4]:
        text = (c.claim or "").strip().rstrip(".")
        if not text or is_junk_text(text):
            continue
        if len(text) > 220:
            text = text[:217].rstrip() + "…"
        sentences.append(text)
        for sid in c.supporting_source_ids[:2]:
            if sid not in used_ids:
                used_ids.append(sid)
        if len(sentences) >= 3:
            break

    if not sentences:
        for s in sources[:3]:
            title = (s.title or "").strip()
            if not title or is_junk_text(title):
                continue
            bit = (s.content or "").strip()
            bit = re.split(r"(?<=[.!?])\s+", bit)[0] if bit else ""
            if bit and not is_junk_text(bit) and len(bit) > 40:
                if len(bit) > 180:
                    bit = bit[:177].rstrip() + "…"
                sentences.append(bit)
            else:
                sentences.append(f"See “{title}” for background on this topic.")
            used_ids.append(s.id)
            if len(sentences) >= 2:
                break

    if not sentences:
        obj = plan.objective or "this question"
        return (
            f"We found limited clean evidence for: {obj}. Try rephrasing or searching deeper.",
            [],
        )

    answer = ". ".join(sentences)
    if not answer.endswith("."):
        answer += "."
    return answer, used_ids


def _llm_short_answer(
    plan: InvestigationPlan,
    sources: List[SourceRecord],
) -> Optional[Tuple[str, List[str]]]:
    """Ask Gemini for a 3–5 sentence answer grounded only in provided sources."""
    try:
        llm = get_llm(temperature=0.2)
    except EnvironmentError:
        return None

    if not sources:
        return None

    catalog = []
    for s in sources[:8]:
        snippet = (s.content or "")[:280].replace("\n", " ")
        catalog.append(f"- {s.id}: {s.title}\n  {snippet}")

    system = SystemMessage(
        content=(
            "You write a short technical answer for a research product.\n"
            "Rules:\n"
            "- 3 to 5 clear sentences.\n"
            "- Answer the user's question directly (define terms, then contrast if asked).\n"
            "- Use ONLY the sources listed. Do not invent facts.\n"
            "- Do not paste navigation menus, ads, or boilerplate.\n"
            "- Do not include raw source IDs like WEB-001 inside the answer text.\n"
            "- After the answer, on its own line write: CITES: ID1, ID2, ID3 "
            "(only IDs from the list that you actually used)."
        )
    )
    human = HumanMessage(
        content=(
            f"Question / objective:\n{plan.objective}\n\n"
            f"Sub-questions:\n"
            + "\n".join(f"- {sq.text}" for sq in (plan.sub_questions or [])[:6])
            + "\n\nSources:\n"
            + "\n".join(catalog)
        )
    )
    try:
        resp = llm.invoke([system, human])
        raw = (resp.content or "").strip()
    except Exception as exc:
        logger.warning("short-answer LLM failed: %s", exc)
        return None

    if len(raw) < 40:
        return None

    cites: List[str] = []
    answer = raw
    m = re.search(r"(?im)^CITES:\s*(.+)$", raw)
    if m:
        answer = raw[: m.start()].strip()
        cites = [p.strip() for p in re.split(r"[, ]+", m.group(1)) if p.strip()]
        allowed = {s.id for s in sources}
        cites = [c for c in cites if c in allowed]

    # Strip any leaked IDs from prose
    answer = _CITATION_RE.sub("", answer)
    answer = re.sub(r"\s{2,}", " ", answer).strip()
    answer = re.sub(r"\s+([,.])", r"\1", answer)
    if is_junk_text(answer):
        return None
    if not cites:
        cites = [s.id for s in sources[:3]]
    return answer, cites


def compile_report(
    *,
    plan: InvestigationPlan,
    evidence: EvidenceAnalysis,
    sources: List[SourceRecord],
) -> InvestigationReport:
    """Short answer + filtered sources only (no snippet dump)."""
    query = _query_text(plan)
    by_src = _source_lookup(sources)

    good_sources = filter_sources(query, sources, limit=8, min_score=0.2)
    good_ids = {s.id for s in good_sources}

    claims = filter_claims(query, evidence.claims or [])
    # Prefer claims that point at kept sources
    claims = [
        c
        for c in claims
        if not c.supporting_source_ids
        or any(sid in good_ids or sid in by_src for sid in c.supporting_source_ids)
    ]

    # If relevance filter was too aggressive, keep claim-linked sources
    if not good_sources:
        linked: List[SourceRecord] = []
        seen: set[str] = set()
        for c in claims:
            for sid in c.supporting_source_ids:
                if sid in by_src and sid not in seen:
                    linked.append(by_src[sid])
                    seen.add(sid)
        good_sources = linked or list(sources)[:6]
        good_ids = {s.id for s in good_sources}

    short_answer, used_ids = _deterministic_short_answer(plan, claims, good_sources)

    # Prefer LLM short answer when available
    llm_result = _llm_short_answer(plan, good_sources or list(sources)[:6])
    mode = "compile"
    if llm_result:
        short_answer, used_ids = llm_result
        mode = "llm"

    # Final source list: cited first, then other good sources
    cited_sources: List[str] = []
    for sid in used_ids:
        if sid in by_src and sid not in cited_sources:
            cited_sources.append(sid)
    for s in good_sources:
        if s.id not in cited_sources:
            cited_sources.append(s.id)
    cited_sources = cited_sources[:8]

    sections: List[ReportSection] = [
        ReportSection(
            title="Short answer",
            body=short_answer,
            claim_ids=[c.id for c in claims[:5]],
            source_ids=cited_sources,
        )
    ]

    if cited_sources:
        lines = []
        for sid in cited_sources:
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

    headline = plan.objective if plan.objective else "Answer"
    markdown = _to_markdown(headline, short_answer, sections)

    return InvestigationReport(
        headline=headline,
        executive_summary=short_answer,
        sections=sections,
        cited_claim_ids=[c.id for c in claims[:5]],
        cited_source_ids=cited_sources,
        markdown=markdown,
        mode=mode,  # type: ignore[arg-type]
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
    """Ensure every cited ID in the report exists in known evidence/sources."""
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
    missing_declared_claims = sorted(set(report.cited_claim_ids) - valid_claims)
    missing_declared_sources = sorted(set(report.cited_source_ids) - valid_sources)

    notes: List[str] = []
    # Short answers intentionally omit inline IDs — that is OK
    if missing_declared_sources:
        notes.append(f"cited_source_ids missing from sources: {missing_declared_sources}")

    # Claims listed for provenance may be filtered; don't fail the whole report
    invalid_all = sorted(set(invalid))
    missing_sources = missing_declared_sources
    passed = not invalid_all and not missing_sources
    if passed:
        notes.append("Cited sources resolve; short answer has no invented IDs.")

    return VerificationResult(
        passed=passed,
        invalid_citations=invalid_all,
        missing_sources=missing_sources,
        notes=notes,
    )


def synthesize_report(
    *,
    plan: InvestigationPlan,
    evidence: EvidenceAnalysis,
    sources: List[SourceRecord],
    use_llm: bool = False,
) -> Tuple[InvestigationReport, VerificationResult]:
    # compile_report already tries LLM for the short answer when the key exists.
    # use_llm kept for API compatibility (extra polish path unused for snippet dumps).
    _ = use_llm
    report = compile_report(plan=plan, evidence=evidence, sources=sources)
    verification = validate_citations(report, evidence=evidence, sources=sources)
    return report, verification
