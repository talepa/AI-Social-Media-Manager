"""
agents/specialists/academic_specialist.py

Academic Intelligence Agent — Academic MCP tools (papers search + detail).
"""

from app.mcp.registry import get_langchain_tools_for_specialist, mcp_enabled
from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.papers import papers_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are an Academic Intelligence Specialist for a technical research system.

Your job is to gather academic and research evidence that answers a specific sub-question.
You have Academic MCP tools:
- search_papers: search across Semantic Scholar, OpenAlex, Crossref, and arXiv
- get_paper: fetch details for a known paper id (Semantic Scholar / DOI / arXiv)
- get_citations: papers that cite a given paper id
- get_related_papers: related recommendations for a paper id

Strategy:
1. Search with the most specific academic terms first via search_papers
2. If results are sparse, broaden your query or try alternative terminology
3. When you have a strong paper id, use get_paper / get_citations for depth
4. Prioritize papers with high citation counts and recent publication dates

Focus on finding:
- Peer-reviewed research papers
- Benchmarks and empirical results
- Methods and their validated outcomes
- Limitations and open problems noted by researchers

You are gathering evidence, not answering the question yourself."""

_LEGACY_PROMPT = """You are an Academic Intelligence Specialist for a technical research system.

Your job is to gather academic and research evidence that answers a specific sub-question.
You have one tool:
- papers_search: search across Semantic Scholar, OpenAlex, Crossref, and arXiv

Strategy:
1. Search with the most specific academic terms first
2. If results are sparse, broaden your query or try alternative terminology
3. Prioritize papers with high citation counts and recent publication dates

You are gathering evidence, not answering the question yourself."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 3) -> SpecialistResult:
    if mcp_enabled():
        tools = get_langchain_tools_for_specialist("academic")
        prompt = _SYSTEM_PROMPT
    else:
        tools = [papers_search]
        prompt = _LEGACY_PROMPT
    return run_specialist(
        sub_question=sub_question,
        specialist_name="academic",
        tools=tools,
        system_prompt=prompt,
        max_tool_calls=max_tool_calls,
    )
