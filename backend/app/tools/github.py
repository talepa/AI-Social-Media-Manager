"""
tools/github.py

LangChain tool wrapper around the GitHub repository search client.
"""

from typing import List

from langchain_core.tools import tool

from app.services.github_client import search_github_repos


@tool
def github_search(topic: str, limit: int = 8) -> List[dict]:
    """Search GitHub repositories by topic.
    Returns repository names, URLs, descriptions, star counts, and activity."""
    results = search_github_repos(topic=topic, limit=limit)
    return [r.model_dump() for r in results]
