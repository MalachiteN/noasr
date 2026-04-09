"""Tests for MiMo client wrapper."""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai.types.chat import ChatCompletion

from noasr.client import MiMoClient, OpenAiTransport, create_client, MiMoTransport


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


class TestSend:
    """Tests for MiMoClient.send()."""

    def test_send_passes_correct_kwargs_to_transport(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that send() passes correct kwargs to transport."""
        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"},
        ]

        client.send(messages=messages)

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "xiaomi/mimo-v2-omni"
        assert call["messages"] == messages
        assert call["max_completion_tokens"] == 1024


class TestArchitecturalInvariants:
    """Verify that deleted methods are not accidentally reintroduced."""

    def test_mimoclient_has_no_transcribe_method(self) -> None:
        """MiMoClient.transcribe() was removed in the agent-centric refactor."""
        client = MiMoClient(api_key="k", base_url="u")
        assert not hasattr(client, "transcribe"), (
            "MiMoClient.transcribe() should not exist — all LLM calls go through AgentManager"
        )

    def test_mimoclient_has_no_run_agent_method(self) -> None:
        """MiMoClient.run_agent() was removed in the agent-centric refactor."""
        client = MiMoClient(api_key="k", base_url="u")
        assert not hasattr(client, "run_agent"), (
            "MiMoClient.run_agent() should not exist — all LLM calls go through AgentManager"
        )

    def test_mimoclient_has_no_build_transcription_messages(self) -> None:
        """MiMoClient.build_transcription_messages() was removed."""
        client = MiMoClient(api_key="k", base_url="u")
        assert not hasattr(client, "build_transcription_messages"), (
            "MiMoClient.build_transcription_messages() should not exist — message construction is in AgentManager"
        )

    def test_mimoclient_has_no_build_agent_messages(self) -> None:
        """MiMoClient.build_agent_messages() was removed."""
        client = MiMoClient(api_key="k", base_url="u")
        assert not hasattr(client, "build_agent_messages"), (
            "MiMoClient.build_agent_messages() should not exist — message construction is in AgentManager"
        )

    def test_mimoclient_has_send_method(self) -> None:
        """MiMoClient.send() is the sole transport method."""
        client = MiMoClient(api_key="k", base_url="u")
        assert hasattr(client, "send"), (
            "MiMoClient.send() must exist as the sole transport method"
        )

    def test_send_no_tools_no_tool_choice(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that send() omits tool_choice when no tools provided."""
        client.send(messages=[])

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["tools"] is None
        assert call["tool_choice"] is None


class TestLogging:
    """Tests for request/response logging to stderr."""

    def test_request_logged_to_stderr(
        self, client: MiMoClient, mock_transport: MockTransport, capsys: Any
    ) -> None:
        """Test that request dict is logged to stderr."""
        client.send(messages=[{"role": "user", "content": "Hello"}])

        captured = capsys.readouterr()

        # Should have request logged to stderr
        assert "[MiMo REQUEST]" in captured.err

        # Extract JSON between REQUEST and RESPONSE markers
        request_start = captured.err.find("[MiMo REQUEST]")
        response_start = captured.err.find("[MiMo RESPONSE]")

        if response_start > request_start:
            json_str = captured.err[
                request_start + len("[MiMo REQUEST] ") : response_start
            ].strip()
        else:
            json_start = captured.err.find("{", request_start)
            json_str = captured.err[json_start:]

        parsed = json.loads(json_str)
        assert "model" in parsed
        assert "messages" in parsed

    def test_response_logged_to_stderr(
        self, client: MiMoClient, mock_transport: MockTransport, capsys: Any
    ) -> None:
        """Test that response JSON is logged to stderr."""
        client.send(messages=[{"role": "user", "content": "Hello"}])

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

        result = client.send(messages=[{"role": "user", "content": "test"}])

        # Should get the mock response as a raw dict
        assert isinstance(result, dict)
        assert result["id"] == "mock-id"
        assert result["choices"][0]["message"]["content"] == "Mock response"

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
    """Tests for tool call response parsing via send()."""

    def test_tool_call_response_parsing(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test parsing of tool call responses from send()."""
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

        result = client.send(messages=[{"role": "user", "content": "test"}])

        # Result is a raw dict — check tool_calls in the response
        tool_calls = result["choices"][0]["message"].get("tool_calls", [])
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

        result = client.send(messages=[{"role": "user", "content": "test"}])

        message = result["choices"][0]["message"]
        assert message.get("tool_calls") is None
        assert message["content"] == "Final answer"


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

        result = client.send(messages=[{"role": "user", "content": "test"}])

        assert result["choices"] == []

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

        result = client.send(messages=[{"role": "user", "content": "test"}])

        assert result["choices"][0]["message"]["content"] == ""


class TestModelDefaults:
    """Tests for model and parameter defaults."""

    def test_default_model_and_tokens(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that default model and token values are used."""
        client.send(messages=[{"role": "user", "content": "test"}])

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "xiaomi/mimo-v2-omni"
        assert call["max_completion_tokens"] == 1024

    def test_custom_model_and_tokens(
        self, client: MiMoClient, mock_transport: MockTransport
    ) -> None:
        """Test that custom model and token values can be specified."""
        client.send(
            messages=[{"role": "user", "content": "test"}],
            model="custom-model",
            max_completion_tokens=2048,
        )

        call = mock_transport.get_last_call()
        assert call is not None
        assert call["model"] == "custom-model"
        assert call["max_completion_tokens"] == 2048
