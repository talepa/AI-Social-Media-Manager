"""
app/mcp — first-party MCP capability layer.

Three focused servers wrap existing provider clients:
  - research   (web / news / page fetch)
  - academic   (papers)
  - repository (GitHub)

Specialists consume LangChain tools adapted from these MCP servers
(in-process via MCPServer.call_tool). Providers stay replaceable behind
the MCP boundary.
"""

from app.mcp.registry import (
    MCP_SERVER_NAMES,
    get_langchain_tools_for_specialist,
    list_mcp_capabilities,
    mcp_call_stats,
)

__all__ = [
    "MCP_SERVER_NAMES",
    "get_langchain_tools_for_specialist",
    "list_mcp_capabilities",
    "mcp_call_stats",
]
