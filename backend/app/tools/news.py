from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def fetch_news(topic: str) -> List[Dict[str, Any]]:
    """
    Fetch recent news articles regarding a specific topic.
    Useful for timely and relevant content creation.
    """
    # Mock implementation of a News API (like NewsAPI or GNews)
    return [
        {
            "headline": f"Breaking: Major updates in {topic}",
            "source": "TechCrunch",
            "summary": "Recent developments suggest a huge shift in the industry."
        }
    ]
