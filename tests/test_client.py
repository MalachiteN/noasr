"""Tests for MiMo client wrapper."""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai.types.chat import ChatCompletion

from noasr.client import MiMoClient, OpenAiTransport, create_client, MiMoTransport
from noasr.models import MiMoResponse


class MockTransport:
    """Mock transport for testing."""

    def __init__(self, response: ChatCompletion | None = None) -> None:
        self._response = response
        self._calls: list[dict[str, Any]] = []

    def create_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatCompletion:
        """Record call and return mock response."""
        call = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "tools": tools,
            "tool_choice": tool_choice,
        }
        self._calls.append(call)

        if self._response is None:
            # Default mock response
            return ChatCompletion.model_validate(
                {
                    "id": "test-id",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "index": 0,
                            "message": {
                                "content": "Test response",
                                "role": "assistant",
                            },
                        }
                    ],
                    "created": 1234567890,
                    "model": model,
                    "object": "chat.completion",
                    "usage": {
                        "completion_tokens": 10,
                        "prompt_tokens": 50,
                        "total_tokens": 60,
                    },
                }
            )
        return self._response

    def get_calls(self) -> list[dict[str, Any]]:
        """Get recorded calls."""
        return self._calls

    def get_last_call(self) -> dict[str, Any] | None:
        """Get last recorded call."""
        return self._calls[-1] if self._calls else None


@pytest.fixture
def mock_transport() -> MockTransport:
    """Create a mock transport."""
    return MockTransport()


@pytest.fixture
def client(mock_transport: MockTransport) -> MiMoClient:
    """Create a MiMo client with mock transport."""
    return create_client(
        api_key="test-api-key",
        base_url="https://test.example.com",
        transport=mock_transport,
    )


