"""
Search tools using Tavily API
"""

import os
import requests
from typing import Dict, Any, List
from loguru import logger


class TavilySearchTool:
    """Tool to search the web using Tavily API"""

    name = "search"
    description = "Search the web for information. Input should be a search query string."

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com/search"

    def run(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search the web

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            Dictionary with search results
        """
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set, returning mock results")
            return self._mock_search(query, max_results)

        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": True,
            }

            response = requests.post(self.base_url, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()

            results = {
                "query": query,
                "answer": data.get("answer", ""),
                "results": [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0),
                    }
                    for result in data.get("results", [])
                ],
            }

            logger.info(f"Tavily search completed for: {query}")
            return results

        except Exception as e:
            logger.error(f"Error in Tavily search: {e}")
            return self._mock_search(query, max_results)

    def _mock_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """Return mock search results for demo"""
        return {
            "query": query,
            "answer": f"This is a simulated answer for: {query}. The Tavily API key is not configured.",
            "results": [
                {
                    "title": f"Result {i + 1} for {query}",
                    "url": f"https://example.com/result-{i + 1}",
                    "content": f"This is mock content for result {i + 1} about {query}.",
                    "score": 0.9 - (i * 0.1),
                }
                for i in range(max_results)
            ],
        }


if __name__ == "__main__":
    # Test tool
    tool = TavilySearchTool()
    result = tool.run("What is Bitcoin?")
    print(result)
