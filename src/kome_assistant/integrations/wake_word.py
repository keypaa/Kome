from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AudioWakeWordDecision:
    triggered: bool
    confidence: float


@dataclass(slots=True)
class WakeWordDecision:
    triggered: bool
    text_without_wake_word: str


class WakeWordDetector:
    def evaluate(self, text: str) -> WakeWordDecision:
        del text
        raise NotImplementedError("Wake-word detector not configured")


class AudioWakeWordDetector:
    def evaluate_audio(self, wav_audio_bytes: bytes) -> AudioWakeWordDecision:
        del wav_audio_bytes
        raise NotImplementedError("Audio wake-word detector not configured")


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


class OpenWakeWordAudioDetector(AudioWakeWordDetector):
    """Optional audio wake-word detector powered by openWakeWord.

    If openwakeword is unavailable, construction raises RuntimeError so callers
    can safely fall back to phrase-only detection.
    """

    def __init__(
        self,
        wake_phrases: list[str],
        threshold: float = 0.5,
        custom_model_path: Path | None = None,
    ) -> None:
        if not wake_phrases:
            raise ValueError("wake_phrases must not be empty")
        self.wake_phrases = [item.strip().lower() for item in wake_phrases if item.strip()]
        self.threshold = threshold
        self.custom_model_path = custom_model_path
        self._model: Any | None = None

    def evaluate_audio(self, wav_audio_bytes: bytes) -> AudioWakeWordDecision:
        model = self._load_model()
        pcm_i16 = _decode_wav_to_mono_i16(wav_audio_bytes)
        # openWakeWord is typically chunked at 80ms (1280 samples at 16kHz).
        chunk_size = 1280
        best_confidence = 0.0
        for start in range(0, len(pcm_i16), chunk_size):
            chunk = pcm_i16[start : start + chunk_size]
            if len(chunk) == 0:
                continue
            scores = model.predict(chunk)
            if isinstance(scores, dict):
                for key, value in scores.items():
                    key_low = str(key).lower()
                    if any(phrase in key_low for phrase in self.wake_phrases):
                        best_confidence = max(best_confidence, float(value))
        return AudioWakeWordDecision(triggered=best_confidence >= self.threshold, confidence=best_confidence)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise RuntimeError("openwakeword is not installed") from exc

        if self.custom_model_path is not None:
            self._model = Model(wakeword_models=[str(self.custom_model_path)])
        else:
            self._model = Model()
        return self._model


def _decode_wav_to_mono_i16(wav_audio_bytes: bytes) -> Any:
    import wave

    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required for openwakeword adapter") from exc

    with wave.open(BytesIO(wav_audio_bytes), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        raw_frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV is supported for openwakeword adapter")

    waveform = np.frombuffer(raw_frames, dtype=np.int16)
    if channels > 1:
        waveform = waveform.reshape(-1, channels).mean(axis=1).astype(np.int16)
    return waveform
