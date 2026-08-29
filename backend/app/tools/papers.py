"""
tools/papers.py

LangChain tool wrapper around the academic papers client.
"""

from typing import List

from langchain_core.tools import tool

from app.services.papers_client import search_papers


@tool
def papers_search(topic: str, limit: int = 8) -> List[dict]:
    """Search academic papers across Semantic Scholar, OpenAlex, Crossref, and arXiv.
    Returns titles, URLs, abstracts, authors, venues, and citation counts."""
    results = search_papers(topic=topic, limit=limit)
    return [r.model_dump() for r in results]
