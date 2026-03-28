from __future__ import annotations

from typing import Iterator

from kome_assistant.integrations.audio_input import AudioInput


class _FakeAudioInput(AudioInput):
    def __init__(self) -> None:
        self.calls = 0

    def capture_wav(self, duration_s: float, sample_rate_hz: int = 16000) -> bytes:
        del duration_s, sample_rate_hz
        self.calls += 1
        return f"wav-{self.calls}".encode("utf-8")

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


def test_capture_stream_respects_max_turns() -> None:
    audio = _FakeAudioInput()
    chunks = list(audio.capture_wav_stream(duration_s=0.5, max_turns=3))
    assert chunks == [b"wav-1", b"wav-2", b"wav-3"]


def test_capture_stream_rejects_negative_max_turns() -> None:
    audio = _FakeAudioInput()
    try:
        list(audio.capture_wav_stream(duration_s=0.5, max_turns=-1))
        assert False, "expected ValueError"
    except ValueError:
        assert True
