from __future__ import annotations

from dataclasses import dataclass
import wave
from io import BytesIO
from pathlib import Path
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


class SoundDevicePlaybackHandle(PlaybackHandle):
    """Non-blocking playback handle backed by sounddevice global stream state."""

    def __init__(self, sd_module: Any) -> None:
        self._sd = sd_module

    def is_playing(self) -> bool:
        try:
            stream = self._sd.get_stream()
            return bool(stream and stream.active)
        except Exception:  # noqa: BLE001
            return False

    def stop(self) -> None:
        self._sd.stop()

    def wait_done(self) -> None:
        self._sd.wait()


class SoundDeviceAudioOutput(AudioOutput):
    """Playback backend using sounddevice with optional explicit output device."""

    def __init__(self, output_device: str | int | None = None) -> None:
        self.output_device = output_device

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
            import numpy as np
            import sounddevice as sd
        except ImportError:
            return None

        with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        if sample_width != 2:
            raise ValueError("Only 16-bit PCM WAV playback is supported")

        data_i16 = np.frombuffer(frames, dtype=np.int16)
        if channels > 1:
            data_i16 = data_i16.reshape(-1, channels)

        sd.play(data_i16, samplerate=sample_rate, device=self.output_device, blocking=False)
        return SoundDevicePlaybackHandle(sd_module=sd)
