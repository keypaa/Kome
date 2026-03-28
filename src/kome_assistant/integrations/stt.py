from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any


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


class StreamingSTTEngine(STTEngine):
    """Chunk-based streaming STT interface.

    Implementations can return partial hypotheses as chunks arrive and a final
    hypothesis when `is_final=True`.
    """

    def transcribe_stream_chunk(self, audio_bytes: bytes, is_final: bool = False) -> TranscriptionResult:
        del audio_bytes, is_final
        raise NotImplementedError("Streaming STT backend not configured yet")


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


class MockStreamingSTTEngine(MockSTTEngine, StreamingSTTEngine):
    def __init__(self) -> None:
        self._buffer: list[str] = []

    def transcribe_stream_chunk(self, audio_bytes: bytes, is_final: bool = False) -> TranscriptionResult:
        chunk = audio_bytes.decode("utf-8", errors="ignore").strip()
        if chunk:
            self._buffer.append(chunk)
        if not is_final:
            partial = " ".join(self._buffer[-3:]).strip()
            return TranscriptionResult(text=partial, language="fr", confidence=0.5 if partial else 0.0)
        final = " ".join(self._buffer).strip()
        self._buffer.clear()
        if not final:
            return TranscriptionResult(text="", language="fr", confidence=0.0)
        return self.transcribe(final.encode("utf-8"))


class FasterWhisperSTTEngine(STTEngine):
    """Local STT backed by faster-whisper.

    Audio input is expected to be WAV bytes. Model loading is lazy to keep
    startup fast and avoid eager heavyweight initialization.
    """

    def __init__(self, model_size_or_path: str = "small", device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_size_or_path = model_size_or_path
        self.device = device
        self.compute_type = compute_type
        self._model: Any | None = None

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        if not audio_bytes:
            return TranscriptionResult(text="", language="fr", confidence=0.0)

        audio_array = _wav_bytes_to_float32(audio_bytes)
        model = self._load_model()

        segments, info = model.transcribe(
            audio=audio_array,
            beam_size=1,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()

        language = getattr(info, "language", "fr") or "fr"
        probability = float(getattr(info, "language_probability", 0.0) or 0.0)

        return TranscriptionResult(text=text, language=language, confidence=probability)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed") from exc

        self._model = WhisperModel(
            self.model_size_or_path,
            device=self.device,
            compute_type=self.compute_type,
        )
        return self._model


class FasterWhisperStreamingSTTEngine(FasterWhisperSTTEngine, StreamingSTTEngine):
    """Streaming approximation using rolling WAV chunk accumulation.

    This is not true frame-level CTC streaming, but it enables lower-latency
    partial hypotheses in a local-first setup while keeping the same model stack.
    """

    def __init__(
        self,
        model_size_or_path: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        max_chunks: int = 6,
    ) -> None:
        super().__init__(model_size_or_path=model_size_or_path, device=device, compute_type=compute_type)
        self.max_chunks = max_chunks
        self._chunk_buffer: list[bytes] = []

    def transcribe_stream_chunk(self, audio_bytes: bytes, is_final: bool = False) -> TranscriptionResult:
        if audio_bytes:
            self._chunk_buffer.append(audio_bytes)
        if len(self._chunk_buffer) > self.max_chunks:
            self._chunk_buffer = self._chunk_buffer[-self.max_chunks :]

        merged = _merge_wav_chunks(self._chunk_buffer)
        result = self.transcribe(merged)
        if is_final:
            self._chunk_buffer.clear()
        return result


def _merge_wav_chunks(chunks: list[bytes]) -> bytes:
    import wave

    if not chunks:
        return b""

    with wave.open(BytesIO(chunks[0]), "rb") as first:
        channels = first.getnchannels()
        sample_width = first.getsampwidth()
        frame_rate = first.getframerate()

    merged_pcm = bytearray()
    for item in chunks:
        with wave.open(BytesIO(item), "rb") as wav_file:
            merged_pcm.extend(wav_file.readframes(wav_file.getnframes()))

    with BytesIO() as out:
        with wave.open(out, "wb") as wav_out:
            wav_out.setnchannels(channels)
            wav_out.setsampwidth(sample_width)
            wav_out.setframerate(frame_rate)
            wav_out.writeframes(bytes(merged_pcm))
        return out.getvalue()


def _wav_bytes_to_float32(audio_bytes: bytes) -> Any:
    """Decode mono/stereo PCM WAV bytes into float32 waveform expected by whisper."""
    import wave

    with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frame_rate = wav_file.getframerate()
        raw_frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV is supported for faster-whisper adapter")
    if frame_rate <= 0:
        raise ValueError("Invalid WAV sample rate")

    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required for faster-whisper adapter") from exc

    waveform = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        waveform = waveform.reshape(-1, channels).mean(axis=1)
    return waveform
