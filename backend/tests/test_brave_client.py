"""
Tests for app.services.brave_client — the Brave Search API client.

All tests mock httpx so they run without BRAVE_API_KEY or network access.
"""

import json

import pytest

from app.services.brave_client import search_web


def test_empty_topic_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        search_web("")


def test_negative_limit_raises():
    with pytest.raises(ValueError, match="must be >= 1"):
        search_web("test", limit=0)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="BRAVE_API_KEY is not set"):
        search_web("test query")


def test_limit_clamped_to_20(monkeypatch):
    """Verify limit is silently clamped, not rejected."""
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")

    import httpx

    class _MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"web": {"results": []}}

    class _MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def get(self, url, *, params=None, headers=None):
            assert params["count"] == 20
            return _MockResponse()

    monkeypatch.setattr(httpx, "Client", lambda **kw: _MockClient())
    results, answer, images = search_web("test", limit=50)
    assert results == []
    assert answer is None


def test_successful_response_mapping(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")

    import httpx

    brave_response = {
        "web": {
            "results": [
                {
                    "title": "LangGraph Docs",
                    "url": "https://docs.langgraph.dev",
                    "description": "Official LangGraph documentation",
                    "thumbnail": {"src": "https://img.example.com/thumb.png"},
                    "profile": {"img": "https://docs.langgraph.dev/favicon.ico"},
                },
                {
                    "title": "LangGraph GitHub",
                    "url": "https://github.com/langchain-ai/langgraph",
                    "description": "LangGraph repo on GitHub",
                },
                {
                    "title": "",
                    "url": "",
                    "description": "should be skipped",
                },
            ]
        }
    }

    class _MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return brave_response

    class _MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def get(self, url, *, params=None, headers=None):
            return _MockResponse()

    monkeypatch.setattr(httpx, "Client", lambda **kw: _MockClient())
    results, answer, images = search_web("langgraph", limit=5)

    assert len(results) == 2
    assert results[0].title == "LangGraph Docs"
    assert results[0].url == "https://docs.langgraph.dev"
    assert results[0].content == "Official LangGraph documentation"
    assert results[0].image_url == "https://img.example.com/thumb.png"
    assert results[0].favicon_url == "https://docs.langgraph.dev/favicon.ico"
    assert results[0].score is None

    assert results[1].title == "LangGraph GitHub"
    assert results[1].image_url is None

    assert answer is None
    assert len(images) == 1


def test_freshness_param_passed(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")

    import httpx

    captured_params = {}

    class _MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"web": {"results": []}}

    class _MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def get(self, url, *, params=None, headers=None):
            captured_params.update(params)
            return _MockResponse()

    monkeypatch.setattr(httpx, "Client", lambda **kw: _MockClient())
    search_web("test", freshness="pw")
    assert captured_params["freshness"] == "pw"


def test_http_error_raises_runtime(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")

    import httpx

    class _MockResponse:
        status_code = 429
        text = "Rate limited"
        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "429", request=httpx.Request("GET", "http://x"), response=self,
            )

    class _MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def get(self, url, *, params=None, headers=None):
            return _MockResponse()

    monkeypatch.setattr(httpx, "Client", lambda **kw: _MockClient())
    with pytest.raises(RuntimeError, match="Brave Search API error 429"):
        search_web("test")
