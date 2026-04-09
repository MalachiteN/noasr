"""Audio recording and normalization for noasr.

This module provides:
- Pure helper functions for audio normalization (testable with synthetic data)
- AudioRecorder class for live microphone capture via sounddevice

Design separates device I/O from byte-level processing for testability.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd

from noasr.constants import (
    AUDIO_BIT_DEPTH,
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    MAX_RECORDING_DURATION,
    MIN_RECORDING_DURATION,
)


class RecordingTooShortError(Exception):
    """Raised when recording is shorter than minimum duration."""

    pass


class RecordingTooLongError(Exception):
    """Raised when recording exceeds maximum duration."""

    pass


@dataclass(frozen=True)
class AudioFormat:
    """Normalized audio format specification."""

    sample_rate: int = AUDIO_SAMPLE_RATE
    channels: int = AUDIO_CHANNELS
    bit_depth: int = AUDIO_BIT_DEPTH

    @property
    def sample_width(self) -> int:
        """Sample width in bytes."""
        return self.bit_depth // 8


def normalize_audio(
    samples: np.ndarray,
    source_sample_rate: int,
    source_channels: int,
    target_format: AudioFormat | None = None,
) -> np.ndarray:
    """Normalize audio samples to target format.

    Args:
        samples: Input audio samples (numpy array)
        source_sample_rate: Original sample rate in Hz
        source_channels: Number of channels in input
        target_format: Target format (defaults to mono 16kHz 16-bit)

    Returns:
        Normalized samples as float64 array (range -1.0 to 1.0)
    """
    if target_format is None:
        target_format = AudioFormat()

    # Ensure float64 for processing
    if samples.dtype != np.float64:
        if np.issubdtype(samples.dtype, np.integer):
            # Convert integer to float, normalize by max value
            max_val = np.iinfo(samples.dtype).max
            samples = samples.astype(np.float64) / max_val
        else:
            samples = samples.astype(np.float64)

    # Ensure 2D array [frames, channels]
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)

    # Convert to mono if needed
    if source_channels > 1 and target_format.channels == 1:
        samples = np.mean(samples, axis=1, keepdims=True)

    # Resample if needed (simple linear interpolation for MVP)
    if source_sample_rate != target_format.sample_rate:
        samples = _resample(samples, source_sample_rate, target_format.sample_rate)

    return samples.squeeze()  # Return 1D array for mono


def _resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio using linear interpolation.

    Simple implementation suitable for MVP. For production,
    consider scipy.signal.resample or librosa.
    """
    # Calculate new length
    ratio = target_rate / source_rate
    new_length = int(len(samples) * ratio)

    # Create interpolation indices
    old_indices = np.linspace(0, len(samples) - 1, new_length)

    # Linear interpolation
    indices_floor = np.floor(old_indices).astype(np.int64)
    indices_ceil = np.minimum(indices_floor + 1, len(samples) - 1)
    fractions = old_indices - indices_floor

    if samples.ndim == 2:
        resampled = (
            samples[indices_floor] * (1 - fractions)[:, np.newaxis]
            + samples[indices_ceil] * fractions[:, np.newaxis]
        )
    else:
        resampled = (
            samples[indices_floor] * (1 - fractions) + samples[indices_ceil] * fractions
        )

    return resampled


def samples_to_int16(samples: np.ndarray) -> np.ndarray:
    """Convert float samples to 16-bit integers.

    Args:
        samples: Float samples in range [-1.0, 1.0]

    Returns:
        16-bit integer samples
    """
    # Clip to valid range
    clipped = np.clip(samples, -1.0, 1.0)
    # Convert to int16
    return (clipped * 32767).astype(np.int16)


def create_wav_bytes(
    samples: np.ndarray,
    sample_rate: int = AUDIO_SAMPLE_RATE,
    channels: int = AUDIO_CHANNELS,
) -> bytes:
    """Create WAV file bytes from normalized float samples.

    Args:
        samples: Normalized float samples (mono or stereo)
        sample_rate: Sample rate in Hz
        channels: Number of channels

    Returns:
        WAV file as bytes
    """
    # Convert to int16
    int_samples = samples_to_int16(samples)

    # Create WAV in memory
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int_samples.tobytes())

    return buffer.getvalue()


def normalize_to_wav_bytes(
    samples: np.ndarray,
    source_sample_rate: int,
    source_channels: int,
) -> bytes:
    """Complete pipeline: normalize samples and create WAV bytes.

    Args:
        samples: Input audio samples
        source_sample_rate: Original sample rate
        source_channels: Original channel count

    Returns:
        WAV file bytes in normalized format (mono 16kHz 16-bit)
    """
    normalized = normalize_audio(samples, source_sample_rate, source_channels)
    return create_wav_bytes(normalized, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS)


def get_recording_duration(samples: np.ndarray, sample_rate: int) -> float:
    """Calculate recording duration in seconds.

    Args:
        samples: Audio samples
        sample_rate: Sample rate in Hz

    Returns:
        Duration in seconds
    """
    return len(samples) / sample_rate


