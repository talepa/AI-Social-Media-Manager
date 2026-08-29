"""
tools/news.py

LangChain tool wrapper around the Google News RSS client.
"""

from typing import List

from langchain_core.tools import tool

from app.services.news_client import search_news


@tool
def news_search(topic: str, limit: int = 8) -> List[dict]:
    """Search recent news articles via Google News RSS.
    Returns headlines, URLs, descriptions, and publication dates."""
    results = search_news(topic=topic, limit=limit)
    return [r.model_dump() for r in results]
