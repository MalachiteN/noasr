"""Agent types and agent manager for noasr.

Implements the ReAct (Reason-Act) loop pattern for tool-calling agents.
All LLM interaction goes through AgentManager — there is no direct client call.
"""

import json
import sys
from typing import Any, Callable

from noasr.config import load_agent_prompts
from noasr.models import AgentConfig, AudioPayload
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
    def trigger(self) -> int:
        """Trigger key code."""
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
        """Find an agent whose trigger matches the given key code."""
        for agent in self._agent_dict.values():
            if agent.trigger == key_code:
                return agent
        return None

    def run_agent(
        self,
        name: str,
        audio_data_uri: str,
        client: Any,
    ) -> str:
        """Run an agent with the ReAct loop.

        Builds the initial messages from agent config (prompt files + audio),
        then loops: if response has tool_calls, execute each and append results;
        if no tool_calls, return final content.

        Args:
            name: Agent name to run.
            audio_data_uri: Base64 data URI of the recorded audio.
            client: MiMoClient instance with a send() method.

        Returns:
            Final assistant text content string.
        """
        agent = self._agent_dict.get(name)
        if agent is None:
            print(f"Error: Agent '{name}' not found", file=sys.stderr)
            return ""

        # Build messages from agent config
        system_prompt, user_prompt = load_agent_prompts(
            system_prompt_file=agent._config.system_prompt_file,
            user_prompt_file=agent._config.user_prompt_file,
        )

        messages: list[dict[str, Any]] = []

        # System message
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # User message with audio + text
        audio_payload = AudioPayload(data_uri=audio_data_uri)
        user_content: list[dict[str, Any]] = [audio_payload.to_api_item()]
        if user_prompt:
            user_content.append({"type": "text", "text": user_prompt})
        messages.append({"role": "user", "content": user_content})

        # Get tools for this agent
        tools = agent.get_tools() if agent.has_tools() else None

        # Send initial request (MiMoClient.send() handles logging)
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

            # If no tool calls, we're done
            if not tool_calls:
                content = message.get("content", "")
                # Content may be None, a string, or a structured list
                if content is None:
                    return ""
                if isinstance(content, list):
                    # Multimodal response: extract text items
                    parts = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    return "\n".join(parts)
                return str(content) if content else ""

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

                # Execute tool (isolate failures so one bad tool doesn't abort the loop)
                try:
                    result = tool_manager.execute_tool(tool_name, arguments)
                except Exception as e:
                    result = f"Error executing tool '{tool_name}': {e}"
                    print(f"Tool execution error: {e}", file=sys.stderr)

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
        @agenttype(AgentConfig(name="dictate", trigger=165, toolsets=["default"]))
        class DictateAgent:
            pass
    """

    def decorator(cls: type) -> type:
        # This would be used by the runtime to auto-register agents
        # For now, the AgentManager.register() is the primary way
        return cls

    return decorator
