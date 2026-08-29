"""
agents/specialists/web_specialist.py

Web Intelligence Agent — gathers web evidence via Research MCP tools
(or legacy LangChain wrappers when USE_MCP=false).
"""

from app.mcp.registry import get_langchain_tools_for_specialist, mcp_enabled
from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.news import news_search
from app.tools.tavily import tavily_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are a Web Intelligence Specialist for a technical research system.

Your job is to gather web-based evidence that answers a specific sub-question.
You have MCP research tools:
- search_web: search the web for articles, documentation, blog posts, product pages
- search_news: search recent news articles
- fetch_url / extract_content: read a specific page when a URL is already known
- get_page_metadata: lightweight title/description for a URL

Strategy:
1. Start with a targeted search_web using the most relevant query terms
2. If the question involves recent developments, also use search_news
3. Refine your search if initial results are too broad or miss the point
4. Do NOT repeat the same search query — vary your terms
5. Optionally fetch_url on the most promising source for deeper evidence

Focus on finding:
- Primary sources (official docs, original announcements, specifications)
- Technical analysis (benchmarks, comparisons, case studies)
- Recent developments when recency matters

You are gathering evidence, not answering the question yourself. Let the sources speak."""

_LEGACY_PROMPT = """You are a Web Intelligence Specialist for a technical research system.

Your job is to gather web-based evidence that answers a specific sub-question.
You have two tools:
- tavily_search: search the web for articles, documentation, blog posts, product pages
- news_search: search recent news articles via Google News RSS

Strategy:
1. Start with a targeted tavily_search using the most relevant query terms
2. If the question involves recent developments, also use news_search
3. Refine your search if initial results are too broad or miss the point
4. Do NOT repeat the same search query — vary your terms

You are gathering evidence, not answering the question yourself. Let the sources speak."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 4) -> SpecialistResult:
    if mcp_enabled():
        tools = get_langchain_tools_for_specialist("web")
        prompt = _SYSTEM_PROMPT
    else:
        tools = [tavily_search, news_search]
        prompt = _LEGACY_PROMPT
    return run_specialist(
        sub_question=sub_question,
        specialist_name="web",
        tools=tools,
        system_prompt=prompt,
        max_tool_calls=max_tool_calls,
    )
