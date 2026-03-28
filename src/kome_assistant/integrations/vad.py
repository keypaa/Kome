from __future__ import annotations

import wave
from io import BytesIO


class VADEngine:
    """Voice activity detector interface."""

    def has_speech(self, audio_bytes: bytes) -> bool:
        del audio_bytes
        raise NotImplementedError("VAD backend not configured yet")


class MockVADEngine(VADEngine):
    """Lightweight heuristic VAD for integration tests and CLI simulation."""

    def has_speech(self, audio_bytes: bytes) -> bool:
        # Non-empty frame is considered as speech for mock mode.
        return bool(audio_bytes and audio_bytes.strip())


class EnergyVADEngine(VADEngine):
    """Dependency-free VAD approximation based on average byte amplitude."""

    def __init__(self, threshold: int = 4) -> None:
        self.threshold = threshold

    def has_speech(self, audio_bytes: bytes) -> bool:
        if not audio_bytes:
            return False
        payload = _extract_pcm_payload(audio_bytes)
        amplitude = sum(abs(byte - 128) for byte in payload) / len(payload)
        return amplitude >= self.threshold


def _extract_pcm_payload(audio_bytes: bytes) -> bytes:
    if audio_bytes.startswith(b"RIFF"):
        try:
            with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
                return wav_file.readframes(wav_file.getnframes())
        except Exception:  # noqa: BLE001
            return audio_bytes
    return audio_bytes
