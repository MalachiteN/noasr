"""Tests for agent types and agent manager."""

import json
from unittest import mock

import pytest

from noasr.agent import AgentManager, AgentType
from noasr.models import AgentConfig
from noasr.tools import ITool, ToolManager


class TestAgentType:
    """Test AgentType class."""

    def test_agent_type_properties(self) -> None:
        """Test that AgentType exposes correct properties."""
        config = AgentConfig(name="dictate", trigger=[62, 62], toolsets=["default"])
        agent = AgentType(config)

        assert agent.name == "dictate"
        assert agent.trigger == [62, 62]
        assert agent.toolsets == ["default"]

    def test_agent_type_get_tools(self) -> None:
        """Test that get_tools merges toolsets from ToolManager."""
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()

        class TestTool(ITool):
            @property
            def name(self) -> str:
                return "TestTool"

            @property
            def function(self) -> dict:
                return {"type": "function", "function": {"name": "TestTool"}}

            def xeq(self, arguments: dict) -> str:
                return "test"

        manager.register_tool(TestTool())
        manager.register_toolset("default", ["TestTool"])

        config = AgentConfig(name="agent1", trigger=[62, 62], toolsets=["default"])
        agent = AgentType(config)

        tools = agent.get_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "TestTool"

    def test_agent_type_has_tools_true(self) -> None:
        """Test has_tools returns True when tools are configured."""
        ToolManager._instance = None
        ToolManager._initialized = False

        manager = ToolManager()
        manager.register_toolset("default", ["NonExistentTool"])

        config = AgentConfig(name="agent1", trigger=[62, 62], toolsets=["default"])
        agent = AgentType(config)

        # No actual tools registered, so has_tools should be False
        assert agent.has_tools() is False

    def test_agent_type_empty_toolsets(self) -> None:
        """Test agent with empty toolsets."""
        config = AgentConfig(name="bare", trigger=[62, 62], toolsets=[])
        agent = AgentType(config)

        assert agent.has_tools() is False
        assert agent.get_tools() == []


class TestAgentManager:
    """Test AgentManager class."""

    def test_register_and_get_agent(self) -> None:
        """Test registering and retrieving an agent."""
        mgr = AgentManager()
        config = AgentConfig(name="dictate", trigger=[62, 62], toolsets=["default"])
        agent = AgentType(config)

        mgr.register(agent)

        assert mgr.get_agent("dictate") is agent
        assert mgr.get_agent("nonexistent") is None

    def test_list_agents(self) -> None:
        """Test listing all registered agents."""
        mgr = AgentManager()

        mgr.register(
            AgentType(AgentConfig(name="agent1", trigger=[62, 62], toolsets=[]))
        )
        mgr.register(
            AgentType(AgentConfig(name="agent2", trigger=[63, 63], toolsets=[]))
        )

        names = mgr.list_agents()
        assert "agent1" in names
        assert "agent2" in names

    def test_get_agent_for_trigger(self) -> None:
        """Test finding agent by trigger key code."""
        mgr = AgentManager()
        mgr.register(
            AgentType(AgentConfig(name="dictate", trigger=[62, 62], toolsets=[]))
        )
        mgr.register(
            AgentType(AgentConfig(name="agent2", trigger=[63, 63], toolsets=[]))
        )

        found = mgr.get_agent_for_trigger(62)
        assert found is not None
        assert found.name == "dictate"

        found2 = mgr.get_agent_for_trigger(63)
        assert found2 is not None
        assert found2.name == "agent2"

        not_found = mgr.get_agent_for_trigger(99)
        assert not_found is None


class TestRunAgent:
    """Test the ReAct loop in run_agent."""

    AUDIO_DATA_URI = "data:audio/wav;base64,AAAA"

    def _make_manager(self) -> AgentManager:
        """Create an AgentManager with a registered agent."""
        ToolManager._instance = None
        ToolManager._initialized = False

        tool_manager = ToolManager()

        class DummyTool(ITool):
            @property
            def name(self) -> str:
                return "DummyTool"

            @property
            def function(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "DummyTool",
                        "description": "A dummy tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }

            def xeq(self, arguments: dict) -> str:
                return "tool_result_ok"

        tool_manager.register_tool(DummyTool())
        tool_manager.register_toolset("default", ["DummyTool"])

        mgr = AgentManager()
        config = AgentConfig(name="test_agent", trigger=[62, 62], toolsets=["default"])
        mgr.register(AgentType(config))
        return mgr

    def test_run_agent_no_tool_calls(self) -> None:
        """Test run_agent with a response that has no tool calls."""
        mgr = self._make_manager()

        mock_client = mock.MagicMock()
        mock_client.send.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello world",
                        "tool_calls": None,
                    }
                }
            ]
        }

        with mock.patch(
            "noasr.agent.load_agent_prompts", return_value=("sys prompt", "user prompt")
        ):
            result = mgr.run_agent("test_agent", self.AUDIO_DATA_URI, mock_client)

        assert result == "Hello world"

    def test_run_agent_with_tool_call(self) -> None:
        """Test run_agent with one round of tool calls then final response."""
        mgr = self._make_manager()

        mock_client = mock.MagicMock()

        # First response: has tool_calls
        # Second response: final content
        mock_client.send.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "DummyTool",
                                        "arguments": "{}",
                                    },
                                    "type": "function",
                                }
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Final answer after tool call",
                            "tool_calls": None,
                        }
                    }
                ]
            },
        ]

        with mock.patch(
            "noasr.agent.load_agent_prompts", return_value=("sys prompt", "user prompt")
        ):
            result = mgr.run_agent("test_agent", self.AUDIO_DATA_URI, mock_client)

        assert result == "Final answer after tool call"
        assert mock_client.send.call_count == 2

    def test_run_agent_unknown_agent(self) -> None:
        """Test run_agent with non-existent agent name."""
        mgr = AgentManager()
        result = mgr.run_agent("nonexistent", self.AUDIO_DATA_URI, mock.MagicMock())

        assert result == ""

    def test_run_agent_empty_choices(self) -> None:
        """Test run_agent when response has empty choices."""
        mgr = self._make_manager()

        mock_client = mock.MagicMock()
        mock_client.send.return_value = {"choices": []}

        with mock.patch(
            "noasr.agent.load_agent_prompts", return_value=("sys prompt", "user prompt")
        ):
            result = mgr.run_agent("test_agent", self.AUDIO_DATA_URI, mock_client)

        assert result == ""

    def test_run_agent_multiple_tool_calls(self) -> None:
        """Test run_agent with multiple tool calls in one round."""
        mgr = self._make_manager()

        mock_client = mock.MagicMock()
        mock_client.send.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "DummyTool",
                                        "arguments": "{}",
                                    },
                                    "type": "function",
                                },
                                {
                                    "id": "call_2",
                                    "function": {
                                        "name": "DummyTool",
                                        "arguments": "{}",
                                    },
                                    "type": "function",
                                },
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Done with all tools",
                            "tool_calls": None,
                        }
                    }
                ]
            },
        ]

        with mock.patch(
            "noasr.agent.load_agent_prompts", return_value=("sys prompt", "user prompt")
        ):
            result = mgr.run_agent("test_agent", self.AUDIO_DATA_URI, mock_client)

        assert result == "Done with all tools"
