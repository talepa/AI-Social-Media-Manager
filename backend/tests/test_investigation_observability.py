"""
Tests for optional LLM polish flag + evidence/synthesis failure fallbacks.
"""

from app.agents.evidence_analyst import compile_evidence
from app.graphs.investigation_graph import evidence_analyst_node, synthesis_node
from app.schemas.investigation import (
    InvestigationPlan,
    ResearchFinding,
    SourceRecord,
    SubQuestion,
)
from app.services.investigation_runner import initial_state
from app.schemas.investigation import DirectorRequest


def _plan_state(*, use_llm: bool = False) -> dict:
    plan = InvestigationPlan(
        objective="Evaluate readiness",
        mode="evaluate",
        depth="quick",
        sub_questions=[SubQuestion(id="Q1", text="ready?", specialist="web")],
        required_specialists=["web"],
        tool_budget=6,
        max_tasks=3,
    )
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
            claim="LangGraph is used in production",
            source_ids=["WEB-001"],
            confidence=0.8,
        )
    ]
    return {
        "run_id": "run-test",
        "question": "Is LangGraph production ready?",
        "mode": "evaluate",
        "depth": "quick",
        "use_llm": use_llm,
        "plan": plan.model_dump(mode="json"),
        "findings": [f.model_dump(mode="json") for f in findings],
        "sources": [s.model_dump(mode="json") for s in sources],
        "tool_calls_used": 1,
        "llm_calls_used": 1,
        "errors": {},
        "events": [],
    }


def test_initial_state_carries_use_llm():
    body = DirectorRequest(
        question="test",
        mode="explore",
        depth="quick",
        use_llm=True,
    )
    state = initial_state("r1", body)
    assert state["use_llm"] is True


def test_evidence_node_respects_use_llm_false(monkeypatch):
    called = {"use_llm": None}

    def _fake_analyze(*, plan, findings, sources, use_llm=True):
        called["use_llm"] = use_llm
        return compile_evidence(plan=plan, findings=findings, sources=sources)

    monkeypatch.setattr(
        "app.graphs.investigation_graph.analyze_evidence",
        _fake_analyze,
    )
    out = evidence_analyst_node(_plan_state(use_llm=False))
    assert called["use_llm"] is False
    assert out["evidence"] is not None
    assert out["events"][0]["use_llm"] is False
    assert "elapsed_ms" in out["events"][0]


def test_evidence_node_respects_use_llm_true(monkeypatch):
    called = {"use_llm": None}

    def _fake_analyze(*, plan, findings, sources, use_llm=True):
        called["use_llm"] = use_llm
        analysis = compile_evidence(plan=plan, findings=findings, sources=sources)
        return analysis.model_copy(update={"llm_calls_used": 1})

    monkeypatch.setattr(
        "app.graphs.investigation_graph.analyze_evidence",
        _fake_analyze,
    )
    out = evidence_analyst_node(_plan_state(use_llm=True))
    assert called["use_llm"] is True
    assert out["events"][0]["llm_polished"] is True
    assert out["llm_calls_used"] == 2  # prior 1 + 1


def test_evidence_node_falls_back_on_exception(monkeypatch):
    def _boom(*, plan, findings, sources, use_llm=True):
        raise RuntimeError("llm down")

    monkeypatch.setattr(
        "app.graphs.investigation_graph.analyze_evidence",
        _boom,
    )
    out = evidence_analyst_node(_plan_state(use_llm=True))
    assert out["evidence"] is not None
    assert out["errors"]["evidence"] == "llm down"
    assert any(e["event_type"] == "evidence_analysis_fallback" for e in out["events"])
    assert any(e["event_type"] == "evidence_analysis_completed" for e in out["events"])


def test_synthesis_node_falls_back_on_exception(monkeypatch):
    state = _plan_state(use_llm=True)
    # seed evidence
    ev = evidence_analyst_node({**state, "use_llm": False})
    state["evidence"] = ev["evidence"]

    def _boom(*, plan, evidence, sources, use_llm=False):
        raise RuntimeError("synth fail")

    monkeypatch.setattr(
        "app.graphs.investigation_graph.synthesize_report",
        _boom,
    )
    out = synthesis_node(state)
    assert out["report"] is not None
    assert out["verification"] is not None
    assert out["errors"]["synthesis"] == "synth fail"
    assert any(e["event_type"] == "synthesis_fallback" for e in out["events"])
    assert out["report"]["mode"] == "compile"
