"""
Tests for first-party MCP servers + LangChain adapter.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.mcp.adapter import _unwrap_tool_result, mcp_tools_as_langchain
from app.mcp.registry import (
    get_langchain_tools_for_specialist,
    list_mcp_capabilities,
    reset_mcp_registry_for_tests,
)
from app.mcp.servers import SERVERS
from app.mcp.servers.research import research_mcp


client = TestClient(app)


def setup_function():
    reset_mcp_registry_for_tests()


def test_three_mcp_servers_registered():
    assert set(SERVERS) == {"research", "academic", "repository"}


def test_research_server_exposes_expected_tools():
    tools = mcp_tools_as_langchain(research_mcp, server_name="research")
    names = {t.name for t in tools}
    assert "search_web" in names
    assert "search_news" in names
    assert "fetch_url" in names
    assert "get_page_metadata" in names


def test_specialist_tool_scoping():
    web = {t.name for t in get_langchain_tools_for_specialist("web")}
    acad = {t.name for t in get_langchain_tools_for_specialist("academic")}
    repo = {t.name for t in get_langchain_tools_for_specialist("repository")}
    assert "search_web" in web
    assert "search_papers" in acad
    assert "search_repositories" in repo
    assert "search_web" not in acad
    assert "search_papers" not in repo


def test_unwrap_items_payload():
    class Fake:
        structured_content = {"items": [{"title": "A", "url": "https://x"}]}
        content = []
        is_error = False

    assert _unwrap_tool_result(Fake()) == [{"title": "A", "url": "https://x"}]


def test_unwrap_single_record():
    class Fake:
        structured_content = {"title": "Repo", "url": "https://github.com/a/b"}
        content = []
        is_error = False

    out = _unwrap_tool_result(Fake())
    assert isinstance(out, list) and out[0]["title"] == "Repo"


def test_capabilities_endpoint():
    res = client.get("/api/mcp/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is True
    assert data["transport"] == "in-process"
    names = {s["name"] for s in data["servers"]}
    assert names == {"research", "academic", "repository"}
    research = next(s for s in data["servers"] if s["name"] == "research")
    assert research["tool_count"] >= 4


def test_list_mcp_capabilities_helper():
    caps = list_mcp_capabilities()
    assert caps["specialist_scope"]["web"] == "research"


def test_health_includes_mcp():
    res = client.get("/health")
    assert res.status_code == 200
    assert "mcp" in res.json()
