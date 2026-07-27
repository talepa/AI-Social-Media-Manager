from langchain_core.tools import tool
from typing import Dict, Any, List

@tool
def get_google_trends(topic: str) -> Dict[str, Any]:
    """
    Get trending data and related queries for a specific topic using Google Trends.
    Use this to see what people are currently searching for related to your niche.
    """
    # Mock implementation of pytrends or SerpApi Google Trends
    return {
        "topic": topic,
        "interest_over_time": "increasing",
        "related_queries": ["how to " + topic, "best " + topic + " 2026"]
    }
