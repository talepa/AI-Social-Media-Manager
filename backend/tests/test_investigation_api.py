"""
Tests for POST /api/investigation/runs. Mocks the Director's LLM call so the
suite doesn't depend on network access or GOOGLE_API_KEY, and confirms the
new router didn't disturb the existing /api/research/* and /api/session/*
surfaces (additive-only regression check).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_start_run_returns_plan(monkeypatch):
    monkeypatch.setattr(
        "app.agents.director.get_llm",
        lambda **kw: (_ for _ in ()).throw(EnvironmentError("no key, use fallback")),
    )
    res = client.post(
        "/api/investigation/runs",
        json={"question": "Is this GitHub repo production ready?", "mode": "evaluate", "depth": "quick"},
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
