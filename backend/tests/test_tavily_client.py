"""
Tests for Tavily web search used by the investigation Web specialist.

Mocks the Tavily client so tests run without TAVILY_API_KEY or network access.
"""

import sys
from types import ModuleType

import pytest

from app.services.tavily_client import search_web


def _install_fake_tavily(monkeypatch, client_cls):
    fake = ModuleType("tavily")
    fake.TavilyClient = client_cls
    monkeypatch.setitem(sys.modules, "tavily", fake)


def test_empty_topic_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        search_web("")


def test_negative_limit_raises():
    with pytest.raises(ValueError, match="must be >= 1"):
        search_web("test", limit=0)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY is not set"):
        search_web("test query")


def test_limit_clamped_to_20(monkeypatch):
    """Verify limit is silently clamped, not rejected."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    captured = {}

    class _MockClient:
        def __init__(self, api_key=None):
            pass

        def search(self, **kwargs):
            captured.update(kwargs)
            return {"results": [], "answer": None, "images": []}

    _install_fake_tavily(monkeypatch, _MockClient)
    results, answer, images = search_web("test", limit=50)
    assert results == []
    assert answer is None
    assert captured.get("max_results") == 20


def test_successful_response_mapping(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    tavily_response = {
        "results": [
            {
                "title": "LangGraph Docs",
                "url": "https://docs.langgraph.dev",
                "content": "Official LangGraph documentation",
                "score": 0.91,
                "images": ["https://img.example.com/thumb.png"],
                "favicon": "https://docs.langgraph.dev/favicon.ico",
            },
            {
                "title": "LangGraph GitHub",
                "url": "https://github.com/langchain-ai/langgraph",
                "content": "LangGraph repo on GitHub",
                "score": 0.8,
            },
            {
                "title": "",
                "url": "",
                "content": "should be skipped",
            },
        ],
        "answer": "LangGraph is a framework for agent workflows.",
        "images": ["https://img.example.com/thumb.png"],
    }

    class _MockClient:
        def __init__(self, api_key=None):
            pass

        def search(self, **kwargs):
            return tavily_response

    _install_fake_tavily(monkeypatch, _MockClient)
    results, answer, images = search_web("langgraph", limit=5)

    assert len(results) == 2
    assert results[0].title == "LangGraph Docs"
    assert results[0].url == "https://docs.langgraph.dev"
    assert results[0].content == "Official LangGraph documentation"
    assert results[0].image_url == "https://img.example.com/thumb.png"
    assert results[0].favicon_url == "https://docs.langgraph.dev/favicon.ico"
    assert results[0].score == pytest.approx(0.91)

    assert results[1].title == "LangGraph GitHub"
    assert results[1].image_url is None

    assert answer == "LangGraph is a framework for agent workflows."
    assert len(images) == 1


def test_time_range_param_passed(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    captured = {}

    class _MockClient:
        def __init__(self, api_key=None):
            pass

        def search(self, **kwargs):
            captured.update(kwargs)
            return {"results": [], "answer": None, "images": []}

    _install_fake_tavily(monkeypatch, _MockClient)
    search_web("test", time_range="week")
    assert captured["time_range"] == "week"


def test_search_error_raises_runtime(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class _MockClient:
        def __init__(self, api_key=None):
            pass

        def search(self, **kwargs):
            raise Exception("upstream failure")

    _install_fake_tavily(monkeypatch, _MockClient)
    with pytest.raises(RuntimeError, match="Tavily search failed"):
        search_web("test")