class TestMessageBuilding:
    """Tests for message building functions."""

    def test_transcription_messages_structure(self, client: MiMoClient) -> None:
        """Test that transcription mode produces correct message structure."""
        messages = client.build_transcription_messages(
            system_prompt="You are a helpful assistant.",
            user_prompt="Transcribe this audio.",
            audio_data_uri="data:audio/wav;base64,test123",
        )

        # Should have exactly 2 messages
        assert len(messages) == 2

        # First message should be system
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

        # Second message should be user with multimodal content
        assert messages[1]["role"] == "user"
        assert isinstance(messages[1]["content"], list)
        assert len(messages[1]["content"]) == 2

        # First content item should be audio
        assert messages[1]["content"][0]["type"] == "input_audio"
        assert (
            messages[1]["content"][0]["input_audio"]["data"]
            == "data:audio/wav;base64,test123"
        )

        # Second content item should be text
        assert messages[1]["content"][1]["type"] == "text"
        assert messages[1]["content"][1]["text"] == "Transcribe this audio."

    def test_transcription_messages_empty_prompts(self, client: MiMoClient) -> None:
        """Test message building with empty prompts."""
        messages = client.build_transcription_messages(
            system_prompt="",
            user_prompt="",
            audio_data_uri="data:audio/wav;base64,test123",
        )

        # System prompt empty - should not include system message
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

        # User content should have audio but no text (text is empty)
        assert len(messages[0]["content"]) == 1  # Only audio

    def test_agent_messages_with_history(self, client: MiMoClient) -> None:
        """Test agent message building with conversation history."""
        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]

        messages = client.build_agent_messages(
            system_prompt="System prompt",
            user_prompt="User prompt",
            audio_data_uri="data:audio/wav;base64,test123",
            conversation_history=history,
        )

        # Should preserve history
        assert len(messages) == 2
        assert messages[0]["content"] == "Previous message"
        assert messages[1]["content"] == "Previous response"

    def test_agent_messages_without_history(self, client: MiMoClient) -> None:
        """Test agent message building without conversation history."""
        messages = client.build_agent_messages(
            system_prompt="System prompt",
            user_prompt="User prompt",
            audio_data_uri="data:audio/wav;base64,test123",
        )

        # Should create initial messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestTranscriptionMode:
    """Tests for plain transcription mode."""

    def test_transcription_sends_correct_payload(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that transcription sends correct two-message payload."""
        response = ChatCompletion.model_validate(
            {
                "id": "transcription-id",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {
                            "content": "Transcribed text here",
                            "role": "assistant",
                        },
                    }
                ],
                "created": 1234567890,
                "model": "xiaomi/mimo-v2-omni",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 10,
                    "prompt_tokens": 50,
                    "total_tokens": 60,
                },
            }
        )
        mock_transport._response = response

        result = client.transcribe(
            system_prompt="You are a transcriber.",
            user_prompt="Transcribe this.",
            audio_data_uri="data:audio/wav;base64,abc123",
        )

        # Check the call
        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "xiaomi/mimo-v2-omni"
        assert call["max_completion_tokens"] == 1024
        assert call["tools"] is None

        # Check messages
        messages = call["messages"]
        assert len(messages) == 2

        # System message
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a transcriber."

        # User message
        assert messages[1]["role"] == "user"
        assert isinstance(messages[1]["content"], list)

        # Response should be parsed correctly
        assert isinstance(result, MiMoResponse)
        assert result.get_content() == "Transcribed text here"

    def test_transcription_no_tools_in_request(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that transcription mode does not include tools."""
        client.transcribe(
            system_prompt="System",
            user_prompt="User",
            audio_data_uri="data:audio/wav;base64,test",
        )

        call = mock_transport.get_last_call()
        assert call is not None
        assert call.get("tools") is None
        assert call.get("tool_choice") is None


class TestAgentMode:
    """Tests for agent mode with tools."""

    def test_agent_mode_includes_tools(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that agent mode includes merged tools."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_datetime",
                    "description": "Get current date and time",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "agent-id",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "index": 0,
                        "message": {
                            "content": "",
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "get_datetime",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        },
                    }
                ],
                "created": 1234567890,
                "model": "xiaomi/mimo-v2-omni",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 20,
                    "prompt_tokens": 100,
                    "total_tokens": 120,
                },
            }
        )

        result = client.run_agent(
            system_prompt="You are an agent.",
            user_prompt="What time is it?",
            audio_data_uri="data:audio/wav;base64,test",
            tools=tools,
        )

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["tools"] == tools
        assert call["tool_choice"] == "auto"

        # Check response parsing for tool calls
        assert result.has_tool_calls()
        tool_calls = result.get_tool_calls()
        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "get_datetime"

    def test_agent_mode_with_tool_choice(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that agent mode respects tool_choice parameter."""
        tools = [{"type": "function", "function": {"name": "test_tool"}}]

        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "id",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {"content": "Done", "role": "assistant"},
                    }
                ],
                "created": 1234567890,
                "model": "xiaomi/mimo-v2-omni",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        client.run_agent(
            system_prompt="System",
            user_prompt="User",
            audio_data_uri="data:audio/wav;base64,test",
            tools=tools,
            tool_choice="required",
        )

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["tool_choice"] == "required"


class TestLogging:
    """Tests for request/response logging to stderr."""

    def test_request_logged_to_stderr(
        self, client: MiMoClient, mock_transport: MockTransport, capsys: Any
    ) -> None:
        """Test that request dict is logged to stderr."""
        client.transcribe(
            system_prompt="System",
            user_prompt="User",
            audio_data_uri="data:audio/wav;base64,test",
        )

        captured = capsys.readouterr()

        # Should have request logged to stderr
        assert "[MiMo REQUEST]" in captured.err

        # Extract JSON between REQUEST and RESPONSE markers
        request_start = captured.err.find("[MiMo REQUEST]")
        response_start = captured.err.find("[MiMo RESPONSE]")

        if response_start > request_start:
            # Get the JSON between the two markers
            json_str = captured.err[
                request_start + len("[MiMo REQUEST] ") : response_start
            ].strip()
        else:
            # Fallback: just get the part after REQUEST
            json_start = captured.err.find("{", request_start)
            json_str = captured.err[json_start:]

        parsed = json.loads(json_str)
        assert "model" in parsed
        assert "messages" in parsed

    def test_response_logged_to_stderr(
        self, client: MiMoClient, mock_transport: MockTransport, capsys: Any
    ) -> None:
        """Test that response JSON is logged to stderr."""
        client.transcribe(
            system_prompt="System",
            user_prompt="User",
            audio_data_uri="data:audio/wav;base64,test",
        )

        captured = capsys.readouterr()

        # Should have response logged to stderr
        assert "[MiMo RESPONSE]" in captured.err

        # Should be valid JSON after the prefix
        response_start = captured.err.find("[MiMo RESPONSE]")
        json_start = captured.err.find("{", response_start)
        json_str = captured.err[json_start:]
        parsed = json.loads(json_str)
        assert "id" in parsed


class TestMockTransport:
    """Tests for mock transport boundary."""

    def test_mock_transport_no_real_api_call(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that mock transport prevents real API calls."""
        # This test verifies we're using the mock, not making real calls
        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "mock-id",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {"content": "Mock response", "role": "assistant"},
                    }
                ],
                "created": 1234567890,
                "model": "test-model",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        result = client.transcribe("System", "User", "data:audio/wav;base64,test")

        # Should get the mock response, not a real API response
        assert result.id == "mock-id"
        assert result.get_content() == "Mock response"

        # Should have recorded the call
        assert len(mock_transport.get_calls()) == 1

    def test_transport_protocol_compliance(self) -> None:
        """Test that mock transport follows the protocol."""
        # Verify MockTransport implements MiMoTransport protocol
        mock = MockTransport()

        # Should be able to call create_completion
        response = mock.create_completion(
            model="test",
            messages=[],
            max_completion_tokens=100,
        )

        assert response is not None
        assert isinstance(response, ChatCompletion)


