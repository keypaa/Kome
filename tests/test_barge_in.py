from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.cli import _play_with_barge_in
from kome_assistant.integrations.audio_output import PlaybackHandle


@dataclass(slots=True)
class _FakePlaybackHandle(PlaybackHandle):
    remaining_steps: int
    stopped: bool = False

    def is_playing(self) -> bool:
        if self.stopped:
            return False
        if self.remaining_steps <= 0:
            return False
        self.remaining_steps -= 1
        return True

    def stop(self) -> None:
        self.stopped = True

    def wait_done(self) -> None:
        return None


class _FakeAudioInput:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.calls = 0

    def capture_wav(self, duration_s: float, sample_rate_hz: int = 16000) -> bytes:
        del duration_s, sample_rate_hz
        self.calls += 1
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeVAD:
    def __init__(self, should_trigger_on: bytes) -> None:
        self.should_trigger_on = should_trigger_on

    def has_speech(self, audio_bytes: bytes) -> bool:
        return audio_bytes == self.should_trigger_on


@dataclass(slots=True)
class _FakeVoiceLoop:
    vad: _FakeVAD


def test_barge_in_interrupts_playback() -> None:
    handle = _FakePlaybackHandle(remaining_steps=5)
    audio_in = _FakeAudioInput(chunks=[b"silence", b"speech"])
    voice_loop = _FakeVoiceLoop(vad=_FakeVAD(should_trigger_on=b"speech"))

    result = _play_with_barge_in(handle=handle, audio_in=audio_in, voice_loop=voice_loop)

    assert result is True
    assert handle.stopped is True


def test_barge_in_does_not_interrupt_without_speech() -> None:
    handle = _FakePlaybackHandle(remaining_steps=2)
    audio_in = _FakeAudioInput(chunks=[b"silence", b"silence"])
    voice_loop = _FakeVoiceLoop(vad=_FakeVAD(should_trigger_on=b"speech"))

    result = _play_with_barge_in(handle=handle, audio_in=audio_in, voice_loop=voice_loop)

    assert result is True
    assert handle.stopped is False
