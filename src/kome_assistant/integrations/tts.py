from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SynthesisResult:
    audio_bytes: bytes
    sample_rate_hz: int


class TTSEngine:
    """Placeholder TTS adapter.

    Future backend: Piper local runtime.
    """

    def synthesize(self, text: str, language: str = "fr") -> SynthesisResult:
        del text, language
        raise NotImplementedError("TTS backend not configured yet")


class MockTTSEngine(TTSEngine):
    """Simple local mock TTS that returns encoded text bytes."""

    def synthesize(self, text: str, language: str = "fr") -> SynthesisResult:
        payload = f"[{language}] {text}".encode("utf-8")
        return SynthesisResult(audio_bytes=payload, sample_rate_hz=16000)
