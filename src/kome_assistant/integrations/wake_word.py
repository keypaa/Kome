from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WakeWordDecision:
    triggered: bool
    text_without_wake_word: str


class WakeWordDetector:
    def evaluate(self, text: str) -> WakeWordDecision:
        del text
        raise NotImplementedError("Wake-word detector not configured")


class PhraseWakeWordDetector(WakeWordDetector):
    """Simple phrase-based wake-word detector for text-transcribed input."""

    def __init__(self, wake_phrases: list[str]) -> None:
        cleaned = [item.strip().lower() for item in wake_phrases if item.strip()]
        if not cleaned:
            raise ValueError("wake_phrases must not be empty")
        self.wake_phrases = cleaned

    def evaluate(self, text: str) -> WakeWordDecision:
        stripped = text.strip()
        low = stripped.lower()
        for phrase in self.wake_phrases:
            if low.startswith(phrase):
                remainder = stripped[len(phrase) :].strip(" ,.:;!?")
                return WakeWordDecision(triggered=True, text_without_wake_word=remainder)
        return WakeWordDecision(triggered=False, text_without_wake_word="")
