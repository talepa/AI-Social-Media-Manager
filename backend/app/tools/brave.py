"""
tools/brave.py

LangChain tool wrapper around the Brave Search client.
"""

from typing import List

from langchain_core.tools import tool

from app.services.brave_client import search_web


@tool
def brave_search(query: str, limit: int = 10) -> List[dict]:
    """Search the web with Brave Search for a query.
    Returns titles, URLs, and content snippets from web results."""
    results, _answer, _images = search_web(topic=query, limit=limit)
    return [r.model_dump() for r in results]
