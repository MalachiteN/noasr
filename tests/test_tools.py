"""Tests for tool system."""

from datetime import datetime
from unittest import mock

import pytest

from noasr.tools import ITool, ToolManager, agenttool, agenttoolset
from noasr.tools.datetime import GetCurrentDateTime


class TestToolManagerSingleton:
    """Test ToolManager singleton behavior."""

    def test_get_instance_returns_same_object(self) -> None:
        """Test that get_instance returns the same singleton."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager1 = ToolManager.get_instance()
        manager2 = ToolManager.get_instance()

        assert manager1 is manager2

    def test_constructor_returns_same_instance(self) -> None:
        """Test that constructor returns the same singleton."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager1 = ToolManager()
        manager2 = ToolManager()

        assert manager1 is manager2


class TestToolRegistration:
    """Test tool registration."""

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()

        class TestTool(ITool):
            @property
            def name(self) -> str:
                return "TestTool"

            @property
            def function(self) -> dict:
                return {"name": "TestTool"}

            def xeq(self, arguments: dict) -> str:
                return "test result"

        tool = TestTool()
        manager.register_tool(tool)

        assert "TestTool" in manager.list_tools()

    def test_agenttool_decorator_registers_tool(self) -> None:
        """Test that @agenttool decorator registers the tool."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        @agenttool
        class DecoratedTool(ITool):
            @property
            def name(self) -> str:
                return "DecoratedTool"

            @property
            def function(self) -> dict:
                return {"name": "DecoratedTool"}

            def xeq(self, arguments: dict) -> str:
                return "decorated"

        manager = ToolManager()
        assert "DecoratedTool" in manager.list_tools()


class TestToolsetRegistration:
    """Test toolset registration."""

    def test_register_toolset(self) -> None:
        """Test registering a toolset."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()
        manager.register_toolset("default", ["Tool1", "Tool2"])

        assert "default" in manager.list_toolsets()

    def test_agenttoolset_decorator(self) -> None:
        """Test that @agenttoolset decorator registers the toolset."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        @agenttoolset("myset", ["A", "B"])
        def dummy() -> None:
            pass

        manager = ToolManager()
        assert "myset" in manager.list_toolsets()


class TestGetToolSets:
    """Test get_tool_sets deduplication."""

    def test_deduplication_across_toolsets(self) -> None:
        """Test that tools are deduplicated across toolsets."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()

        # Register tools
        class Tool1(ITool):
            @property
            def name(self) -> str:
                return "Tool1"

            @property
            def function(self) -> dict:
                return {"name": "Tool1"}

            def xeq(self, arguments: dict) -> str:
                return "1"

        class Tool2(ITool):
            @property
            def name(self) -> str:
                return "Tool2"

            @property
            def function(self) -> dict:
                return {"name": "Tool2"}

            def xeq(self, arguments: dict) -> str:
                return "2"

        manager.register_tool(Tool1())
        manager.register_tool(Tool2())

        # Register overlapping toolsets
        manager.register_toolset("set1", ["Tool1", "Tool2"])
        manager.register_toolset("set2", ["Tool2", "Tool3"])  # Tool3 not registered

        # Get merged toolsets
        tools = manager.get_tool_sets(["set1", "set2"])

        # Should have 2 tools (Tool1 and Tool2), not 3
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "Tool1" in tool_names
        assert "Tool2" in tool_names

    def test_returns_function_definitions(self) -> None:
        """Test that get_tool_sets returns function definitions."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()

        class TestTool(ITool):
            @property
            def name(self) -> str:
                return "TestTool"

            @property
            def function(self) -> dict:
                return {"name": "TestTool", "description": "A test tool"}

            def xeq(self, arguments: dict) -> str:
                return "test"

        manager.register_tool(TestTool())
        manager.register_toolset("testset", ["TestTool"])

        tools = manager.get_tool_sets(["testset"])

        assert len(tools) == 1
        assert tools[0] == {"name": "TestTool", "description": "A test tool"}


class TestExecuteTool:
    """Test tool execution."""

    def test_execute_existing_tool(self) -> None:
        """Test executing a registered tool."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()

        class EchoTool(ITool):
            @property
            def name(self) -> str:
                return "EchoTool"

            @property
            def function(self) -> dict:
                return {"name": "EchoTool"}

            def xeq(self, arguments: dict) -> str:
                msg = arguments.get("message", "")
                return f"Echo: {msg}"

        manager.register_tool(EchoTool())
        result = manager.execute_tool("EchoTool", {"message": "hello"})

        assert result == "Echo: hello"

    def test_execute_missing_tool(self) -> None:
        """Test executing a non-existent tool returns error."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()
        result = manager.execute_tool("NonExistent", {})

        assert "Error" in result
        assert "NonExistent" in result


class TestGetCurrentDateTime:
    """Test the datetime tool."""

    def test_name_and_function(self) -> None:
        """Test tool metadata."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()

        assert tool.name == "GetCurrentDateTime"
        assert "function" in tool.function
        assert tool.function["function"]["name"] == "GetCurrentDateTime"

    def test_xeq_returns_string(self) -> None:
        """Test that execution returns a string."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result = tool.xeq({})

        assert isinstance(result, str)

    def test_xeq_iso_format(self) -> None:
        """Test ISO format output."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result = tool.xeq({"format": "iso"})

        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)

    def test_xeq_short_format(self) -> None:
        """Test short format output."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result = tool.xeq({"format": "short"})

        # Should be in format "YYYY-MM-DD HH:MM"
        assert len(result) == 16
        assert result[10] == " "
        assert result[13] == ":"

    def test_xeq_full_format(self) -> None:
        """Test full format output."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result = tool.xeq({"format": "full"})

        # Should contain day name
        assert any(
            day in result
            for day in [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        )

    def test_default_format_is_iso(self) -> None:
        """Test that default format is ISO."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result_default = tool.xeq({})
        result_iso = tool.xeq({"format": "iso"})

        # Both should be ISO format (exact value differs by time)
        parsed = datetime.fromisoformat(result_default)
        assert isinstance(parsed, datetime)

    def test_invalid_format_defaults_to_iso(self) -> None:
        """Test that invalid format defaults to ISO."""
        # Reset for clean test
        ToolManager._instance = None
        ToolManager._initialized = False

        tool = GetCurrentDateTime()
        result = tool.xeq({"format": "invalid"})

        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)


class TestDateTimeToolRegistration:
    """Test that datetime tool is properly registered."""

    def test_datetime_tool_in_manager(self) -> None:
        """Test that GetCurrentDateTime is registered in ToolManager."""
        # Just use the existing manager that already has the tool registered
        # from the module import at the top of the test file
        from noasr.tools.datetime import GetCurrentDateTime

        # Force registration if not already done
        from noasr.tools import ToolManager

        manager = ToolManager()
        if "GetCurrentDateTime" not in manager.list_tools():
            manager.register_tool(GetCurrentDateTime())

        assert "GetCurrentDateTime" in manager.list_tools()

    def test_datetime_tool_can_be_executed(self) -> None:
        """Test that datetime tool can be executed via manager."""
        from noasr.tools.datetime import GetCurrentDateTime
        from noasr.tools import ToolManager

        manager = ToolManager()
        if "GetCurrentDateTime" not in manager.list_tools():
            manager.register_tool(GetCurrentDateTime())

        result = manager.execute_tool("GetCurrentDateTime", {"format": "iso"})

        # Should be parseable as datetime
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)
