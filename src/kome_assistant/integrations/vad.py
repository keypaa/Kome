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
