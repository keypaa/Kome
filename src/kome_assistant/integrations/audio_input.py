from __future__ import annotations

import wave
from io import BytesIO
from typing import Iterator


class AudioInput:
    def capture_wav(self, duration_s: float, sample_rate_hz: int = 16000) -> bytes:
        del duration_s, sample_rate_hz
        raise NotImplementedError("Audio input backend not configured")

    def capture_wav_stream(
        self,
        duration_s: float,
        sample_rate_hz: int = 16000,
        max_turns: int = 0,
    ) -> Iterator[bytes]:
        del duration_s, sample_rate_hz, max_turns
        raise NotImplementedError("Audio input stream backend not configured")


class MicrophoneAudioInput(AudioInput):
    """Microphone capture backend using optional sounddevice package."""

    def __init__(self, channels: int = 1) -> None:
        self.channels = channels

    def capture_wav(self, duration_s: float, sample_rate_hz: int = 16000) -> bytes:
        if duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is required for voice-live mode") from exc

        frames = int(duration_s * sample_rate_hz)
        recording = sd.rec(
            frames,
            samplerate=sample_rate_hz,
            channels=self.channels,
            dtype="int16",
            blocking=True,
        )
        pcm = recording.tobytes()
        return _encode_pcm16_wav(
            pcm_bytes=pcm,
            sample_rate_hz=sample_rate_hz,
            channels=self.channels,
            sample_width_bytes=2,
        )

    def capture_wav_stream(
        self,
        duration_s: float,
        sample_rate_hz: int = 16000,
        max_turns: int = 0,
    ) -> Iterator[bytes]:
        if max_turns < 0:
            raise ValueError("max_turns must be >= 0")
        turns = 0
        while True:
            yield self.capture_wav(duration_s=duration_s, sample_rate_hz=sample_rate_hz)
            turns += 1
            if max_turns and turns >= max_turns:
                break


def _encode_pcm16_wav(
    pcm_bytes: bytes,
    sample_rate_hz: int,
    channels: int,
    sample_width_bytes: int,
) -> bytes:
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width_bytes)
            wav_file.setframerate(sample_rate_hz)
            wav_file.writeframes(pcm_bytes)
        return buffer.getvalue()
