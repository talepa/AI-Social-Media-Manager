"""
agents/specialists/repository_specialist.py

Repository Intelligence Agent — Repository MCP (GitHub search + health).
"""

from app.mcp.registry import get_langchain_tools_for_specialist, mcp_enabled
from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.github import github_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are a Repository Intelligence Specialist for a technical research system.

Your job is to gather implementation evidence from GitHub that answers a specific sub-question.
You have Repository MCP tools:
- search_repositories: find repos by topic (stars, activity, description)
- get_repository: detailed metadata for owner/name
- get_release_history: recent releases/tags
- get_activity: recent commits
- get_issue_summary: open-issue signal + recent titles

Strategy:
1. Search for the most relevant repositories first via search_repositories
2. For promising repos, call get_repository and optionally get_activity / get_release_history
3. If comparing technologies, search for each one separately
4. Prefer active maintenance and recent releases over stars alone

You are gathering evidence about real-world implementation, not answering the question yourself."""

_LEGACY_PROMPT = """You are a Repository Intelligence Specialist for a technical research system.

Your job is to gather implementation evidence from GitHub that answers a specific sub-question.
You have one tool:
- github_search: search GitHub repositories by topic (returns names, descriptions, stars, activity)

Strategy:
1. Search for the most relevant repositories first
2. If comparing technologies, search for each one separately
3. Look for both the primary project and related ecosystem tools

You are gathering evidence about real-world implementation, not answering the question yourself."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 3) -> SpecialistResult:
    if mcp_enabled():
        tools = get_langchain_tools_for_specialist("repository")
        prompt = _SYSTEM_PROMPT
    else:
        tools = [github_search]
        prompt = _LEGACY_PROMPT
    return run_specialist(
        sub_question=sub_question,
        specialist_name="repository",
        tools=tools,
        system_prompt=prompt,
        max_tool_calls=max_tool_calls,
    )
