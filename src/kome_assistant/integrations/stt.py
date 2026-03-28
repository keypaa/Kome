from __future__ import annotations


class STTEngine:
    """Placeholder STT adapter.

    Future backend: faster-whisper local runtime.
    """

    def transcribe(self, audio_bytes: bytes) -> str:
        del audio_bytes
        raise NotImplementedError("STT backend not configured yet")
