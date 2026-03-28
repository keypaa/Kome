from __future__ import annotations


class TTSEngine:
    """Placeholder TTS adapter.

    Future backend: Piper local runtime.
    """

    def synthesize(self, text: str, language: str = "fr") -> bytes:
        del text, language
        raise NotImplementedError("TTS backend not configured yet")