def validate_recording_duration(duration: float) -> None:
    """Validate recording duration against constraints.

    Args:
        duration: Recording duration in seconds

    Raises:
        RecordingTooShortError: If duration < MIN_RECORDING_DURATION
        RecordingTooLongError: If duration > MAX_RECORDING_DURATION
    """
    if duration < MIN_RECORDING_DURATION:
        raise RecordingTooShortError(
            f"Recording too short: {duration:.3f}s < {MIN_RECORDING_DURATION}s"
        )
    if duration > MAX_RECORDING_DURATION:
        raise RecordingTooLongError(
            f"Recording too long: {duration:.3f}s > {MAX_RECORDING_DURATION}s"
        )


class AudioRecorder:
    """Audio recorder with non-blocking lifecycle.

    Separates device I/O from processing for testability.
    The device layer can be mocked by providing a custom stream_factory.
    """

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
        dtype: np.dtype = np.float32,
        blocksize: int = 1024,
        device: int | None = None,
        stream_factory: Callable | None = None,
    ):
        """Initialize recorder.

        Args:
            sample_rate: Recording sample rate (default 16kHz)
            channels: Number of channels (default 1 for mono)
            dtype: Sample data type (default float32)
            blocksize: Buffer size per callback (default 1024)
            device: Audio device ID (None for default)
            stream_factory: Optional factory to create InputStream for testing
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.blocksize = blocksize
        self.device = device
        self._stream_factory = stream_factory or sd.InputStream

        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def _callback(
        self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ) -> None:
        """Internal callback for audio stream."""
        if status:
            # Log any status flags (overrun/underrun)
            pass
        if self._is_recording:
            self._frames.append(indata.copy())

    def start(self) -> None:
        """Start recording.

        Raises:
            RuntimeError: If already recording
        """
        if self._is_recording:
            raise RuntimeError("Recording already in progress")

        self._frames = []
        self._is_recording = True

        self._stream = self._stream_factory(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.blocksize,
            device=self.device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return captured samples.

        Returns:
            Captured audio as numpy array

        Raises:
            RuntimeError: If not recording
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        self._is_recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return np.array([], dtype=self.dtype)

        # Concatenate all frames
        return np.concatenate(self._frames, axis=0)

    def stop_and_normalize(self) -> bytes:
        """Stop recording and return normalized WAV bytes.

        Returns:
            WAV file bytes in normalized format

        Raises:
            RecordingTooShortError: If recording is too short
        """
        samples = self.stop()
        duration = get_recording_duration(samples, self.sample_rate)

        if duration < MIN_RECORDING_DURATION:
            raise RecordingTooShortError(
                f"Recording too short: {duration:.3f}s < {MIN_RECORDING_DURATION}s"
            )

        return normalize_to_wav_bytes(samples, self.sample_rate, self.channels)

    def get_elapsed_time(self) -> float:
        """Get elapsed recording time in seconds.

        Returns:
            Elapsed time since start() was called
        """
        if not self._is_recording:
            return 0.0

        total_samples = sum(len(frame) for frame in self._frames)
        return total_samples / self.sample_rate

    def should_auto_stop(self) -> bool:
        """Check if recording should auto-stop due to max duration.

        Returns:
            True if max duration reached
        """
        return self.get_elapsed_time() >= MAX_RECORDING_DURATION

    def __enter__(self) -> AudioRecorder:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._is_recording:
            self.stop()


def record_for_duration(duration: float, **kwargs) -> bytes:
    """Convenience function: record for a specific duration.

    Args:
        duration: Recording duration in seconds (capped at MAX_RECORDING_DURATION)
        **kwargs: Additional arguments passed to AudioRecorder

    Returns:
        Normalized WAV bytes
    """
    duration = min(duration, MAX_RECORDING_DURATION)

    recorder = AudioRecorder(**kwargs)
    recorder.start()

    import time

    time.sleep(duration)

    return recorder.stop_and_normalize()


def create_synthetic_sine_wave(
    duration: float,
    frequency: float = 440.0,
    sample_rate: int = AUDIO_SAMPLE_RATE,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Create synthetic sine wave for testing.

    Args:
        duration: Wave duration in seconds
        frequency: Sine wave frequency in Hz
        sample_rate: Sample rate in Hz
        amplitude: Wave amplitude (0.0 to 1.0)

    Returns:
        Sine wave samples as float64 array
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * frequency * t)


def create_synthetic_noise(
    duration: float,
    sample_rate: int = AUDIO_SAMPLE_RATE,
    amplitude: float = 0.1,
) -> np.ndarray:
    """Create synthetic noise for testing.

    Args:
        duration: Noise duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Noise amplitude

    Returns:
        Noise samples as float64 array
    """
    num_samples = int(sample_rate * duration)
    return amplitude * (2 * np.random.random(num_samples) - 1)
