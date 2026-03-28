from __future__ import annotations


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
        amplitude = sum(abs(byte - 128) for byte in audio_bytes) / len(audio_bytes)
        return amplitude >= self.threshold
