"""
mcp/adapter.py

Convert in-process MCPServer tools into LangChain BaseTools so specialists
can bind them for Gemini tool-calling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

_loop_local = threading.local()


def _run_async(coro):
    """Run a coroutine from sync specialist code (safe with/without running loop)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Nested event loop — use a dedicated thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _unwrap_tool_result(result: Any) -> Any:
    """
    Normalize CallToolResult → Python value for the specialist loop.

    Prefer structured_content; else parse text JSON. If payload has
    ``items`` (our MCP convention), return that list so SourceRecord
    extraction works unchanged.
    """
    if result is None:
        return []

    data: Any = None
    if getattr(result, "structured_content", None) is not None:
        data = result.structured_content
        if isinstance(data, dict) and "result" in data and len(data) == 1:
            data = data["result"]
    elif getattr(result, "content", None):
        texts = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                texts.append(text)
        raw = "\n".join(texts).strip()
        if not raw:
            data = []
        else:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = [{"title": "MCP result", "content": raw[:600], "url": ""}]

    if getattr(result, "is_error", False):
        raise RuntimeError(str(data) if data else "MCP tool error")

    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Single-record tools (get_repository, get_paper, …)
        return [data]
    return data if data is not None else []


def _schema_to_args_model(tool_name: str, schema: Optional[dict]) -> type[BaseModel]:
    """Build a pydantic args model from MCP JSON schema (best-effort)."""
    props = (schema or {}).get("properties") or {}
    required = set((schema or {}).get("required") or [])
    fields: Dict[str, Any] = {}

    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for name, prop in props.items():
        prop = prop or {}
        json_type = prop.get("type") or "string"
        if isinstance(json_type, list):
            json_type = next((t for t in json_type if t != "null"), "string")
        py_type = type_map.get(json_type, Any)
        default = ... if name in required else prop.get("default", None)
        desc = prop.get("description") or ""
        if default is ...:
            fields[name] = (py_type, Field(description=desc))
        else:
            fields[name] = (Optional[py_type], Field(default=default, description=desc))

    if not fields:
        fields["query"] = (str, Field(description="Primary query / input"))

    model_name = "".join(p.capitalize() for p in tool_name.split("_")) + "Args"
    return create_model(model_name, **fields)


def mcp_tools_as_langchain(
    server: MCPServer,
    *,
    server_name: str,
    on_call=None,
) -> List[StructuredTool]:
    """
    Discover tools on an MCPServer and wrap each as a sync LangChain tool.
    """

    async def _list():
        return await server.list_tools()

    mcp_tools = _run_async(_list())
    out: List[StructuredTool] = []

    for meta in mcp_tools:
        name = meta.name
        description = meta.description or f"MCP tool {name} ({server_name})"
        schema = getattr(meta, "inputSchema", None) or getattr(meta, "input_schema", None)
        if schema is None and hasattr(meta, "model_dump"):
            dumped = meta.model_dump()
            schema = dumped.get("inputSchema") or dumped.get("input_schema")

        args_model = _schema_to_args_model(name, schema)

        def _make_invoke(tool_name: str):
            def _invoke(**kwargs):
                async def _call():
                    return await server.call_tool(tool_name, kwargs)

                if on_call:
                    on_call(server_name, tool_name, kwargs)
                raw = _run_async(_call())
                return _unwrap_tool_result(raw)

            return _invoke

        out.append(
            StructuredTool.from_function(
                func=_make_invoke(name),
                name=name,
                description=description,
                args_schema=args_model,
            )
        )

    logger.info(
        "mcp adapter: server=%s tools=%s",
        server_name,
        [t.name for t in out],
    )
    return out
