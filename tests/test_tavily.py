"""Tests for TavilySearch tool."""

import json
from unittest import mock

import pytest

from noasr.tools.tavily import TavilySearch


class TestTavilySearchProperties:
    """Test TavilySearch properties."""

    def test_name(self) -> None:
        """Tool name is TavilySearch."""
        tool = TavilySearch(api_key="test-key")
        assert tool.name == "TavilySearch"

    def test_function_has_required_fields(self) -> None:
        """Function definition has type, function, name, description, parameters."""
        tool = TavilySearch(api_key="test-key")
        func = tool.function
        assert func["type"] == "function"
        assert "function" in func
        assert func["function"]["name"] == "TavilySearch"
        assert "description" in func["function"]
        assert "parameters" in func["function"]

    def test_function_query_is_required(self) -> None:
        """Query parameter is required."""
        tool = TavilySearch(api_key="test-key")
        params = tool.function["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]

    def test_function_optional_params(self) -> None:
        """Optional parameters search_depth and include_answer exist."""
        tool = TavilySearch(api_key="test-key")
        params = tool.function["function"]["parameters"]
        assert "search_depth" in params["properties"]
        assert "include_answer" in params["properties"]


class TestTavilySearchExecute:
    """Test TavilySearch.xeq()."""

    def test_missing_query_returns_error(self) -> None:
        """xeq returns error when query is missing."""
        tool = TavilySearch(api_key="test-key")
        result = tool.xeq({})
        assert "Error" in result
        assert "query" in result

    def test_empty_query_returns_error(self) -> None:
        """xeq returns error when query is empty string."""
        tool = TavilySearch(api_key="test-key")
        result = tool.xeq({"query": ""})
        assert "Error" in result

    def test_successful_search_returns_json(self) -> None:
        """xeq returns raw JSON string on successful search."""
        tool = TavilySearch(api_key="test-key")
        mock_response = {
            "query": "test query",
            "answer": "test answer",
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "content": "Test content",
                    "score": 0.9,
                }
            ],
        }
        with mock.patch("tavily.TavilyClient") as MockClient:
            instance = MockClient.return_value
            instance.search.return_value = mock_response
            result = tool.xeq({"query": "test query"})

        # Result should be valid JSON
        parsed = json.loads(result)
        assert parsed["query"] == "test query"
        assert parsed["answer"] == "test answer"
        assert len(parsed["results"]) == 1

    def test_search_with_custom_depth(self) -> None:
        """xeq passes search_depth to TavilyClient."""
        tool = TavilySearch(api_key="test-key")
        mock_response = {"query": "test", "results": []}
        with mock.patch("tavily.TavilyClient") as MockClient:
            instance = MockClient.return_value
            instance.search.return_value = mock_response
            tool.xeq({"query": "test", "search_depth": "advanced"})
            instance.search.assert_called_once_with(
                query="test",
                search_depth="advanced",
                include_answer="basic",
            )

    def test_search_with_include_answer(self) -> None:
        """xeq passes include_answer to TavilyClient."""
        tool = TavilySearch(api_key="test-key")
        mock_response = {"query": "test", "results": []}
        with mock.patch("tavily.TavilyClient") as MockClient:
            instance = MockClient.return_value
            instance.search.return_value = mock_response
            tool.xeq({"query": "test", "include_answer": "none"})
            instance.search.assert_called_once_with(
                query="test",
                search_depth="basic",
                include_answer="none",
            )

    def test_api_error_returns_error_string(self) -> None:
        """xeq returns error message string on Tavily API error."""
        tool = TavilySearch(api_key="test-key")
        with mock.patch("tavily.TavilyClient") as MockClient:
            instance = MockClient.return_value
            instance.search.side_effect = Exception(
                "InvalidAPIKeyError: Invalid API key"
            )
            result = tool.xeq({"query": "test"})

        assert "Error" in result
        assert "InvalidAPIKeyError" in result

    def test_import_error_returns_install_hint(self) -> None:
        """xeq returns install hint when tavily-python is not installed."""
        tool = TavilySearch(api_key="test-key")
        with mock.patch.dict("sys.modules", {"tavily": None}):
            result = tool.xeq({"query": "test"})
        assert "tavily-python" in result

    def test_tavily_specific_errors_passed_through(self) -> None:
        """Tavily-specific errors (UsageLimitExceeded, etc.) are passed to LLM."""
        tool = TavilySearch(api_key="test-key")

        # Simulate UsageLimitExceededError
        with mock.patch("tavily.TavilyClient") as MockClient:
            instance = MockClient.return_value
            instance.search.side_effect = Exception(
                "UsageLimitExceededError: Usage limit exceeded"
            )
            result = tool.xeq({"query": "test"})

        assert "UsageLimitExceededError" in result


class TestTavilySearchRegistration:
    """Test that TavilySearch integrates with ToolManager."""

    def test_register_and_execute(self) -> None:
        """TavilySearch can be registered with ToolManager and executed."""
        from noasr.tools import ToolManager

        # Reset singleton
        ToolManager._instance = None
        ToolManager._initialized = False

        mgr = ToolManager.get_instance()
        tool = TavilySearch(api_key="test-key")
        mgr.register_tool(tool)
        mgr.register_toolset("search", ["TavilySearch"])

        assert "TavilySearch" in mgr.list_tools()
        definitions = mgr.get_tool_sets(["search"])
        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "TavilySearch"

        # Cleanup
        ToolManager._instance = None
        ToolManager._initialized = False
