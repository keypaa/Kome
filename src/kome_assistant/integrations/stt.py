from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    language: str
    confidence: float


class STTEngine:
    """Placeholder STT adapter.

    Future backend: faster-whisper local runtime.
    """

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        del audio_bytes
        raise NotImplementedError("STT backend not configured yet")


class MockSTTEngine(STTEngine):
    """Simple local mock STT for voice-loop integration testing.

    It treats incoming audio bytes as UTF-8 text, which lets us run the whole
    voice path without microphone or model dependencies.
    """

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        text = audio_bytes.decode("utf-8", errors="ignore").strip()
        if not text:
            return TranscriptionResult(text="", language="fr", confidence=0.0)

        language = "fr"
        low = text.lower()
        if any(token in low for token in ["what", "time", "turn", "light", "search"]):
            language = "en"
        return TranscriptionResult(text=text, language=language, confidence=0.8)
