"""Tests for domain models and constants."""

import base64
from unittest import mock

import pytest

from noasr import constants, models
from noasr.constants import (
    AUDIO_BIT_DEPTH,
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    MAX_RECORDING_DURATION,
    MIN_RECORDING_DURATION,
    PlatformCapability,
)


class TestConstants:
    """Test constant values."""

    def test_audio_constants(self) -> None:
        """Test audio format constants."""
        assert AUDIO_SAMPLE_RATE == 16000
        assert AUDIO_BIT_DEPTH == 16
        assert AUDIO_CHANNELS == 1

    def test_recording_duration_constants(self) -> None:
        """Test recording duration constraints."""
        assert MIN_RECORDING_DURATION == 0.3  # 300ms
        assert MAX_RECORDING_DURATION == 30.0  # 30s

    def test_platform_capability_values(self) -> None:
        """Test platform capability constants."""
        assert PlatformCapability.WINDOWS == "windows"
        assert PlatformCapability.MACOS == "macos"
        assert PlatformCapability.LINUX == "linux"
        assert PlatformCapability.LINUX_X11 == "linux_x11"
        assert PlatformCapability.LINUX_WAYLAND == "linux_wayland"

    def test_platform_warnings_exist(self) -> None:
        """Test that platform warnings are defined."""
        from noasr.constants import PLATFORM_WARNINGS

        assert PlatformCapability.MACOS in PLATFORM_WARNINGS
        assert PlatformCapability.LINUX in PLATFORM_WARNINGS
        assert PlatformCapability.LINUX_X11 in PLATFORM_WARNINGS
        assert PlatformCapability.LINUX_WAYLAND in PLATFORM_WARNINGS


class TestAppConfig:
    """Test AppConfig model."""

    def test_default_values(self) -> None:
        """Test that AppConfig has correct defaults."""
        config = models.AppConfig()

        assert config.baseurl == "https://api.mi-fds.com/v1"
        assert config.api_key == ""
        assert config.toolsets == {}
        assert config.agents == []

    def test_from_dict_with_defaults(self) -> None:
        """Test that from_dict uses defaults for missing fields."""
        config = models.AppConfig.from_dict({})

        assert config.baseurl == "https://api.mi-fds.com/v1"
        assert config.api_key == ""
        assert config.toolsets == {}
        assert config.agents == []

    def test_from_dict_with_values(self) -> None:
        """Test that from_dict correctly parses values."""
        data = {
            "baseurl": "https://custom.api.com",
            "api_key": "test-key",
            "toolsets": {"default": ["Tool1"]},
            "agents": [{"name": "test"}],
        }
        config = models.AppConfig.from_dict(data)

        assert config.baseurl == "https://custom.api.com"
        assert config.api_key == "test-key"
        assert config.toolsets == {"default": ["Tool1"]}
        assert config.agents == [{"name": "test"}]

    def test_from_dict_partial_values(self) -> None:
        """Test that from_dict uses defaults for partial data."""
        config = models.AppConfig.from_dict({"api_key": "only-this"})

        assert config.baseurl == "https://api.mi-fds.com/v1"  # default
        assert config.api_key == "only-this"
        assert config.toolsets == {}  # default


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_default_values(self) -> None:
        """Test that AgentConfig has correct defaults."""
        agent = models.AgentConfig()

        assert agent.name == ""
        assert agent.trigger == []
        assert agent.toolsets == []

    def test_from_dict(self) -> None:
        """Test that from_dict correctly parses agent config."""
        data = {
            "name": "dictate",
            "trigger": [62, 62],
            "toolsets": ["default"],
        }
        agent = models.AgentConfig.from_dict(data)

        assert agent.name == "dictate"
        assert agent.trigger == [62, 62]
        assert agent.toolsets == ["default"]


class TestRuntimeState:
    """Test RuntimeState enum."""

    def test_state_values(self) -> None:
        """Test that all runtime states are defined."""
        assert models.RuntimeState.IDLE is not None
        assert models.RuntimeState.LISTENING is not None
        assert models.RuntimeState.LOADING is not None
        assert models.RuntimeState.ERROR is not None
        assert models.RuntimeState.APPLYING_RESULT is not None


class TestOverlayState:
    """Test OverlayState enum."""

    def test_state_values(self) -> None:
        """Test that all overlay states are defined."""
        assert models.OverlayState.HIDDEN is not None
        assert models.OverlayState.LISTENING is not None
        assert models.OverlayState.LOADING is not None
        assert models.OverlayState.ERROR is not None


class TestMiMoRequest:
    """Test MiMoRequest model."""

    def test_default_values(self) -> None:
        """Test that MiMoRequest has correct defaults."""
        req = models.MiMoRequest()

        assert req.model == "xiaomi/mimo-v2-omni"
        assert req.messages == []
        assert req.max_completion_tokens == 1024
        assert req.tools is None
        assert req.tool_choice is None

    def test_to_dict_without_tools(self) -> None:
        """Test to_dict excludes None tool fields."""
        req = models.MiMoRequest(messages=[{"role": "user", "content": "test"}])
        data = req.to_dict()

        assert "tools" not in data
        assert "tool_choice" not in data
        assert data["model"] == "xiaomi/mimo-v2-omni"
        assert data["messages"] == [{"role": "user", "content": "test"}]

    def test_to_dict_with_tools(self) -> None:
        """Test to_dict includes tool fields when set."""
        req = models.MiMoRequest(
            messages=[],
            tools=[{"type": "function"}],
            tool_choice="auto",
        )
        data = req.to_dict()

        assert data["tools"] == [{"type": "function"}]
        assert data["tool_choice"] == "auto"