class TestOpenAiTransport:
    """Tests for the real OpenAI transport (requires mocking OpenAI client)."""

    def test_openai_transport_initialization(self) -> None:
        """Test that OpenAiTransport correctly swaps variables."""
        # Note: The original MiMo example had api_key and base_url swapped.
        # We're testing that we correctly accept them in proper order.
        transport = OpenAiTransport(
            api_key="my-api-key",
            base_url="https://api.example.com",
        )

        # The internal client should be initialized with correct values
        assert transport._client.api_key == "my-api-key"
        # Note: base_url is stored differently in OpenAI client
        assert transport._client.base_url.raw_path == b"/"  # Root path preserved


class TestToolCallParsing:
    """Tests for tool call response parsing."""

    def test_tool_call_response_parsing(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test parsing of tool call responses."""
        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "tool-call-id",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "index": 0,
                        "message": {
                            "content": "",
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "tool_one",
                                        "arguments": '{"arg1": "value1"}',
                                    },
                                },
                                {
                                    "id": "call_2",
                                    "type": "function",
                                    "function": {
                                        "name": "tool_two",
                                        "arguments": '{"arg2": "value2"}',
                                    },
                                },
                            ],
                        },
                    }
                ],
                "created": 1234567890,
                "model": "xiaomi/mimo-v2-omni",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        result = client.transcribe("System", "User", "data:audio/wav;base64,test")

        assert result.has_tool_calls()
        tool_calls = result.get_tool_calls()
        assert len(tool_calls) == 2
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[1]["id"] == "call_2"

    def test_final_response_without_tool_calls(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test parsing of final response without tool calls."""
        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "final-id",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {
                            "content": "Final answer",
                            "role": "assistant",
                        },
                    }
                ],
                "created": 1234567890,
                "model": "xiaomi/mimo-v2-omni",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        result = client.transcribe("System", "User", "data:audio/wav;base64,test")

        assert not result.has_tool_calls()
        assert result.get_tool_calls() == []
        assert result.get_content() == "Final answer"


class TestErrorHandling:
    """Tests for error handling."""

    def test_empty_choices_handling(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test handling of response with empty choices."""
        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "empty",
                "choices": [],
                "created": 1234567890,
                "model": "test",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        result = client.transcribe("System", "User", "data:audio/wav;base64,test")

        assert result.get_content() == ""
        assert result.get_tool_calls() == []

    def test_missing_message_handling(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test handling of response with empty message content."""
        mock_transport._response = ChatCompletion.model_validate(
            {
                "id": "missing",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {"role": "assistant", "content": ""},
                    }
                ],
                "created": 1234567890,
                "model": "test",
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": 1,
                    "prompt_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        result = client.transcribe("System", "User", "data:audio/wav;base64,test")

        assert result.get_content() == ""
        assert result.get_tool_calls() == []


class TestModelDefaults:
    """Tests for model and parameter defaults."""

    def test_default_model_and_tokens(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that default model and token values are used."""
        client.transcribe("System", "User", "data:audio/wav;base64,test")

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "xiaomi/mimo-v2-omni"
        assert call["max_completion_tokens"] == 1024

    def test_custom_model_and_tokens(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that custom model and token values can be specified."""
        client.transcribe(
            "System",
            "User",
            "data:audio/wav;base64,test",
            model="custom-model",
            max_completion_tokens=2048,
        )

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "custom-model"
        assert call["max_completion_tokens"] == 2048
