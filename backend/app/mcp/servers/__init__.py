"""
mcp/servers/__init__.py
"""

from app.mcp.servers.academic import academic_mcp
from app.mcp.servers.repository import repository_mcp
from app.mcp.servers.research import research_mcp

SERVERS = {
    "research": research_mcp,
    "academic": academic_mcp,
    "repository": repository_mcp,
}

__all__ = ["SERVERS", "research_mcp", "academic_mcp", "repository_mcp"]
