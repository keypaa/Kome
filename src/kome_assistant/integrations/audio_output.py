from __future__ import annotations

import wave
from io import BytesIO


class AudioOutput:
    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        del wav_bytes
        raise NotImplementedError("Audio output backend not configured")


class NullAudioOutput(AudioOutput):
    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        del wav_bytes
        return False


class SimpleAudioOutput(AudioOutput):
    """Playback backend based on optional simpleaudio package."""

    def play_wav_bytes(self, wav_bytes: bytes) -> bool:
        if not wav_bytes:
            return False
        try:
            import simpleaudio as sa
        except ImportError:
            return False

        with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        play_obj = sa.play_buffer(frames, channels, sample_width, sample_rate)
        play_obj.wait_done()
        return True
