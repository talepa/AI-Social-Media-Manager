"""
Tests for Synthesis Agent + citation validation.
"""

from app.agents.evidence_analyst import compile_evidence
from app.agents.synthesizer import compile_report, synthesize_report, validate_citations
from app.schemas.investigation import (
    InvestigationPlan,
    InvestigationReport,
    ResearchFinding,
    SourceRecord,
    SubQuestion,
)


def _fixtures():
    plan = InvestigationPlan(
        objective="Evaluate LangGraph readiness",
        mode="evaluate",
        depth="quick",
        sub_questions=[
            SubQuestion(id="Q1", text="Is it ready?", specialist="web"),
        ],
        required_specialists=["web"],
        tool_budget=6,
        max_tasks=3,
    )
    sources = [
        SourceRecord(
            id="WEB-001",
            type="web",
            title="Docs",
            url="https://example.com/docs",
            specialist="web",
            sub_question_id="Q1",
        )
    ]
    findings = [
        ResearchFinding(
            id="F-001",
            sub_question_id="Q1",
            specialist="web",
            claim="LangGraph supports durable execution in production",
            source_ids=["WEB-001"],
            confidence=0.75,
        )
    ]
    evidence = compile_evidence(plan=plan, findings=findings, sources=sources)
    return plan, sources, evidence


def test_compile_report_cites_claims_and_sources():
    plan, sources, evidence = _fixtures()
    report = compile_report(plan=plan, evidence=evidence, sources=sources)
    assert report.mode == "compile"
    assert "WEB-001" in report.markdown
    assert "CLAIM-001" in report.cited_claim_ids
    assert "WEB-001" in report.cited_source_ids
    assert any(s.title == "Short answer" for s in report.sections)
    assert any(s.title == "Details" for s in report.sections)
    details = next(s for s in report.sections if s.title == "Details")
    assert "(WEB-" not in details.body
    assert "[[" in details.body  # footnote encoding for UI
    assert "CLAIM-001" in details.claim_ids


def test_citation_validation_passes_for_compile():
    plan, sources, evidence = _fixtures()
    report = compile_report(plan=plan, evidence=evidence, sources=sources)
    verification = validate_citations(report, evidence=evidence, sources=sources)
    assert verification.passed is True
    assert verification.invalid_citations == []


def test_citation_validation_fails_on_invented_id():
    plan, sources, evidence = _fixtures()
    report = InvestigationReport(
        headline="Bad report",
        executive_summary="Mentions CLAIM-999 and WEB-999 which do not exist",
        sections=[],
        cited_claim_ids=["CLAIM-999"],
        cited_source_ids=["WEB-999"],
        markdown="# Bad\nSee CLAIM-999 and WEB-999",
        mode="llm",
    )
    verification = validate_citations(report, evidence=evidence, sources=sources)
    assert verification.passed is False
    assert "CLAIM-999" in verification.invalid_citations
    assert "WEB-999" in verification.missing_sources


def test_synthesize_report_end_to_end():
    plan, sources, evidence = _fixtures()
    report, verification = synthesize_report(
        plan=plan,
        evidence=evidence,
        sources=sources,
        use_llm=False,
    )
    assert report.markdown
    assert verification.passed is True
