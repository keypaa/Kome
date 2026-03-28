from io import BytesIO
import wave

from kome_assistant.integrations.stt import MockSTTEngine, MockStreamingSTTEngine


def _build_silent_wav(sample_rate: int = 16000, seconds: float = 0.1) -> bytes:
    frames = int(sample_rate * seconds)
    pcm = b"\x00\x00" * frames
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm)
        return buffer.getvalue()


def test_mock_stt_ignores_binary_wav_payload() -> None:
    engine = MockSTTEngine()
    result = engine.transcribe(_build_silent_wav())
    assert result.text == ""
    assert result.confidence == 0.0


def test_mock_streaming_stt_ignores_binary_wav_payload() -> None:
    engine = MockStreamingSTTEngine()
    partial = engine.transcribe_stream_chunk(_build_silent_wav(), is_final=False)
    final = engine.transcribe_stream_chunk(_build_silent_wav(), is_final=True)
    assert partial.text == ""
    assert final.text == ""
