"""
agents/specialists/repository_specialist.py

Repository Intelligence Agent — uses GitHub Search to assess implementation
maturity, community health, and project activity.
"""

from app.schemas.investigation import SpecialistResult, SubQuestion
from app.tools.github import github_search

from .base import run_specialist

_SYSTEM_PROMPT = """You are a Repository Intelligence Specialist for a technical research system.

Your job is to gather implementation evidence from GitHub that answers a specific sub-question.
You have one tool:
- github_search: search GitHub repositories by topic (returns names, descriptions, stars, activity)

Strategy:
1. Search for the most relevant repositories first
2. If the question is about a specific technology, search for that technology name
3. If comparing technologies, search for each one separately
4. Look for both the primary project and related ecosystem tools

Focus on finding:
- Star counts and community size as adoption signals
- Recent activity and maintenance status
- Description and purpose alignment with the question
- Implementation maturity indicators

You are gathering evidence about real-world implementation, not answering the question
yourself. High star counts alone don't mean quality — look for active maintenance
and recent releases as stronger signals."""


def run(sub_question: SubQuestion, *, max_tool_calls: int = 3) -> SpecialistResult:
    return run_specialist(
        sub_question=sub_question,
        specialist_name="repository",
        tools=[github_search],
        system_prompt=_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
    )
