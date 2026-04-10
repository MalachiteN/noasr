"""MiMo client wrapper for OpenAI-compatible API.

MiMoClient is a thin transport layer with a single send() method.
All message construction is handled by AgentManager.
"""

import json
import sys
from typing import Any, Protocol

from openai import OpenAI
from openai.types.chat import ChatCompletion


class MiMoTransport(Protocol):
    """Protocol for MiMo API transport - allows mocking in tests."""

    def create_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ChatCompletion:
        """Create a chat completion."""
        ...


class OpenAiTransport:
    """Default OpenAI-compatible transport implementation."""

    def __init__(self, api_key: str, base_url: str) -> None:
        """Initialize transport with API credentials.

        Args:
            api_key: API key for authentication (corrected from baseurl in example).
            base_url: Base URL for API endpoint (corrected from api_key in example).
        """
        # Note: The original MiMo example had these swapped - this corrects it.
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def create_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ChatCompletion:
        """Create a chat completion via OpenAI API."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if extra_body is not None:
            kwargs["extra_body"] = extra_body

        return self._client.chat.completions.create(**kwargs)


class MiMoClient:
    """MiMo API client — thin transport wrapper.

    All message construction and ReAct loop logic lives in AgentManager.
    This class only handles the raw HTTP transport and logging.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        transport: MiMoTransport | None = None,
    ) -> None:
        """Initialize MiMo client.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for API endpoint.
            transport: Optional transport implementation for testing.
        """
        self._transport = transport or OpenAiTransport(api_key, base_url)

    def _log_request(self, request_dict: dict[str, Any]) -> None:
        """Log request dict to stderr as JSON."""
        try:
            json_str = json.dumps(request_dict, ensure_ascii=False, indent=2)
            print(f"[MiMo REQUEST] {json_str}", file=sys.stderr, flush=True)
        except (TypeError, ValueError) as e:
            print(
                f"[MiMo REQUEST] Failed to serialize: {e}", file=sys.stderr, flush=True
            )

    def _log_response(self, response_json: str) -> None:
        """Log response JSON to stderr."""
        print(f"[MiMo RESPONSE] {response_json}", file=sys.stderr, flush=True)

    def send(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: str = "xiaomi/mimo-v2-omni",
        max_completion_tokens: int = 1024,
        thinking_type: str = "disabled",
    ) -> dict[str, Any]:
        """Send a chat completion request and return raw response dict.

        Args:
            messages: Conversation messages.
            tools: Optional tool definitions.
            tool_choice: Optional tool choice strategy.
            model: Model identifier.
            max_completion_tokens: Maximum tokens to generate.
            thinking_type: 'enabled' or 'disabled' — controls model thinking.

        Returns:
            Raw response dict with 'choices' key.

        Raises:
            ConnectionError: On network/transport failures with detail.
            RuntimeError: On API errors (auth, rate limit, server error).
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is None and tools is not None:
            kwargs["tool_choice"] = "auto"
        elif tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        # Pass thinking configuration via extra_body (non-standard API param)
        if thinking_type in ("enabled", "disabled"):
            kwargs["extra_body"] = {"thinking": {"type": thinking_type}}

        # Log request
        self._log_request(kwargs)

        # Make request with detailed error handling
        try:
            completion = self._transport.create_completion(**kwargs)
        except Exception as e:
            # Unwrap OpenAI SDK exceptions to get the real cause
            cause = e.__cause__ if e.__cause__ else e
            error_type = type(e).__name__
            cause_type = type(cause).__name__

            # Build a descriptive error message
            parts = [f"{error_type}"]
            if cause is not e:
                parts.append(f"caused by {cause_type}: {cause}")
            else:
                parts.append(str(e))

            # Add hint based on common patterns
            msg_lower = str(cause).lower()
            if "timeout" in msg_lower:
                parts.append("(request timed out — check network or increase timeout)")
            elif "refused" in msg_lower or "connection" in msg_lower:
                parts.append("(could not reach server — check baseurl in config)")
            elif "ssl" in msg_lower or "certificate" in msg_lower:
                parts.append("(SSL/TLS error — check if baseurl uses https)")
            elif "401" in str(e) or "unauthorized" in msg_lower:
                parts.append("(authentication failed — check api_key in config)")
            elif "429" in str(e) or "rate" in msg_lower:
                parts.append("(rate limited — wait and retry)")
            elif "500" in str(e) or "502" in str(e) or "503" in str(e):
                parts.append("(server error — the API endpoint may be down)")

            detail = " ".join(parts)
            print(f"[MiMo ERROR] {detail}", file=sys.stderr, flush=True)

            # Re-raise as a descriptive error
            if (
                "connection" in msg_lower
                or "timeout" in msg_lower
                or "refused" in msg_lower
            ):
                raise ConnectionError(detail) from e
            raise RuntimeError(detail) from e

        # Log response
        response_json = completion.model_dump_json()
        self._log_response(response_json)

        # Return raw dict for caller to parse
        return completion.model_dump()


def create_client(
    api_key: str,
    base_url: str = "https://api.mi-fds.com/v1",
    transport: MiMoTransport | None = None,
) -> MiMoClient:
    """Factory function to create a MiMo client.

    Args:
        api_key: API key for authentication.
        base_url: Base URL for API endpoint.
        transport: Optional transport for testing.

    Returns:
        Configured MiMoClient instance.
    """
    return MiMoClient(api_key=api_key, base_url=base_url, transport=transport)
