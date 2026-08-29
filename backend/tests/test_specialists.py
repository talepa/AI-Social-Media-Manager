"""
Tests for specialist agents — Web, Academic, and Repository.

All tests mock the LLM and tools so they run without API keys or network.
"""

import json

import pytest

from app.agents.specialists.base import run_specialist
from app.schemas.investigation import SubQuestion


class _FakeToolCallResponse:
    """Simulates an AIMessage with one tool call."""

    def __init__(self, tool_name: str, tool_args: dict, call_id: str = "call_1"):
        self.content = ""
        self.tool_calls = [{"name": tool_name, "args": tool_args, "id": call_id}]


class _FakeFinalResponse:
    """Simulates an AIMessage with no tool calls (agent is done)."""

    def __init__(self, content: str = "Done researching."):
        self.content = content
        self.tool_calls = []


class _FakeFindingsResponse:
    """Simulates the findings extraction LLM call."""

    def __init__(self, findings: list):
        self.content = json.dumps(findings)
        self.tool_calls = []


class _MockLLM:
    """Mock LLM that returns a tool call on first invoke, then stops."""

    def __init__(self, findings=None):
        self._call_count = 0
        self._findings = findings or [
            {
                "claim": "Test claim from mock",
                "evidence_summary": "Mock evidence summary",
                "source_indices": [0],
                "confidence": 0.8,
                "methodology_note": None,
            }
        ]

    def bind_tools(self, tools):
        self._tool_names = [t.name for t in tools]
        return self

    def invoke(self, messages):
        self._call_count += 1

        # Findings extraction call (last call, triggered by _FINDINGS_PROMPT)
        last_msg = messages[-1] if messages else None
        if hasattr(last_msg, "content") and "JSON array" in (last_msg.content or ""):
            return _FakeFindingsResponse(self._findings)

        # First agent call: issue a tool call
        if self._call_count == 1 and self._tool_names:
            return _FakeToolCallResponse(
                self._tool_names[0],
                {"query" if "search" in self._tool_names[0] else "topic": "test query", "limit": 3},
            )

        # Second agent call: no more tools
        return _FakeFinalResponse()


class _MockAlwaysCallsLLM:
    """Mock LLM that always wants to call tools (for budget testing)."""

    def __init__(self):
        self._call_count = 0

    def bind_tools(self, tools):
        self._tool_names = [t.name for t in tools]
        return self

    def invoke(self, messages):
        self._call_count += 1
        last_msg = messages[-1] if messages else None
        if hasattr(last_msg, "content") and "JSON array" in (last_msg.content or ""):
            return _FakeFindingsResponse([{
                "claim": "Budget test finding",
                "evidence_summary": "Budget was enforced",
                "source_indices": [],
                "confidence": 0.5,
            }])
        return _FakeToolCallResponse(
            self._tool_names[0],
            {"query": "test", "limit": 3},
            call_id=f"call_{self._call_count}",
        )


def _fake_tool(name: str):
    """Create a mock LangChain tool that returns canned results."""
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def _search(query: str, limit: int = 5):
        """Mock search tool."""
        return [
            {"title": f"Result for {query}", "url": f"https://example.com/{i}", "content": f"Content about {query}"}
            for i in range(min(limit, 3))
        ]

    _search.name = name
    return _search


_SQ = SubQuestion(id="Q1", text="Is LangGraph production ready?", specialist="web", rationale="Assess maturity")


def test_web_specialist_produces_result(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search"), _fake_tool("news_search")],
        system_prompt="You are a web specialist.",
        max_tool_calls=4,
    )
    assert result.specialist == "web"
    assert result.sub_question_id == "Q1"
    assert len(result.sources) > 0
    assert result.tool_calls_used >= 1
    assert result.llm_calls_used >= 2
    assert result.error is None
    assert len(result.findings) >= 1
    assert result.findings[0].claim == "Test claim from mock"


def test_academic_specialist_produces_result(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    sq = SubQuestion(id="Q2", text="Recent research on RAG", specialist="academic", rationale="Survey papers")
    result = run_specialist(
        sub_question=sq,
        specialist_name="academic",
        tools=[_fake_tool("papers_search")],
        system_prompt="You are an academic specialist.",
        max_tool_calls=3,
    )
    assert result.specialist == "academic"
    assert result.sub_question_id == "Q2"
    assert len(result.sources) > 0
    assert result.error is None


def test_repository_specialist_produces_result(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    sq = SubQuestion(id="Q3", text="LangGraph GitHub activity", specialist="repository", rationale="Check repo")
    result = run_specialist(
        sub_question=sq,
        specialist_name="repository",
        tools=[_fake_tool("github_search")],
        system_prompt="You are a repository specialist.",
        max_tool_calls=3,
    )
    assert result.specialist == "repository"
    assert result.sub_question_id == "Q3"
    assert len(result.sources) > 0
    assert result.error is None


def test_budget_enforcement(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockAlwaysCallsLLM())
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search")],
        system_prompt="You are a web specialist.",
        max_tool_calls=2,
    )
    assert result.tool_calls_used <= 2
    assert result.error is None


def test_missing_api_key_returns_error(monkeypatch):
    def _raise(**kw):
        raise EnvironmentError("GOOGLE_API_KEY not set")

    monkeypatch.setattr("app.agents.specialists.base.get_llm", _raise)
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search")],
        system_prompt="You are a web specialist.",
    )
    assert result.error is not None
    assert "GOOGLE_API_KEY" in result.error
    assert result.sources == []
    assert result.findings == []


def test_source_ids_have_correct_prefix(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search")],
        system_prompt="You are a web specialist.",
    )
    for source in result.sources:
        assert source.id.startswith("WEB-")

    sq = SubQuestion(id="Q2", text="Papers on RAG", specialist="academic", rationale="Find papers")
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    result = run_specialist(
        sub_question=sq,
        specialist_name="academic",
        tools=[_fake_tool("papers_search")],
        system_prompt="You are an academic specialist.",
    )
    for source in result.sources:
        assert source.id.startswith("PAPER-")


def test_findings_have_valid_source_ids(monkeypatch):
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM())
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search")],
        system_prompt="You are a web specialist.",
    )
    all_source_ids = {s.id for s in result.sources}
    for finding in result.findings:
        for sid in finding.source_ids:
            assert sid in all_source_ids, f"Finding references unknown source {sid}"


def test_findings_confidence_bounded(monkeypatch):
    findings_data = [
        {"claim": "High confidence", "evidence_summary": "Strong", "source_indices": [0], "confidence": 1.5},
        {"claim": "Negative confidence", "evidence_summary": "Bad", "source_indices": [], "confidence": -0.5},
    ]
    monkeypatch.setattr("app.agents.specialists.base.get_llm", lambda **kw: _MockLLM(findings=findings_data))
    result = run_specialist(
        sub_question=_SQ,
        specialist_name="web",
        tools=[_fake_tool("brave_search")],
        system_prompt="You are a web specialist.",
    )
    for f in result.findings:
        assert 0.0 <= f.confidence <= 1.0
