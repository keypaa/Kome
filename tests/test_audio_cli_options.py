from kome_assistant.cli import _build_audio_output, _parse_device_arg
from kome_assistant.integrations.audio_output import SimpleAudioOutput, SoundDeviceAudioOutput


def test_parse_device_arg_empty_returns_none() -> None:
    assert _parse_device_arg("") is None
    assert _parse_device_arg("   ") is None


def test_parse_device_arg_int_and_string() -> None:
    assert _parse_device_arg("3") == 3
    assert _parse_device_arg("USB Mic") == "USB Mic"


def test_build_audio_output_auto_prefers_simpleaudio_without_device() -> None:
    output = _build_audio_output(backend="auto", output_device=None)
    assert isinstance(output, SimpleAudioOutput)


def test_build_audio_output_auto_uses_sounddevice_with_device() -> None:
    output = _build_audio_output(backend="auto", output_device=2)
    assert isinstance(output, SoundDeviceAudioOutput)
