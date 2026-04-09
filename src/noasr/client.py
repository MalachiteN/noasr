"""MiMo client wrapper for OpenAI-compatible API."""

import json
import sys
from typing import Any, Protocol

from openai import OpenAI
from openai.types.chat import ChatCompletion

from noasr.models import MiMoRequest, MiMoResponse, AudioPayload


class MiMoTransport(Protocol):
    """Protocol for MiMo API transport - allows mocking in tests."""

    def create_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
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
        # Original: api_key=os.environ.get("OPENAI_BASEURL")
        #           base_url=os.environ.get("OPENAI_API_KEY")
        # Correct:  api_key should be the actual API key
        #           base_url should be the endpoint URL
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def create_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_completion_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
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

        return self._client.chat.completions.create(**kwargs)


class MiMoClient:
    """MiMo API client wrapper."""

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
                      If not provided, uses OpenAiTransport.
        """
        self._api_key = api_key
        self._base_url = base_url
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

    def build_transcription_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        audio_data_uri: str,
    ) -> list[dict[str, Any]]:
        """Build messages for plain transcription mode.

        Args:
            system_prompt: System prompt text.
            user_prompt: User prompt text.
            audio_data_uri: Base64 data URI for audio.

        Returns:
            List of message dicts: 1 system + 1 user (multimodal).
        """
        messages: list[dict[str, Any]] = []

        # System message
        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        # User message with audio and text
        user_content: list[dict[str, Any]] = []

        # Audio input
        user_content.append(
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_data_uri,
                },
            }
        )

        # Text prompt
        if user_prompt:
            user_content.append(
                {
                    "type": "text",
                    "text": user_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_content,
            }
        )

        return messages

    def build_agent_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        audio_data_uri: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Build messages for agent mode with tool support.

        Args:
            system_prompt: System prompt text.
            user_prompt: User prompt text.
            audio_data_uri: Base64 data URI for audio.
            conversation_history: Optional conversation history for multi-round.

        Returns:
            List of message dicts for the conversation.
        """
        # Start with history if provided
        messages = list(conversation_history) if conversation_history else []

        # If no history, add the initial messages
        if not messages:
            # System message
            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                )

            # User message with audio and text
            user_content: list[dict[str, Any]] = []

            # Audio input
            user_content.append(
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_data_uri,
                    },
                }
            )

            # Text prompt
            if user_prompt:
                user_content.append(
                    {
                        "type": "text",
                        "text": user_prompt,
                    }
                )

            messages.append(
                {
                    "role": "user",
                    "content": user_content,
                }
            )

        return messages

    def transcribe(
        self,
        system_prompt: str,
        user_prompt: str,
        audio_data_uri: str,
        model: str = "xiaomi/mimo-v2-omni",
        max_completion_tokens: int = 1024,
    ) -> MiMoResponse:
        """Send transcription request without tools.

        Args:
            system_prompt: System prompt text.
            user_prompt: User prompt text.
            audio_data_uri: Base64 data URI for audio.
            model: Model identifier.
            max_completion_tokens: Maximum tokens to generate.

        Returns:
            MiMoResponse with the transcription result.
        """
        messages = self.build_transcription_messages(
            system_prompt, user_prompt, audio_data_uri
        )

        request = MiMoRequest(
            model=model,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
        )

        # Log request
        self._log_request(request.to_dict())

        # Make request
        completion = self._transport.create_completion(
            model=model,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
        )

        # Log response
        response_json = completion.model_dump_json()
        self._log_response(response_json)

        # Parse response
        return MiMoResponse.from_dict(completion.model_dump())

    def run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        audio_data_uri: str,
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
        model: str = "xiaomi/mimo-v2-omni",
        max_completion_tokens: int = 1024,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> MiMoResponse:
        """Send agent request with tool support.

        Args:
            system_prompt: System prompt text.
            user_prompt: User prompt text.
            audio_data_uri: Base64 data URI for audio.
            tools: List of tool function definitions.
            tool_choice: Tool choice strategy.
            model: Model identifier.
            max_completion_tokens: Maximum tokens to generate.
            conversation_history: Optional conversation history.

        Returns:
            MiMoResponse with the result.
        """
        messages = self.build_agent_messages(
            system_prompt, user_prompt, audio_data_uri, conversation_history
        )

        request = MiMoRequest(
            model=model,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )

        # Log request
        self._log_request(request.to_dict())

        # Make request
        completion = self._transport.create_completion(
            model=model,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )

        # Log response
        response_json = completion.model_dump_json()
        self._log_response(response_json)

        # Parse response
        return MiMoResponse.from_dict(completion.model_dump())


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
