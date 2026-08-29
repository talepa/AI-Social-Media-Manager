"""
api/mcp.py — MCP capability discovery (read-only).
"""

from fastapi import APIRouter

from app.mcp.registry import list_mcp_capabilities, mcp_call_stats

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


@router.get("/capabilities")
async def mcp_capabilities():
    """List first-party MCP servers and their tools (scoped by specialist)."""
    return list_mcp_capabilities()


@router.get("/stats")
async def mcp_stats():
    """Observable MCP tool-call counts for this process."""
    return {"calls": mcp_call_stats()}
