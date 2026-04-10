"""Tavily search tool for noasr."""

import json
import sys
from typing import Any

from noasr.tools import ITool


class TavilySearch(ITool):
    """Tool to search the web using Tavily API.

    Returns raw JSON response string for LLM consumption.
    On error, returns the error message string so the LLM can react accordingly.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "TavilySearch"

    @property
    def function(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search the web for real-time information. "
                    "Returns search results with URLs, titles, and content snippets. "
                    "Use this when you need current information that may not be in your training data."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string",
                        },
                        "search_depth": {
                            "type": "string",
                            "description": "Search depth: 'basic' for quick results, 'advanced' for more thorough search",
                            "enum": ["basic", "advanced"],
                        },
                        "include_answer": {
                            "type": "string",
                            "description": "Whether to include a short answer in the response",
                            "enum": ["none", "basic"],
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def xeq(self, arguments: dict[str, Any]) -> str:
        """Execute the Tavily search.

        Args:
            arguments: Must contain 'query'. Optional: 'search_depth', 'include_answer'.

        Returns:
            Raw JSON response string on success, error message string on failure.
        """
        query = arguments.get("query", "")
        if not query:
            return "Error: 'query' is required for TavilySearch"

        search_depth = arguments.get("search_depth", "basic")
        include_answer = arguments.get("include_answer", "basic")

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self._api_key)
            response = client.search(
                query=query,
                search_depth=search_depth,
                include_answer=include_answer,
            )
            return json.dumps(response, ensure_ascii=False)

        except ImportError:
            return (
                "Error: tavily-python is not installed. "
                "Install with: pip install tavily-python"
            )
        except Exception as e:
            # Pass the error directly to the LLM so it can reason about it
            error_type = type(e).__name__
            print(
                f"[TavilySearch ERROR] {error_type}: {e}",
                file=sys.stderr,
                flush=True,
            )
            return f"Error: TavilySearch failed: {error_type}: {e}"
