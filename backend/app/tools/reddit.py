"""
tools/reddit.py

LangChain tool wrapper around the real Reddit client.
Feature 1 uses the client directly from the graph node; this tool is ready
for later agent tool-calling.
"""

from typing import List

from langchain_core.tools import tool

from app.schemas.research import RedditPost
from app.services.reddit_client import search_reddit as _search_reddit


@tool
def search_reddit(topic: str, limit: int = 10) -> List[dict]:
    """
    Search Reddit for posts related to a topic.
    Returns titles, scores, comment counts, subreddits, and permalinks.
    """
    posts: List[RedditPost] = _search_reddit(topic=topic, limit=limit)
    return [p.model_dump() for p in posts]
