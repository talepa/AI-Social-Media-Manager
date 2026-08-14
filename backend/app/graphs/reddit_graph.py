"""
graphs/reddit_graph.py

Feature 1 LangGraph: user topic -> Reddit search -> results.

Flow: START -> reddit_research -> END
"""

from datetime import datetime, timezone
from typing import List, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.research import RedditPost, RedditResearchResult
from app.services.reddit_client import search_reddit


class RedditResearchState(TypedDict):
    topic: str
    limit: NotRequired[int]
    reddit_posts: NotRequired[List[RedditPost]]
    error: NotRequired[str]


def reddit_research_node(state: RedditResearchState) -> dict:
    topic = (state.get("topic") or "").strip()
    limit = int(state.get("limit") or 10)
    try:
        posts = search_reddit(topic=topic, limit=limit)
        return {"reddit_posts": posts, "error": None}
    except Exception as exc:
        return {"reddit_posts": [], "error": str(exc)}


def build_reddit_graph():
    workflow = StateGraph(RedditResearchState)
    workflow.add_node("reddit_research", reddit_research_node)
    workflow.add_edge(START, "reddit_research")
    workflow.add_edge("reddit_research", END)
    return workflow.compile()


reddit_graph = build_reddit_graph()


def run_reddit_research(topic: str, limit: int = 10) -> RedditResearchResult:
    """Invoke the Reddit graph and return a typed API result."""
    final = reddit_graph.invoke({"topic": topic, "limit": limit})
    posts = final.get("reddit_posts") or []
    # LangGraph may serialize Pydantic models to dicts
    normalized: List[RedditPost] = []
    for post in posts:
        if isinstance(post, RedditPost):
            normalized.append(post)
        else:
            normalized.append(RedditPost.model_validate(post))

    return RedditResearchResult(
        topic=topic,
        posts=normalized,
        fetched_at=datetime.now(timezone.utc),
        error=final.get("error"),
    )
