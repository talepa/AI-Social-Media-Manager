"""
tools/tavily.py

LangChain tool wrapper around the Tavily client (for later agent tool-calling).
"""

from typing import List

from langchain_core.tools import tool

from app.services.tavily_client import search_web


@tool
def tavily_search(topic: str, limit: int = 10) -> List[dict]:
    """
    Search the web with Tavily for a topic.
    Returns titles, URLs, content snippets, and relevance scores.
    """
    results, _answer = search_web(topic=topic, limit=limit)
    return [r.model_dump() for r in results]
