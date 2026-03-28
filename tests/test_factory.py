from pathlib import Path

from kome_assistant.integrations.factory import build_voice_backends
from kome_assistant.integrations.stt import FasterWhisperSTTEngine, MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine, PiperExternalTTSEngine


def test_build_mock_voice_backends() -> None:
    backends = build_voice_backends("mock")
    assert backends.selected_profile == "mock"
    assert isinstance(backends.stt, MockSTTEngine)
    assert isinstance(backends.tts, MockTTSEngine)


def test_build_local_voice_backends_defaults_to_mock_for_stt_tts() -> None:
    backends = build_voice_backends("local")
    assert backends.selected_profile == "local"
    assert isinstance(backends.stt, (MockSTTEngine, FasterWhisperSTTEngine))
    assert isinstance(backends.tts, (MockTTSEngine, PiperExternalTTSEngine))


def test_force_mock_modes(monkeypatch) -> None:
    monkeypatch.setenv("KOME_STT_MODE", "mock")
    monkeypatch.setenv("KOME_TTS_MODE", "mock")
    backends = build_voice_backends("local")
    assert isinstance(backends.stt, MockSTTEngine)
    assert isinstance(backends.tts, MockTTSEngine)


def test_piper_mode_without_model_falls_back_to_mock(monkeypatch) -> None:
    monkeypatch.setenv("KOME_TTS_MODE", "piper1-gpl")
    monkeypatch.delenv("KOME_PIPER_MODEL", raising=False)
    backends = build_voice_backends("local")
    assert isinstance(backends.tts, MockTTSEngine)


def test_piper_mode_with_missing_model_falls_back_to_mock(monkeypatch, tmp_path: Path) -> None:
    missing_model = tmp_path / "missing-model.onnx"
    monkeypatch.setenv("KOME_TTS_MODE", "piper")
    monkeypatch.setenv("KOME_PIPER_MODEL", str(missing_model))
    backends = build_voice_backends("local")
    assert isinstance(backends.tts, MockTTSEngine)
