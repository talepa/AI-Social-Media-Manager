"""
Tests for Evidence Analyst — deterministic claim consolidation, conflicts, gaps.
"""

from app.agents.evidence_analyst import analyze_evidence, compile_evidence
from app.schemas.investigation import (
    InvestigationPlan,
    ResearchFinding,
    SourceRecord,
    SubQuestion,
)


def _plan(*sqs: SubQuestion) -> InvestigationPlan:
    return InvestigationPlan(
        objective="Decide if LangGraph is production ready",
        mode="evaluate",
        depth="quick",
        sub_questions=list(sqs),
        required_specialists=sorted({s.specialist for s in sqs}),
        evidence_requirements=["production deployment evidence"],
        tool_budget=6,
        max_tasks=3,
    )


def test_compile_promotes_findings_to_claims():
    sq = SubQuestion(id="Q1", text="Is it ready?", specialist="web")
    sources = [
        SourceRecord(
            id="WEB-001",
            type="web",
            title="Docs",
            url="https://example.com",
            specialist="web",
            sub_question_id="Q1",
        )
    ]
    findings = [
        ResearchFinding(
            id="F-001",
            sub_question_id="Q1",
            specialist="web",
            claim="LangGraph is used in production by multiple teams",
            source_ids=["WEB-001"],
            confidence=0.8,
        )
    ]
    analysis = compile_evidence(
        plan=_plan(sq),
        findings=findings,
        sources=sources,
    )
    assert len(analysis.claims) == 1
    claim = analysis.claims[0]
    assert claim.id == "CLAIM-001"
    assert claim.supporting_source_ids == ["WEB-001"]
    assert "web" in claim.source_families
    assert claim.strength in ("strong", "moderate", "weak")
    assert analysis.llm_calls_used == 0


def test_gap_when_sub_question_has_no_findings():
    sq1 = SubQuestion(id="Q1", text="Web view", specialist="web")
    sq2 = SubQuestion(id="Q2", text="Repo health", specialist="repository")
    findings = [
        ResearchFinding(
            id="F-001",
            sub_question_id="Q1",
            specialist="web",
            claim="Something about web",
            source_ids=[],
            confidence=0.5,
        )
    ]
    analysis = compile_evidence(plan=_plan(sq1, sq2), findings=findings, sources=[])
    gap_sqs = {g.id: g for g in analysis.gaps}
    assert any("Q2" in g.description or "Q2" in g.related_sub_question_ids for g in analysis.gaps)
    assert gap_sqs  # at least one gap


def test_conflict_detection_opposite_polarity():
    sq = SubQuestion(id="Q1", text="Readiness", specialist="web")
    findings = [
        ResearchFinding(
            id="F-001",
            sub_question_id="Q1",
            specialist="web",
            claim="LangGraph is production ready for multi-agent workflows",
            source_ids=["WEB-001"],
            confidence=0.8,
        ),
        ResearchFinding(
            id="F-002",
            sub_question_id="Q1",
            specialist="web",
            claim="LangGraph is not production ready for multi-agent workflows",
            source_ids=["WEB-002"],
            confidence=0.7,
        ),
    ]
    sources = [
        SourceRecord(
            id="WEB-001",
            type="web",
            title="A",
            url="https://a.example",
            specialist="web",
            sub_question_id="Q1",
        ),
        SourceRecord(
            id="WEB-002",
            type="web",
            title="B",
            url="https://b.example",
            specialist="web",
            sub_question_id="Q1",
        ),
    ]
    analysis = compile_evidence(plan=_plan(sq), findings=findings, sources=sources)
    assert len(analysis.conflicts) >= 1
    assert analysis.conflicts[0].claim_a_id.startswith("CLAIM-")
    assert analysis.conflicts[0].claim_b_id.startswith("CLAIM-")


def test_analyze_evidence_without_llm_key(monkeypatch):
    monkeypatch.setattr(
        "app.agents.evidence_analyst.get_llm",
        lambda **kw: (_ for _ in ()).throw(EnvironmentError("no key")),
    )
    sq = SubQuestion(id="Q1", text="x", specialist="web")
    analysis = analyze_evidence(
        plan=_plan(sq),
        findings=[
            ResearchFinding(
                id="F-001",
                sub_question_id="Q1",
                specialist="web",
                claim="Claim text here",
                source_ids=[],
                confidence=0.4,
            )
        ],
        sources=[],
        use_llm=True,
    )
    assert len(analysis.claims) == 1
    assert analysis.llm_calls_used == 0
