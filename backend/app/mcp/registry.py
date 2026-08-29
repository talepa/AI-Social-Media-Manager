"""
mcp/registry.py

Capability registry: discover MCP servers/tools and scope them by specialist.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict, List, Literal, Optional

from langchain_core.tools import BaseTool

from app.mcp.adapter import mcp_tools_as_langchain
from app.mcp.servers import SERVERS
from app.schemas.investigation import SpecialistName

logger = logging.getLogger(__name__)

MCP_SERVER_NAMES = ("research", "academic", "repository")

SpecialistScope = Literal["web", "academic", "repository"]

_SPECIALIST_SERVER: Dict[SpecialistName, str] = {
    "web": "research",
    "academic": "academic",
    "repository": "repository",
}

_lock = threading.Lock()
_tool_cache: Dict[str, List[BaseTool]] = {}
_stats: Dict[str, int] = {}


def mcp_enabled() -> bool:
    return (os.getenv("USE_MCP") or "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _record_call(server: str, tool: str, _args: dict) -> None:
    key = f"{server}.{tool}"
    with _lock:
        _stats[key] = _stats.get(key, 0) + 1
    logger.info("mcp call: %s", key)


def get_langchain_tools_for_server(server_name: str) -> List[BaseTool]:
    if server_name not in SERVERS:
        raise KeyError(f"unknown MCP server: {server_name}")
    with _lock:
        cached = _tool_cache.get(server_name)
        if cached is not None:
            return list(cached)
    tools = mcp_tools_as_langchain(
        SERVERS[server_name],
        server_name=server_name,
        on_call=_record_call,
    )
    with _lock:
        _tool_cache[server_name] = tools
        return list(tools)


def get_langchain_tools_for_specialist(
    specialist: SpecialistName,
) -> List[BaseTool]:
    """Return MCP tools scoped to the specialist's domain server."""
    server = _SPECIALIST_SERVER[specialist]
    return get_langchain_tools_for_server(server)


def list_mcp_capabilities() -> dict:
    """Startup / health discovery payload."""
    servers = []
    for name, server in SERVERS.items():
        tools = get_langchain_tools_for_server(name)
        servers.append(
            {
                "name": name,
                "tool_count": len(tools),
                "tools": [
                    {"name": t.name, "description": (t.description or "")[:200]}
                    for t in tools
                ],
            }
        )
    return {
        "enabled": mcp_enabled(),
        "transport": "in-process",
        "servers": servers,
        "specialist_scope": dict(_SPECIALIST_SERVER),
        "call_stats": mcp_call_stats(),
    }


def mcp_call_stats() -> Dict[str, int]:
    with _lock:
        return dict(_stats)


def reset_mcp_registry_for_tests() -> None:
    with _lock:
        _tool_cache.clear()
        _stats.clear()
