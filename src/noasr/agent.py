"""Agent types and agent manager for noasr.

Implements the ReAct (Reason-Act) loop pattern for tool-calling agents.
"""

import json
import sys
from typing import Any, Callable

from noasr.models import AgentConfig
from noasr.tools import ToolManager


class AgentType:
    """Represents a single agent configuration with trigger key and toolset bindings."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._name = config.name
        self._trigger = config.trigger
        self._toolsets = config.toolsets

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    @property
    def trigger(self) -> list[int]:
        """Trigger key codes [down, up]."""
        return self._trigger

    @property
    def toolsets(self) -> list[str]:
        """Toolset names this agent can use."""
        return self._toolsets

    def get_tools(self) -> list[dict[str, Any]]:
        """Get merged, deduplicated tool definitions for this agent."""
        manager = ToolManager.get_instance()
        return manager.get_tool_sets(self._toolsets)

    def has_tools(self) -> bool:
        """Check if this agent has any tools configured."""
        return len(self.get_tools()) > 0


class AgentManager:
    """Manages all agent types and provides the ReAct loop."""

    def __init__(self) -> None:
        self._agent_dict: dict[str, AgentType] = {}

    def register(self, agent: AgentType) -> None:
        """Register an agent type."""
        self._agent_dict[agent.name] = agent

    def get_agent(self, name: str) -> AgentType | None:
        """Get an agent by name, returns None if not found."""
        return self._agent_dict.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agent_dict.keys())

    def get_agent_for_trigger(self, key_code: int) -> AgentType | None:
        """Find an agent whose trigger matches the given key code.

        For single-key hold-to-record, the trigger is [key_code, key_code].
        """
        for agent in self._agent_dict.values():
            if len(agent.trigger) >= 1 and agent.trigger[0] == key_code:
                return agent
        return None

    def run_agent(
        self,
        name: str,
        initial_messages: list[dict[str, Any]],
        client: Any,
    ) -> str:
        """Run an agent with the ReAct loop.

        Sends initial messages, then loops:
        - If response has tool_calls, execute each tool and append results
        - If response has no tool_calls, return final content

        Args:
            name: Agent name to run.
            initial_messages: Initial message list for the conversation.
            client: MiMoClient instance with a send() method.

        Returns:
            Final assistant text content string.
        """
        agent = self._agent_dict.get(name)
        if agent is None:
            return f"Error: Agent '{name}' not found"

        messages = list(initial_messages)
        tools = agent.get_tools() if agent.has_tools() else None

        # Log the initial request
        request_dict = {
            "model": "xiaomi/mimo-v2-omni",
            "messages": messages,
            "max_completion_tokens": 1024,
        }
        if tools:
            request_dict["tools"] = tools
            request_dict["tool_choice"] = "auto"

        print(json.dumps(request_dict, ensure_ascii=False, indent=2), file=sys.stderr)

        # Send initial request
        response = client.send(messages=messages, tools=tools)

        # ReAct loop
        max_iterations = 20  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Parse response
            choices = response.get("choices", [])
            if not choices:
                return ""

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls") or []

            # Log response
            print(json.dumps(response, ensure_ascii=False, indent=2), file=sys.stderr)

            # If no tool calls, we're done
            if not tool_calls:
                content = message.get("content", "")
                return content if content else ""

            # Process tool calls
            # Append the assistant message with tool_calls
            messages.append(message)

            # Execute each tool and append results
            tool_manager = ToolManager.get_instance()
            for tool_call in tool_calls:
                tool_id = tool_call.get("id", "")
                function = tool_call.get("function", {})
                tool_name = function.get("name", "")
                try:
                    arguments_str = function.get("arguments", "{}")
                    if isinstance(arguments_str, str):
                        arguments = json.loads(arguments_str)
                    else:
                        arguments = arguments_str
                except json.JSONDecodeError:
                    arguments = {}

                # Execute tool
                result = tool_manager.execute_tool(tool_name, arguments)

                # Append tool result message
                tool_result_msg = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result,
                }
                messages.append(tool_result_msg)

            # Send next request with updated messages
            response = client.send(messages=messages, tools=tools)

        # Safety: if we exceeded max iterations
        return ""


# Decorator for registering agent types
def agenttype(config: AgentConfig) -> Callable[[type], type]:
    """Decorator to register an AgentType.

    Usage:
        @agenttype(AgentConfig(name="dictate", trigger=[62, 62], toolsets=["default"]))
        class DictateAgent:
            pass
    """

    def decorator(cls: type) -> type:
        # This would be used by the runtime to auto-register agents
        # For now, the AgentManager.register() is the primary way
        return cls

    return decorator
