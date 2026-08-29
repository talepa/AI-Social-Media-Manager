"""
Tests for app.agents.director — the Research Director.

These are deterministic/mocked tests (no real network/LLM calls) so the
suite runs fast and doesn't depend on GOOGLE_API_KEY. The one exception is
test_create_research_plan_live, which is skipped unless GOOGLE_API_KEY is
actually configured.
"""

import json
import os

import pytest

from app.agents.director import _fallback_plan, create_research_plan
from app.schemas.investigation import DEPTH_BUDGETS


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, _msgs):
        return _FakeResponse(self._content)


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_fallback_plan_budgets_by_depth(depth):
    plan = _fallback_plan("What is the capital of France?", "explore", depth)
    max_tasks, tool_budget = DEPTH_BUDGETS[depth]
    assert plan.max_tasks == max_tasks
    assert plan.tool_budget == tool_budget
    assert len(plan.sub_questions) <= max_tasks


def test_fallback_plan_technical_question_adds_repository():
    plan = _fallback_plan(
        "Is this GitHub repository framework production ready?", "evaluate", "standard"
    )
    assert "repository" in plan.required_specialists
    assert "web" in plan.required_specialists


def test_fallback_plan_non_technical_question_is_web_only():
    plan = _fallback_plan("What are the benefits of morning walks?", "explore", "quick")
    assert plan.required_specialists == ["web"]


def test_create_research_plan_falls_back_without_api_key(monkeypatch):
    def _raise(*args, **kwargs):
        raise EnvironmentError("no key")

    monkeypatch.setattr("app.agents.director.get_llm", _raise)
    plan = create_research_plan("Compare Kafka and Pulsar", mode="compare", depth="standard")
    assert plan.max_tasks == DEPTH_BUDGETS["standard"][0]
    assert "fallback" in plan.reason.lower()


def test_create_research_plan_falls_back_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        "app.agents.director.get_llm", lambda **kw: _FakeLLM("not valid json at all")
    )
    plan = create_research_plan("Evaluate vector databases for RAG", mode="evaluate", depth="deep")
    assert plan.max_tasks == DEPTH_BUDGETS["deep"][0]
    assert "fallback" in plan.reason.lower()


def test_create_research_plan_falls_back_on_empty_sub_questions(monkeypatch):
    payload = json.dumps(
        {
            "objective": "test",
            "sub_questions": [],
            "required_specialists": ["web"],
            "evidence_requirements": [],
            "freshness_requirement": None,
            "success_criteria": [],
            "reason": "empty",
        }
    )
    monkeypatch.setattr("app.agents.director.get_llm", lambda **kw: _FakeLLM(payload))
    plan = create_research_plan("Anything", mode="explore", depth="quick")
    assert "fallback" in plan.reason.lower()
    assert len(plan.sub_questions) >= 1


def test_create_research_plan_truncates_to_max_tasks(monkeypatch):
    # LLM tries to return more sub_questions than the quick-depth budget allows (3).
    sub_qs = [
        {"id": f"Q{i}", "text": f"question {i}", "specialist": "web", "rationale": "r"}
        for i in range(1, 8)
    ]
    payload = json.dumps(
        {
            "objective": "test objective",
            "sub_questions": sub_qs,
            "required_specialists": ["web"],
            "evidence_requirements": [],
            "freshness_requirement": None,
            "success_criteria": [],
            "reason": "overproduced plan",
        }
    )
    monkeypatch.setattr("app.agents.director.get_llm", lambda **kw: _FakeLLM(payload))
    plan = create_research_plan("Anything", mode="explore", depth="quick")
    assert plan.max_tasks == 3
    assert len(plan.sub_questions) == 3
    assert plan.reason == "overproduced plan"


def test_create_research_plan_strips_markdown_fences(monkeypatch):
    payload = json.dumps(
        {
            "objective": "fenced",
            "sub_questions": [
                {"id": "Q1", "text": "q", "specialist": "academic", "rationale": "r"}
            ],
            "required_specialists": ["academic"],
            "evidence_requirements": [],
            "freshness_requirement": None,
            "success_criteria": [],
            "reason": "fenced plan",
        }
    )
    fenced = f"```json\n{payload}\n```"
    monkeypatch.setattr("app.agents.director.get_llm", lambda **kw: _FakeLLM(fenced))
    plan = create_research_plan("What does research say about X?", mode="academic", depth="standard")
    assert plan.required_specialists == ["academic"]
    assert plan.reason == "fenced plan"


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not configured"
)
def test_create_research_plan_live():
    plan = create_research_plan(
        "Should a startup use LangGraph for a production multi-agent system?",
        mode="evaluate",
        depth="standard",
    )
    assert plan.sub_questions
    assert plan.required_specialists
    assert plan.max_tasks == DEPTH_BUDGETS["standard"][0]
