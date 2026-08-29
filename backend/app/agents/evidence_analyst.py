"""
agents/evidence_analyst.py

Evidence Analyst: consolidates specialist findings into traceable claims,
flags conflicts, and records evidence gaps. Deterministic by default;
optional Gemini polish when available.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.schemas.investigation import (
    EvidenceAnalysis,
    EvidenceClaim,
    EvidenceConflict,
    EvidenceGap,
    EvidenceStrength,
    InvestigationPlan,
    ResearchFinding,
    SourceRecord,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*", re.I)
_NEGATION_RE = re.compile(
    r"\b(not|no|never|isn't|aren't|wasn't|weren't|cannot|can't|won't|without|"
    r"fail(?:s|ed|ure)?|unready|immature|unstable|lacks?)\b",
    re.I,
)


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower())}


def _strength(confidence: float, agreement: int) -> EvidenceStrength:
    if agreement >= 3 and confidence >= 0.7:
        return "strong"
    if agreement >= 2 and confidence >= 0.55:
        return "moderate"
    if confidence >= 0.4 or agreement >= 1:
        return "weak"
    return "insufficient"


def _source_map(sources: List[SourceRecord]) -> dict[str, SourceRecord]:
    return {s.id: s for s in sources if s.id}


def compile_evidence(
    *,
    plan: InvestigationPlan,
    findings: List[ResearchFinding],
    sources: List[SourceRecord],
) -> EvidenceAnalysis:
    """Deterministic evidence consolidation (no LLM)."""
    by_id = _source_map(sources)
    claims: List[EvidenceClaim] = []

    for i, finding in enumerate(findings, 1):
        support_ids = [sid for sid in finding.source_ids if sid in by_id]
        families = sorted(
            {
                by_id[sid].type
                for sid in support_ids
                if sid in by_id
            }
        )
        agreement = max(len(support_ids), len(families), 1 if finding.claim else 0)
        conf = float(finding.confidence)
        claims.append(
            EvidenceClaim(
                id=f"CLAIM-{i:03d}",
                claim=finding.claim.strip() or f"Finding {finding.id}",
                finding_ids=[finding.id],
                supporting_source_ids=support_ids,
                source_families=families,
                confidence=conf,
                strength=_strength(conf, agreement),
                agreement_count=agreement,
                uncertainty_notes=finding.methodology_note,
                sub_question_ids=[finding.sub_question_id] if finding.sub_question_id else [],
            )
        )

    conflicts = _detect_conflicts(claims)
    gaps = _detect_gaps(plan, findings, claims)

    covered = {sq for c in claims for sq in c.sub_question_ids}
    summary = (
        f"{len(claims)} claims from {len(findings)} findings across "
        f"{len({s.type for s in sources})} source families"
        f"{f'; {len(conflicts)} conflict(s)' if conflicts else ''}"
        f"{f'; {len(gaps)} gap(s)' if gaps else ''}."
    )
    if plan.objective:
        summary = f"{plan.objective} — {summary}"

    return EvidenceAnalysis(
        claims=claims,
        conflicts=conflicts,
        gaps=gaps,
        summary=summary,
        llm_calls_used=0,
    )


def _detect_conflicts(claims: List[EvidenceClaim]) -> List[EvidenceConflict]:
    """Heuristic: overlapping tokens with opposite negation polarity."""
    conflicts: List[EvidenceConflict] = []
    n = 0
    for i, a in enumerate(claims):
        a_neg = bool(_NEGATION_RE.search(a.claim))
        a_tok = _tokens(a.claim)
        for b in claims[i + 1 :]:
            b_neg = bool(_NEGATION_RE.search(b.claim))
            if a_neg == b_neg:
                continue
            overlap = a_tok & _tokens(b.claim)
            if len(overlap) < 2:
                continue
            shared_sq = set(a.sub_question_ids) & set(b.sub_question_ids)
            if shared_sq or len(overlap) >= 3:
                n += 1
                conflicts.append(
                    EvidenceConflict(
                        id=f"CONFLICT-{n:03d}",
                        claim_a_id=a.id,
                        claim_b_id=b.id,
                        summary=(
                            f"Possible disagreement between {a.id} and {b.id}: "
                            f"“{a.claim[:80]}” vs “{b.claim[:80]}”"
                        ),
                        source_ids=sorted(
                            set(a.supporting_source_ids) | set(b.supporting_source_ids)
                        )[:8],
                    )
                )
    return conflicts


def _detect_gaps(
    plan: InvestigationPlan,
    findings: List[ResearchFinding],
    claims: List[EvidenceClaim],
) -> List[EvidenceGap]:
    gaps: List[EvidenceGap] = []
    covered_sq = {sq for c in claims for sq in c.sub_question_ids}
    finding_sq = {f.sub_question_id for f in findings if f.sub_question_id}

    n = 0
    for sq in plan.sub_questions:
        if sq.id not in covered_sq and sq.id not in finding_sq:
            n += 1
            gaps.append(
                EvidenceGap(
                    id=f"GAP-{n:03d}",
                    description=f"No findings for sub-question {sq.id}: {sq.text}",
                    related_sub_question_ids=[sq.id],
                    suggested_specialist=sq.specialist,
                )
            )
        elif sq.id not in covered_sq:
            n += 1
            gaps.append(
                EvidenceGap(
                    id=f"GAP-{n:03d}",
                    description=f"Findings for {sq.id} lack usable cited sources.",
                    related_sub_question_ids=[sq.id],
                    suggested_specialist=sq.specialist,
                )
            )

    weak = [c for c in claims if c.strength in ("weak", "insufficient")]
    if weak and len(weak) == len(claims) and claims:
        n += 1
        gaps.append(
            EvidenceGap(
                id=f"GAP-{n:03d}",
                description="All claims are weak or insufficient — need stronger corroboration.",
                related_sub_question_ids=sorted(
                    {sq for c in weak for sq in c.sub_question_ids}
                ),
            )
        )

    for req in plan.evidence_requirements[:5]:
        req_l = req.lower()
        blob = " ".join(c.claim for c in claims).lower()
        if req_l and not any(tok in blob for tok in _tokens(req) if len(tok) > 4):
            n += 1
            gaps.append(
                EvidenceGap(
                    id=f"GAP-{n:03d}",
                    description=f"Plan evidence requirement may be unmet: {req}",
                )
            )
    return gaps


def _llm_refine(
    analysis: EvidenceAnalysis,
    plan: InvestigationPlan,
    findings: List[ResearchFinding],
) -> Optional[EvidenceAnalysis]:
    try:
        llm = get_llm(temperature=0.2)
    except EnvironmentError:
        return None

    payload = {
        "objective": plan.objective,
        "claims": [c.model_dump() for c in analysis.claims[:12]],
        "conflicts": [c.model_dump() for c in analysis.conflicts[:6]],
        "gaps": [g.model_dump() for g in analysis.gaps[:6]],
        "findings_sample": [
            {"id": f.id, "claim": f.claim, "source_ids": f.source_ids}
            for f in findings[:12]
        ],
    }
    system = SystemMessage(
        content=(
            "You refine an evidence analysis for a technical research system. "
            "Return JSON only with keys: summary (string), conflicts (array of "
            "{claim_a_id, claim_b_id, summary}), gaps (array of {description, "
            "related_sub_question_ids, suggested_specialist|null}). "
            "Only reference existing CLAIM-* ids. Do not invent source IDs. "
            "Keep conflicts/gaps short (max 5 each)."
        )
    )
    human = HumanMessage(content=json.dumps(payload, default=str)[:8000])
    try:
        resp = llm.invoke([system, human])
        raw = _FENCE_RE.sub("", (resp.content or "").strip()).replace("```", "").strip()
        data = json.loads(raw)
    except Exception as exc:
        logger.warning("evidence_analyst LLM refine failed: %s", exc)
        return None

    if not isinstance(data, dict):
        return None

    claim_ids = {c.id for c in analysis.claims}
    conflicts: List[EvidenceConflict] = []
    for i, item in enumerate(data.get("conflicts") or [], 1):
        if not isinstance(item, dict):
            continue
        a = str(item.get("claim_a_id") or "")
        b = str(item.get("claim_b_id") or "")
        if a not in claim_ids or b not in claim_ids or a == b:
            continue
        conflicts.append(
            EvidenceConflict(
                id=f"CONFLICT-{i:03d}",
                claim_a_id=a,
                claim_b_id=b,
                summary=str(item.get("summary") or f"Conflict between {a} and {b}"),
            )
        )

    gaps: List[EvidenceGap] = []
    for i, item in enumerate(data.get("gaps") or [], 1):
        if not isinstance(item, dict):
            continue
        desc = str(item.get("description") or "").strip()
        if not desc:
            continue
        suggested = item.get("suggested_specialist")
        if suggested not in ("web", "academic", "repository", None):
            suggested = None
        gaps.append(
            EvidenceGap(
                id=f"GAP-{i:03d}",
                description=desc,
                related_sub_question_ids=[
                    str(x) for x in (item.get("related_sub_question_ids") or []) if x
                ],
                suggested_specialist=suggested,
            )
        )

    summary = str(data.get("summary") or analysis.summary).strip() or analysis.summary
    return EvidenceAnalysis(
        claims=analysis.claims,
        conflicts=conflicts or analysis.conflicts,
        gaps=gaps or analysis.gaps,
        summary=summary,
        llm_calls_used=1,
    )


def analyze_evidence(
    *,
    plan: InvestigationPlan,
    findings: List[ResearchFinding],
    sources: List[SourceRecord],
    use_llm: bool = True,
) -> EvidenceAnalysis:
    base = compile_evidence(plan=plan, findings=findings, sources=sources)
    if not use_llm or not findings:
        return base
    refined = _llm_refine(base, plan, findings)
    return refined if refined is not None else base
