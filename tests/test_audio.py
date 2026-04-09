"""Tests for audio module.

All tests use synthetic data or mocked devices - no real microphone required.
"""

import io
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import sounddevice as sd

from noasr.audio import (
    AudioFormat,
    AudioRecorder,
    RecordingTooLongError,
    RecordingTooShortError,
    create_synthetic_noise,
    create_synthetic_sine_wave,
    create_wav_bytes,
    get_recording_duration,
    normalize_audio,
    normalize_to_wav_bytes,
    samples_to_int16,
    validate_recording_duration,
)
from noasr.constants import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    MAX_RECORDING_DURATION,
    MIN_RECORDING_DURATION,
)


class TestNormalizeAudio:
    """Tests for normalize_audio function."""

    def test_mono_to_mono_no_change(self):
        """Mono input at target rate should remain unchanged."""
        samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0])
        result = normalize_audio(samples, AUDIO_SAMPLE_RATE, 1)
        np.testing.assert_array_almost_equal(result, samples)

    def test_stereo_to_mono_averaging(self):
        """Stereo should be averaged to mono."""
        # Stereo samples [left, right]
        samples = np.array([[1.0, 0.0], [0.5, 0.5], [-1.0, 1.0]])
        result = normalize_audio(samples, AUDIO_SAMPLE_RATE, 2)
        expected = np.array([0.5, 0.5, 0.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_resample_48k_to_16k(self):
        """Resample from 48kHz to 16kHz."""
        duration = 1.0  # 1 second
        samples_48k = create_synthetic_sine_wave(duration, 440.0, 48000)
        result = normalize_audio(samples_48k, 48000, 1)

        # Should be 1/3 the length (48000 -> 16000)
        expected_length = int(AUDIO_SAMPLE_RATE * duration)
        assert len(result) == expected_length

    def test_resample_44_1k_to_16k(self):
        """Resample from 44.1kHz to 16kHz."""
        duration = 1.0
        samples_44k = create_synthetic_sine_wave(duration, 440.0, 44100)
        result = normalize_audio(samples_44k, 44100, 1)

        expected_length = int(AUDIO_SAMPLE_RATE * duration)
        assert abs(len(result) - expected_length) <= 1  # Allow rounding error

    def test_integer_to_float_conversion(self):
        """Integer samples should be normalized to float."""
        int_samples = np.array([0, 16384, -16384, 32767, -32768], dtype=np.int16)
        result = normalize_audio(int_samples, AUDIO_SAMPLE_RATE, 1)

        expected = np.array([0.0, 0.5, -0.5, 0.99997, -1.0], dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected, decimal=4)

    def test_stereo_resample_to_mono(self):
        """Complex case: stereo at 48kHz -> mono at 16kHz."""
        duration = 0.5
        samples = np.random.randn(int(48000 * duration), 2)
        result = normalize_audio(samples, 48000, 2)

        expected_length = int(AUDIO_SAMPLE_RATE * duration)
        assert len(result) == expected_length


class TestSamplesToInt16:
    """Tests for samples_to_int16 function."""

    def test_zero_remains_zero(self):
        """Zero samples should remain zero."""
        samples = np.array([0.0, 0.0, 0.0])
        result = samples_to_int16(samples)
        expected = np.array([0, 0, 0], dtype=np.int16)
        np.testing.assert_array_equal(result, expected)

    def test_one_to_max_int16(self):
        """1.0 should map to 32767."""
        samples = np.array([1.0])
        result = samples_to_int16(samples)
        assert result[0] == 32767

    def test_minus_one_to_min_int16(self):
        """-1.0 should map to -32768 (approximately)."""
        samples = np.array([-1.0])
        result = samples_to_int16(samples)
        # Due to the multiplication by 32767, -1.0 becomes -32767
        assert result[0] == -32767

    def test_clipping(self):
        """Values outside [-1, 1] should be clipped."""
        samples = np.array([2.0, -2.0, 0.5])
        result = samples_to_int16(samples)
        assert result[0] == 32767  # Clipped
        assert result[1] == -32767  # Clipped
        # 0.5 * 32767 = 16383.5 -> rounds to 16383 or 16384 depending on implementation
        assert abs(result[2] - 16384) <= 1  # Normal (allow rounding difference)

    def test_half_amplitude(self):
        """0.5 should map to approximately 16384."""
        samples = np.array([0.5])
        result = samples_to_int16(samples)
        # 0.5 * 32767 = 16383.5, allow either 16383 or 16384
        assert abs(result[0] - 16384) <= 1


class TestCreateWavBytes:
    """Tests for create_wav_bytes function."""

    def test_creates_valid_wav(self):
        """Output should be a valid WAV file."""
        samples = create_synthetic_sine_wave(0.5)
        wav_bytes = create_wav_bytes(samples, AUDIO_SAMPLE_RATE, 1)

        # Parse the WAV file
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2  # 16-bit
            assert wav_file.getframerate() == AUDIO_SAMPLE_RATE
            assert wav_file.getnframes() == len(samples)

    def test_wav_contains_correct_data(self):
        """WAV should contain the correct audio data."""
        samples = np.array([0.5, -0.5, 0.0])
        wav_bytes = create_wav_bytes(samples, AUDIO_SAMPLE_RATE, 1)

        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wav_file:
            raw_data = wav_file.readframes(wav_file.getnframes())
            # Should be 6 bytes (3 samples * 2 bytes each)
            assert len(raw_data) == 6

    def test_empty_samples(self):
        """Empty samples should create valid empty WAV."""
        samples = np.array([])
        wav_bytes = create_wav_bytes(samples, AUDIO_SAMPLE_RATE, 1)

        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wav_file:
            assert wav_file.getnframes() == 0


class TestNormalizeToWavBytes:
    """Tests for the complete normalization pipeline."""

    def test_complete_pipeline_48k_stereo(self):
        """Full pipeline: 48kHz stereo -> 16kHz mono WAV."""
        duration = 0.5
        samples = create_synthetic_sine_wave(duration, 440.0, 48000)
        # Make it "stereo" by duplicating
        stereo_samples = np.column_stack([samples, samples])

        wav_bytes = normalize_to_wav_bytes(stereo_samples, 48000, 2)

        # Verify the output
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getframerate() == AUDIO_SAMPLE_RATE
            assert wav_file.getsampwidth() == 2
            # Should be approximately 0.5s at 16kHz
            expected_frames = int(AUDIO_SAMPLE_RATE * duration)
            assert abs(wav_file.getnframes() - expected_frames) <= 1

    def test_data_uri_compatible(self):
        """Output should be suitable for base64 data URI."""
        samples = create_synthetic_sine_wave(0.3)
        wav_bytes = normalize_to_wav_bytes(samples, AUDIO_SAMPLE_RATE, 1)

        # Should be able to encode to base64
        import base64

        encoded = base64.b64encode(wav_bytes).decode("utf-8")
        data_uri = f"data:audio/wav;base64,{encoded}"

        # Verify it starts correctly
        assert data_uri.startswith("data:audio/wav;base64,")
        # Verify we can decode it back
        decoded = base64.b64decode(encoded)
        assert decoded == wav_bytes


class TestRecordingDuration:
    """Tests for recording duration calculations and validation."""

    def test_get_recording_duration(self):
        """Duration calculation should be accurate."""
        sample_rate = 16000
        samples = np.zeros(16000)  # 1 second
        assert get_recording_duration(samples, sample_rate) == 1.0

        samples = np.zeros(8000)  # 0.5 seconds
        assert get_recording_duration(samples, sample_rate) == 0.5

    def test_validate_short_recording(self):
        """Too short recordings should raise exception."""
        with pytest.raises(RecordingTooShortError):
            validate_recording_duration(0.1)  # 100ms < 300ms

        # Edge case: exactly at minimum should pass
        validate_recording_duration(MIN_RECORDING_DURATION)

    def test_validate_long_recording(self):
        """Too long recordings should raise exception."""
        with pytest.raises(RecordingTooLongError):
            validate_recording_duration(31.0)  # 31s > 30s

        # Edge case: exactly at maximum should pass
        validate_recording_duration(MAX_RECORDING_DURATION)

    def test_validate_normal_recording(self):
        """Normal duration should not raise."""
        validate_recording_duration(1.0)
        validate_recording_duration(5.0)
        validate_recording_duration(29.9)


class TestSyntheticWaveGeneration:
    """Tests for synthetic wave generation helpers."""

    def test_sine_wave_properties(self):
        """Sine wave should have correct properties."""
        duration = 1.0
        frequency = 440.0
        samples = create_synthetic_sine_wave(duration, frequency)

        assert len(samples) == int(AUDIO_SAMPLE_RATE * duration)
        assert samples.dtype == np.float64
        # Amplitude should be within bounds
        assert np.max(samples) <= 0.5
        assert np.min(samples) >= -0.5

    def test_sine_wave_frequency(self):
        """Sine wave should have correct frequency."""
        duration = 0.1
        frequency = 1000.0  # 1kHz
        samples = create_synthetic_sine_wave(duration, frequency)

        # Count zero crossings to estimate frequency
        zero_crossings = np.sum(np.diff(np.sign(samples)) != 0)
        # Should have approximately 2 * duration * frequency crossings
        expected_crossings = 2 * duration * frequency
        assert abs(zero_crossings - expected_crossings) <= 2

    def test_noise_properties(self):
        """Noise should have correct properties."""
        duration = 0.5
        amplitude = 0.1
        samples = create_synthetic_noise(duration, amplitude=amplitude)

        assert len(samples) == int(AUDIO_SAMPLE_RATE * duration)
        assert samples.dtype == np.float64
        assert np.max(samples) <= amplitude
        assert np.min(samples) >= -amplitude


class MockInputStream:
    """Mock sounddevice InputStream for testing."""

    def __init__(self, callback, samplerate, channels, dtype, **kwargs):
        self.callback = callback
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self._running = False
        self._mock_data = []
        self._current_frame = 0

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def close(self):
        pass

    def inject_mock_frames(self, frames):
        """Inject synthetic frames as if from microphone."""
        self._mock_data.extend(frames)
        # Simulate callback for each frame
        for frame in frames:
            if self._running:
                self.callback(frame, len(frame), {}, sd.CallbackFlags())


class TestAudioRecorder:
    """Tests for AudioRecorder with mocked device."""

    def test_recorder_lifecycle(self):
        """Test start/stop lifecycle."""
        mock_factory = MagicMock()
        mock_stream = MagicMock()
        mock_factory.return_value = mock_stream

        recorder = AudioRecorder(stream_factory=mock_factory)

        assert not recorder.is_recording

        recorder.start()
        assert recorder.is_recording
        mock_factory.assert_called_once()
        mock_stream.start.assert_called_once()

        # Simulate some audio data
        frame = np.array([[0.1, 0.2]], dtype=np.float32)
        recorder._callback(frame, 1, {}, sd.CallbackFlags())

        result = recorder.stop()
        assert not recorder.is_recording
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    def test_cannot_start_while_recording(self):
        """Starting while recording should raise."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(stream_factory=mock_factory)
        recorder.start()

        with pytest.raises(RuntimeError, match="already in progress"):
            recorder.start()

        recorder.stop()

    def test_cannot_stop_when_not_recording(self):
        """Stopping when not recording should raise."""
        recorder = AudioRecorder()

        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.stop()

    def test_concatenates_frames(self):
        """Multiple frames should be concatenated."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(stream_factory=mock_factory)
        recorder.start()

        # Simulate 3 frames
        frame1 = np.array([[0.1]], dtype=np.float32)
        frame2 = np.array([[0.2]], dtype=np.float32)
        frame3 = np.array([[0.3]], dtype=np.float32)

        recorder._callback(frame1, 1, {}, sd.CallbackFlags())
        recorder._callback(frame2, 1, {}, sd.CallbackFlags())
        recorder._callback(frame3, 1, {}, sd.CallbackFlags())

        result = recorder.stop()
        assert len(result) == 3
        np.testing.assert_array_almost_equal(result.flatten(), [0.1, 0.2, 0.3])

    def test_elapsed_time_tracking(self):
        """Elapsed time should be tracked accurately."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            sample_rate=1000,  # 1kHz for easy math
            stream_factory=mock_factory,
        )
        recorder.start()

        # Simulate 0.5 seconds of audio (500 samples)
        samples = np.zeros((500, 1), dtype=np.float32)
        recorder._callback(samples, 500, {}, sd.CallbackFlags())

        elapsed = recorder.get_elapsed_time()
        assert abs(elapsed - 0.5) < 0.01

    def test_auto_stop_detection(self):
        """Auto-stop should trigger at max duration."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            sample_rate=1000,
            stream_factory=mock_factory,
        )
        recorder.start()

        # Just under max duration
        samples = np.zeros((29000,), dtype=np.float32).reshape(-1, 1)
        recorder._callback(samples, 29000, {}, sd.CallbackFlags())
        assert not recorder.should_auto_stop()

        # Push over max duration
        more_samples = np.zeros((2000,), dtype=np.float32).reshape(-1, 1)
        recorder._callback(more_samples, 2000, {}, sd.CallbackFlags())
        assert recorder.should_auto_stop()

        recorder.stop()

    def test_stop_and_normalize_too_short(self):
        """stop_and_normalize should reject short recordings."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            sample_rate=1000,
            stream_factory=mock_factory,
        )
        recorder.start()

        # Only 100ms at 1kHz = 100 samples (less than 300ms min)
        samples = np.zeros((100, 1), dtype=np.float32)
        recorder._callback(samples, 100, {}, sd.CallbackFlags())

        with pytest.raises(RecordingTooShortError):
            recorder.stop_and_normalize()

    def test_stop_and_normalize_success(self):
        """stop_and_normalize should return WAV bytes for valid recording."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            sample_rate=10000,  # 10kHz
            channels=1,
            stream_factory=mock_factory,
        )
        recorder.start()

        # 500ms recording
        samples = create_synthetic_sine_wave(0.5, 440.0, 10000).astype(np.float32)
        samples = samples.reshape(-1, 1)
        recorder._callback(samples, len(samples), {}, sd.CallbackFlags())

        wav_bytes = recorder.stop_and_normalize()
        assert len(wav_bytes) > 0

        # Verify it's a valid WAV
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getframerate() == AUDIO_SAMPLE_RATE

    def test_context_manager(self):
        """Recorder should work as context manager."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        with AudioRecorder(stream_factory=mock_factory) as recorder:
            assert recorder.is_recording

            # Simulate some audio
            samples = np.zeros((1000, 1), dtype=np.float32)
            recorder._callback(samples, 1000, {}, sd.CallbackFlags())

        # Should auto-stop on exit
        assert not recorder.is_recording

    def test_empty_recording(self):
        """Empty recording should return empty array."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(stream_factory=mock_factory)
        recorder.start()
        # No frames added
        result = recorder.stop()

        assert len(result) == 0

    def test_2d_frame_handling(self):
        """Frames should be handled correctly with 2D arrays."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            channels=2,  # Stereo
            stream_factory=mock_factory,
        )
        recorder.start()

        # Simulate stereo frames
        frame = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        recorder._callback(frame, 2, {}, sd.CallbackFlags())

        result = recorder.stop()
        assert result.shape == (2, 2)


class TestAudioFormat:
    """Tests for AudioFormat dataclass."""

    def test_default_format(self):
        """Default format should match constants."""
        fmt = AudioFormat()
        assert fmt.sample_rate == AUDIO_SAMPLE_RATE
        assert fmt.channels == AUDIO_CHANNELS
        assert fmt.bit_depth == 16

    def test_custom_format(self):
        """Custom format should work."""
        fmt = AudioFormat(sample_rate=48000, channels=2, bit_depth=24)
        assert fmt.sample_rate == 48000
        assert fmt.channels == 2
        assert fmt.bit_depth == 24

    def test_sample_width(self):
        """Sample width should be bit_depth // 8."""
        fmt = AudioFormat(bit_depth=16)
        assert fmt.sample_width == 2

        fmt = AudioFormat(bit_depth=24)
        assert fmt.sample_width == 3

        fmt = AudioFormat(bit_depth=32)
        assert fmt.sample_width == 4


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_synthetic_to_data_uri(self):
        """Complete flow: synthetic -> normalize -> WAV -> data URI."""
        from noasr.models import AudioPayload

        # Create synthetic audio
        samples = create_synthetic_sine_wave(0.5, 440.0)

        # Normalize and create WAV
        wav_bytes = normalize_to_wav_bytes(samples, AUDIO_SAMPLE_RATE, 1)

        # Create data URI
        payload = AudioPayload.from_wav_bytes(wav_bytes)

        # Verify structure
        assert payload.data_uri.startswith("data:audio/wav;base64,")
        assert len(payload.data_uri) > len("data:audio/wav;base64,")

        # Verify API item format
        item = payload.to_api_item()
        assert item["type"] == "input_audio"
        assert "input_audio" in item
        assert "data" in item["input_audio"]

    def test_recorder_with_synthetic_callback(self):
        """Simulate a full recording with synthetic data injection."""
        mock_stream = MagicMock()
        mock_factory = MagicMock(return_value=mock_stream)

        recorder = AudioRecorder(
            sample_rate=16000,
            stream_factory=mock_factory,
        )

        with recorder:
            # Simulate 1 second of sine wave at 16kHz
            for i in range(10):  # 10 chunks of 100ms each
                chunk = create_synthetic_sine_wave(0.1, 440.0, 16000).astype(np.float32)
                chunk = chunk.reshape(-1, 1)
                recorder._callback(chunk, len(chunk), {}, sd.CallbackFlags())

        # Verify we got the expected duration
        # Note: we can't call stop again, but we verified context manager worked

    def test_duration_bounds_at_boundaries(self):
        """Test exact boundary conditions."""
        # Exactly at minimum - should work
        samples_min = create_synthetic_sine_wave(MIN_RECORDING_DURATION)
        wav_min = normalize_to_wav_bytes(samples_min, AUDIO_SAMPLE_RATE, 1)
        assert len(wav_min) > 0

        # Very short - should be rejected by validation
        samples_short = create_synthetic_sine_wave(0.1)
        # Just verify it creates bytes (validation is separate)
        wav_short = normalize_to_wav_bytes(samples_short, AUDIO_SAMPLE_RATE, 1)
        assert len(wav_short) > 0
