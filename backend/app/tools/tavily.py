from langchain_core.tools import tool
from typing import Dict, Any

@tool
def tavily_search(query: str) -> Dict[str, Any]:
    """
    Search the web using Tavily.
    Use this tool to find up-to-date information on the internet.
    """
    # Note: In a real implementation, you would use TavilySearchResults from langchain_community
    # or make an API call to Tavily.
    return {
        "query": query,
        "results": [
            {"title": "Sample Tavily Result", "content": "This is a mock result for " + query}
        ]
    }
