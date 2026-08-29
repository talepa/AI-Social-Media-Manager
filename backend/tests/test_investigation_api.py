"""
Tests for POST /api/investigation/runs (Director + Specialists).

Mocks the Director LLM and specialist runners so the suite doesn't depend
on network access or API keys. Confirms the new router didn't disturb
existing /api/research/* surfaces (additive-only regression check).
"""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.investigation import (
    ResearchFinding,
    SourceRecord,
    SpecialistResult,
    SubQuestion,
)

client = TestClient(app)


def _fake_specialist_result(sq: SubQuestion, *, max_tool_calls: int = 1) -> SpecialistResult:
    prefix = {"web": "WEB", "academic": "PAPER", "repository": "GH"}[sq.specialist]
    source = SourceRecord(
        id=f"{prefix}-001",
        type={"web": "web", "academic": "papers", "repository": "github"}[sq.specialist],
        title=f"Mock source for {sq.id}",
        url=f"https://example.com/{sq.id}",
        content="Mock content",
        specialist=sq.specialist,
        sub_question_id=sq.id,
    )
    finding = ResearchFinding(
        id="F-001",
        sub_question_id=sq.id,
        specialist=sq.specialist,
        claim=f"Mock claim for {sq.id}",
        evidence_summary="Mock evidence",
        source_ids=[source.id],
        confidence=0.7,
    )
    return SpecialistResult(
        specialist=sq.specialist,
        sub_question_id=sq.id,
        sources=[source],
        findings=[finding],
        tool_calls_used=min(1, max_tool_calls),
        llm_calls_used=2,
    )


def test_start_run_returns_plan_and_specialist_results(monkeypatch):
    monkeypatch.setattr(
        "app.agents.director.get_llm",
        lambda **kw: (_ for _ in ()).throw(EnvironmentError("no key, use fallback")),
    )
    monkeypatch.setattr(
        "app.graphs.investigation_graph.run_for_sub_question",
        _fake_specialist_result,
    )

    res = client.post(
        "/api/investigation/runs",
        json={
            "question": "Is this GitHub repo production ready?",
            "mode": "evaluate",
            "depth": "quick",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"]
    plan = data["plan"]
    assert plan["max_tasks"] == 3
    assert plan["tool_budget"] == 6
    assert plan["depth"] == "quick"
    assert plan["mode"] == "evaluate"
    assert len(plan["sub_questions"]) <= 3

    assert len(data["specialist_results"]) == len(plan["sub_questions"])
    assert len(data["sources"]) >= 1
    assert len(data["findings"]) >= 1
    assert data["tool_calls_used"] >= 1
    assert any(e.get("event_type") == "plan_created" for e in data["events"])
    assert any(e.get("event_type") == "specialists_completed" for e in data["events"])
    assert any(e.get("event_type") == "evidence_analysis_completed" for e in data["events"])
    assert any(e.get("event_type") == "synthesis_completed" for e in data["events"])
    assert any(e.get("event_type") == "citation_validated" for e in data["events"])

    assert data["evidence"] is not None
    assert len(data["evidence"]["claims"]) >= 1
    assert data["evidence"]["claims"][0]["id"].startswith("CLAIM-")

    assert data["report"] is not None
    assert data["report"]["markdown"]
    assert "CLAIM-" in data["report"]["markdown"]

    assert data["verification"] is not None
    assert data["verification"]["passed"] is True

    source_ids = {s["id"] for s in data["sources"]}
    assert len(source_ids) == len(data["sources"])  # unique after aggregation
    for finding in data["findings"]:
        for sid in finding["source_ids"]:
            assert sid in source_ids


def test_start_run_rejects_empty_question():
    res = client.post("/api/investigation/runs", json={"question": ""})
    assert res.status_code == 422


def test_health_endpoint_unaffected():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_research_health_endpoint_unaffected():
    res = client.get("/api/health/research")
    assert res.status_code == 200
    body = res.json()
    assert body["orchestrator"] == "langgraph"
