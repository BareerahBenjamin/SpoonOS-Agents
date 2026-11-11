"""Real Tavily search; mock responses require explicit demo mode."""

import os
from urllib.parse import urlsplit

import requests
from pydantic import Field

from tools.base import ResearchTool, ToolInput, failure_reason, metadata, request_json


class SearchInput(ToolInput):
    query: str = Field(min_length=1, max_length=2000)
    max_results: int = Field(default=5, ge=1, le=10, strict=True)
    topic: str = Field(default="general", pattern=r"^(general|news)$")


class TavilySearchTool(ResearchTool):
    name: str = "search"
    description: str = "Search the web and return source URLs, excerpts and data availability."
    parameters: dict = SearchInput.model_json_schema()
    input_model = SearchInput

    def _run(self, query: str, max_results: int = 5, topic: str = "general") -> dict:
        base = {"query": query, "answer": "", "results": []}
        if self.demo_mode:
            return {
                **base,
                **metadata("mock", "demo"),
                "results": [
                    {
                        "title": f"Demo evidence for {query}",
                        "url": "https://example.com/demo",
                        "content": "Explicit demonstration fixture; not market evidence.",
                        "published_at": None,
                    }
                ],
            }
        key = os.getenv("TAVILY_API_KEY", "")
        if not key or "your-" in key:
            return {
                **base,
                **metadata("unavailable", "tavily", error="TAVILY_API_KEY is not configured"),
            }
        try:
            data = request_json(
                "POST",
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": query,
                    "max_results": max_results,
                    "topic": topic,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            rows = data["results"]
            if not isinstance(rows, list):
                raise ValueError("Missing search results")
            results, seen = [], set()
            for row in rows:
                url = row.get("url", "")
                parsed = urlsplit(url)
                identity = url.rstrip("/").split("#", 1)[0]
                if parsed.scheme not in {"https", "http"} or not parsed.netloc or identity in seen:
                    continue
                if not row.get("title") or not row.get("content"):
                    continue
                seen.add(identity)
                results.append(
                    {
                        "title": row["title"],
                        "url": url,
                        "content": row["content"],
                        "published_at": row.get("published_date"),
                        "source": parsed.netloc,
                    }
                )
                if len(results) == max_results:
                    break
            if not results:
                return {
                    **base,
                    **metadata("unavailable", "tavily", error="No usable source evidence returned"),
                }
            return {**base, **metadata("live", "tavily"), "results": results}
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
            return {**base, **metadata("unavailable", "tavily", error=failure_reason(exc))}
