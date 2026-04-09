"""Tool abstractions and management for noasr."""

from abc import ABC, abstractmethod
from typing import Any, Callable


class ITool(ABC):
    """Abstract interface for tools callable by agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        pass

    @property
    @abstractmethod
    def function(self) -> dict[str, Any]:
        """OpenAI-compatible function definition for LLM."""
        pass

    @abstractmethod
    def xeq(self, arguments: dict[str, Any]) -> str:
        """Execute the tool with given arguments.

        Args:
            arguments: Dict of arguments from LLM function call.

        Returns:
            String result for LLM consumption.
        """
        pass


class ToolManager:
    """Singleton manager for tools."""

    _instance: "ToolManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "ToolManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if ToolManager._initialized:
            return

        self._tool_dict: dict[str, ITool] = {}
        self._tool_set_reg: dict[str, list[str]] = {}
        ToolManager._initialized = True

    @classmethod
    def get_instance(cls) -> "ToolManager":
        """Get the singleton instance."""
        return cls()

    def register_tool(self, tool: ITool) -> None:
        """Register a tool."""
        self._tool_dict[tool.name] = tool

    def register_toolset(self, name: str, tools: list[str]) -> None:
        """Register a toolset mapping."""
        self._tool_set_reg[name] = tools

    def get_tool_sets(self, toolset_names: list[str]) -> list[dict[str, Any]]:
        """Get deduplicated tool definitions from toolsets.

        Args:
            toolset_names: List of toolset names to merge.

        Returns:
            List of tool function definitions (dicts) for LLM.
        """
        seen_tools: set[str] = set()
        result: list[dict[str, Any]] = []

        for name in toolset_names:
            tool_names = self._tool_set_reg.get(name, [])
            for tool_name in tool_names:
                if tool_name not in seen_tools:
                    seen_tools.add(tool_name)
                    tool = self._tool_dict.get(tool_name)
                    if tool:
                        result.append(tool.function)

        return result

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name.

        Args:
            name: Tool name.
            arguments: Arguments dict from LLM.

        Returns:
            Tool execution result string.

        Raises:
            KeyError: If tool not found.
        """
        if name not in self._tool_dict:
            return f"Error: Tool '{name}' not found"
        return self._tool_dict[name].xeq(arguments)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tool_dict.keys())

    def list_toolsets(self) -> list[str]:
        """List all registered toolset names."""
        return list(self._tool_set_reg.keys())


def agenttool(cls: type[ITool]) -> type[ITool]:
    """Decorator to auto-register a tool class.

    Usage:
        @agenttool
        class MyTool(ITool):
            ...
    """
    tool = cls()
    ToolManager.get_instance().register_tool(tool)
    return cls


def agenttoolset(name: str, tools: list[str]) -> Callable[[Any], Any]:
    """Decorator to register a toolset.

    Usage:
        @agenttoolset("myset", ["Tool1", "Tool2"])
        def register_myset():
            pass
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        ToolManager.get_instance().register_toolset(name, tools)
        return func

    return decorator