class TestMiMoResponse:
    """Test MiMoResponse model."""

    def test_from_dict(self) -> None:
        """Test that from_dict correctly parses response."""
        data = {
            "id": "test-123",
            "choices": [{"message": {"content": "Hello"}}],
            "model": "xiaomi/mimo-v2-omni",
            "usage": {"total_tokens": 100},
        }
        resp = models.MiMoResponse.from_dict(data)

        assert resp.id == "test-123"
        assert resp.choices == [{"message": {"content": "Hello"}}]
        assert resp.model == "xiaomi/mimo-v2-omni"
        assert resp.usage == {"total_tokens": 100}

    def test_get_content(self) -> None:
        """Test getting content from response."""
        resp = models.MiMoResponse(choices=[{"message": {"content": "Test content"}}])

        assert resp.get_content() == "Test content"

    def test_get_content_empty_choices(self) -> None:
        """Test getting content with empty choices."""
        resp = models.MiMoResponse(choices=[])

        assert resp.get_content() == ""

    def test_get_tool_calls(self) -> None:
        """Test getting tool calls from response."""
        tool_calls = [{"id": "call-1", "function": {"name": "test"}}]
        resp = models.MiMoResponse(choices=[{"message": {"tool_calls": tool_calls}}])

        assert resp.get_tool_calls() == tool_calls

    def test_get_tool_calls_none(self) -> None:
        """Test getting tool calls when None."""
        resp = models.MiMoResponse(choices=[{"message": {"tool_calls": None}}])

        assert resp.get_tool_calls() == []

    def test_has_tool_calls_true(self) -> None:
        """Test has_tool_calls when true."""
        resp = models.MiMoResponse(
            choices=[{"message": {"tool_calls": [{"id": "call-1"}]}}]
        )

        assert resp.has_tool_calls() is True

    def test_has_tool_calls_false(self) -> None:
        """Test has_tool_calls when false."""
        resp = models.MiMoResponse(choices=[{"message": {"content": "Hello"}}])

        assert resp.has_tool_calls() is False


class TestAudioPayload:
    """Test AudioPayload model."""

    def test_from_wav_bytes(self) -> None:
        """Test creating audio payload from WAV bytes."""
        wav_bytes = b"RIFF....WAVE"  # Fake WAV header
        payload = models.AudioPayload.from_wav_bytes(wav_bytes)

        # Verify it starts with data URI prefix
        assert payload.data_uri.startswith("data:audio/wav;base64,")

        # Verify we can decode it back
        encoded_part = payload.data_uri.replace("data:audio/wav;base64,", "")
        decoded = base64.b64decode(encoded_part)
        assert decoded == wav_bytes

    def test_to_api_item(self) -> None:
        """Test converting to API message item."""
        payload = models.AudioPayload(data_uri="data:audio/wav;base64,test123")
        item = payload.to_api_item()

        assert item == {
            "type": "input_audio",
            "input_audio": {"data": "data:audio/wav;base64,test123"},
        }

    def test_audio_encoding_deterministic(self) -> None:
        """Test that audio encoding produces consistent results."""
        wav_bytes = b"test audio data for encoding"

        payload1 = models.AudioPayload.from_wav_bytes(wav_bytes)
        payload2 = models.AudioPayload.from_wav_bytes(wav_bytes)

        assert payload1.data_uri == payload2.data_uri


class TestPlatformInfo:
    """Test PlatformInfo model."""

    def test_windows_platform(self) -> None:
        """Test Windows platform detection."""
        with mock.patch("sys.platform", "win32"):
            info = models.get_platform_info()

        assert info.is_windows is True
        assert info.is_macos is False
        assert info.is_linux is False

    def test_macos_platform(self) -> None:
        """Test macOS platform detection."""
        with mock.patch("sys.platform", "darwin"):
            info = models.get_platform_info()

        assert info.is_windows is False
        assert info.is_macos is True
        assert info.is_linux is False

    def test_linux_x11_platform(self) -> None:
        """Test Linux X11 platform detection."""
        env_vars = {"DISPLAY": ":0"}
        with mock.patch("sys.platform", "linux"):
            with mock.patch.dict("os.environ", env_vars):
                info = models.get_platform_info()

        assert info.is_windows is False
        assert info.is_macos is False
        assert info.is_linux is True
        assert info.display_server == "x11"

    def test_linux_wayland_platform(self) -> None:
        """Test Linux Wayland platform detection."""
        env_vars = {"WAYLAND_DISPLAY": "wayland-1"}
        with mock.patch("sys.platform", "linux"):
            with mock.patch.dict("os.environ", env_vars, clear=False):
                info = models.get_platform_info()

        assert info.is_windows is False
        assert info.is_macos is False
        assert info.is_linux is True
        assert info.display_server == "wayland"

    def test_get_warnings_windows(self) -> None:
        """Test that Windows has no warnings."""
        info = models.PlatformInfo(is_windows=True)

        assert info.get_warnings() == []

    def test_get_warnings_macos(self) -> None:
        """Test macOS warnings."""
        info = models.PlatformInfo(is_macos=True)
        warnings = info.get_warnings()

        assert len(warnings) == 1
        assert "Accessibility" in warnings[0]
