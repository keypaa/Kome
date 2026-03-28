from __future__ import annotations

from dataclasses import dataclass
import wave
from io import BytesIO
from typing import Any


class PlaybackHandle:
    def is_playing(self) -> bool:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def wait_done(self) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class NullPlaybackHandle(PlaybackHandle):
    def is_playing(self) -> bool:
        return False

    def stop(self) -> None:
        return None

    def wait_done(self) -> None:
        return None


@dataclass(slots=True)
class SimpleAudioPlaybackHandle(PlaybackHandle):
    play_object: Any

    def is_playing(self) -> bool:
        return bool(self.play_object.is_playing())

    def stop(self) -> None:
        self.play_object.stop()

    def wait_done(self) -> None:
        self.play_object.wait_done()


class AudioOutput:
    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        del wav_bytes
        raise NotImplementedError("Audio output backend not configured")

    def play_wav_bytes_nonblocking(self, wav_bytes: bytes) -> PlaybackHandle | None:
        del wav_bytes
        raise NotImplementedError("Non-blocking audio output backend not configured")


class NullAudioOutput(AudioOutput):
    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        del wav_bytes
        return False

    def play_wav_bytes_nonblocking(self, wav_bytes: bytes) -> PlaybackHandle | None:
        del wav_bytes
        return NullPlaybackHandle()


class SimpleAudioOutput(AudioOutput):
    """Playback backend based on optional simpleaudio package."""

    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        handle = self.play_wav_bytes_nonblocking(wav_bytes)
        if handle is None:
            return False
        handle.wait_done()
        return True

    def play_wav_bytes_nonblocking(self, wav_bytes: bytes) -> PlaybackHandle | None:
        if not wav_bytes:
            return None
        try:
            import simpleaudio as sa
        except ImportError:
            return None

        with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        play_obj = sa.play_buffer(frames, channels, sample_width, sample_rate)
        return SimpleAudioPlaybackHandle(play_object=play_obj)
