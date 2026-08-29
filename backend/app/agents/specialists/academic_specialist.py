"""
agents/specialists/academic_specialist.py

Academic Intelligence Agent — uses Semantic Scholar, OpenAlex, Crossref,
and arXiv (via papers_search) to gather research evidence.
"""

from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.papers import papers_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are an Academic Intelligence Specialist for a technical research system.

Your job is to gather academic and research evidence that answers a specific sub-question.
You have one tool:
- papers_search: search across Semantic Scholar, OpenAlex, Crossref, and arXiv

Strategy:
1. Search with the most specific academic terms first
2. If results are sparse, broaden your query or try alternative terminology
3. Prioritize papers with high citation counts and recent publication dates
4. Look for survey/review papers when the question is broad

Focus on finding:
- Peer-reviewed research papers
- Benchmarks and empirical results
- Methods and their validated outcomes
- Limitations and open problems noted by researchers

You are gathering evidence, not answering the question yourself. Pay attention to
citation counts, publication venues, and author credibility as signals of quality."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 3) -> SpecialistResult:
    return run_specialist(
        sub_question=sub_question,
        specialist_name="academic",
        tools=[papers_search],
        system_prompt=_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
    )
