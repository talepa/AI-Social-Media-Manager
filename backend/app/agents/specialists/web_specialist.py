"""
agents/specialists/web_specialist.py

Web Intelligence Agent — uses Brave Search and Google News to gather
web-based evidence for a sub-question.
"""

from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.brave import brave_search
from app.tools.news import news_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are a Web Intelligence Specialist for a technical research system.

Your job is to gather web-based evidence that answers a specific sub-question.
You have two tools:
- brave_search: search the web for articles, documentation, blog posts, product pages
- news_search: search recent news articles via Google News RSS

Strategy:
1. Start with a targeted brave_search using the most relevant query terms
2. If the question involves recent developments, also use news_search
3. Refine your search if initial results are too broad or miss the point
4. Do NOT repeat the same search query — vary your terms

Focus on finding:
- Primary sources (official docs, original announcements, specifications)
- Technical analysis (benchmarks, comparisons, case studies)
- Recent developments when recency matters

You are gathering evidence, not answering the question yourself. Let the sources speak."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 4) -> SpecialistResult:
    return run_specialist(
        sub_question=sub_question,
        specialist_name="web",
        tools=[brave_search, news_search],
        system_prompt=_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
    )
