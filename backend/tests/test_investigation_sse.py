"""
Tests for investigation run store + SSE/GET endpoints.
"""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.investigation import (
    InvestigationPlan,
    InvestigationRunResponse,
    ResearchFinding,
    SourceRecord,
    SpecialistResult,
    SubQuestion,
)
from app.services.investigation_store import InvestigationRunStore

client = TestClient(app)


def _minimal_response(run_id: str = "run-1") -> InvestigationRunResponse:
    plan = InvestigationPlan(
        objective="Test",
        mode="explore",
        depth="quick",
        sub_questions=[SubQuestion(id="Q1", text="t", specialist="web")],
        required_specialists=["web"],
        tool_budget=6,
        max_tasks=3,
    )
    return InvestigationRunResponse(
        run_id=run_id,
        plan=plan,
        events=[{"event_type": "plan_created", "run_id": run_id}],
    )


def test_store_create_complete_get():
    store = InvestigationRunStore(max_runs=10)
    store.create("r1", question="q", mode="explore", depth="quick")
    rec = store.get("r1")
    assert rec is not None
    assert rec.status == "running"
    store.append_events("r1", [{"event_type": "plan_created"}])
    result = _minimal_response("r1")
    store.complete("r1", result)
    rec = store.get("r1")
    assert rec.status == "completed"
    assert rec.result is not None
    assert rec.result.run_id == "r1"


def test_store_fail():
    store = InvestigationRunStore()
    store.create("r2", question="q", mode="explore", depth="quick")
    store.fail("r2", "boom")
    rec = store.get("r2")
    assert rec.status == "failed"
    assert rec.error == "boom"


def test_get_run_404():
    res = client.get("/api/investigation/runs/does-not-exist")
    assert res.status_code == 404


def test_get_run_after_sync(monkeypatch):
    from app.schemas.investigation import DirectorRequest

    fake = _minimal_response("fixed-id")

    def _fake_sync(body: DirectorRequest) -> InvestigationRunResponse:
        from app.services import investigation_store as store_mod

        store_mod.investigation_store.create(
            "fixed-id",
            question=body.question,
            mode=body.mode,
            depth=body.depth,
        )
        store_mod.investigation_store.complete("fixed-id", fake)
        return fake

    monkeypatch.setattr(
        "app.api.investigation.run_investigation_sync",
        _fake_sync,
    )
    res = client.post(
        "/api/investigation/runs",
        json={"question": "test question", "mode": "explore", "depth": "quick"},
    )
    assert res.status_code == 200
    assert res.json()["run_id"] == "fixed-id"

    got = client.get("/api/investigation/runs/fixed-id")
    assert got.status_code == 200
    body = got.json()
    assert body["status"] == "completed"
    assert body["result"]["plan"]["objective"] == "Test"


def test_stream_endpoint_emits_sse(monkeypatch):
    def _fake_sse(body):
        yield 'event: accepted\ndata: {"run_id": "s1"}\n\n'
        yield 'event: progress\ndata: {"event_type": "plan_created"}\n\n'
        yield 'event: complete\ndata: {"run_id": "s1"}\n\n'

    monkeypatch.setattr(
        "app.api.investigation.iter_investigation_sse",
        _fake_sse,
    )
    with client.stream(
        "POST",
        "/api/investigation/runs/stream",
        json={"question": "stream me", "mode": "explore", "depth": "quick"},
    ) as res:
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        text = "".join(res.iter_text())
    assert "event: accepted" in text
    assert "event: progress" in text
    assert "event: complete" in text


def test_existing_sync_api_still_works(monkeypatch):
    monkeypatch.setattr(
        "app.agents.director.get_llm",
        lambda **kw: (_ for _ in ()).throw(EnvironmentError("no key")),
    )

    def _fake_specialist(sq: SubQuestion, *, max_tool_calls: int = 1) -> SpecialistResult:
        src = SourceRecord(
            id="WEB-001",
            type="web",
            title="t",
            url="https://example.com",
            specialist=sq.specialist,
            sub_question_id=sq.id,
        )
        return SpecialistResult(
            specialist=sq.specialist,
            sub_question_id=sq.id,
            sources=[src],
            findings=[
                ResearchFinding(
                    id="F-001",
                    sub_question_id=sq.id,
                    specialist=sq.specialist,
                    claim="c",
                    source_ids=["WEB-001"],
                    confidence=0.6,
                )
            ],
            tool_calls_used=1,
            llm_calls_used=1,
        )

    monkeypatch.setattr(
        "app.graphs.investigation_graph.run_for_sub_question",
        _fake_specialist,
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
    run_id = data["run_id"]
    assert data["evidence"] is not None
    assert data["report"] is not None

    stored = client.get(f"/api/investigation/runs/{run_id}")
    assert stored.status_code == 200
    assert stored.json()["status"] == "completed"
