from kome_assistant.integrations.factory import build_voice_backends
from kome_assistant.integrations.stt import MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine


def test_build_mock_voice_backends() -> None:
    backends = build_voice_backends("mock")
    assert backends.selected_profile == "mock"
    assert isinstance(backends.stt, MockSTTEngine)
    assert isinstance(backends.tts, MockTTSEngine)


def test_build_local_voice_backends_defaults_to_mock_for_stt_tts() -> None:
    backends = build_voice_backends("local")
    assert backends.selected_profile == "local"
    assert isinstance(backends.stt, MockSTTEngine)
    assert isinstance(backends.tts, MockTTSEngine)
