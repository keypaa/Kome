from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.integrations.audio_output import AudioOutput, NullAudioOutput, SimpleAudioOutput, SoundDeviceAudioOutput


@dataclass(slots=True)
class AudioArbitrationPolicy:
    prefer_backend: str = "auto"
    output_device: str | int | None = None


class AudioArbitrator:
    def __init__(self, policy: AudioArbitrationPolicy) -> None:
        self.policy = policy

    def build_output(self) -> AudioOutput:
        if self.policy.prefer_backend == "simpleaudio":
            return SimpleAudioOutput()
        if self.policy.prefer_backend == "sounddevice":
            return SoundDeviceAudioOutput(output_device=self.policy.output_device)

        # auto with fallback preference
        if self.policy.output_device is not None:
            return SoundDeviceAudioOutput(output_device=self.policy.output_device)
        return SimpleAudioOutput()

    def fallback_output(self, current: AudioOutput) -> AudioOutput:
        if isinstance(current, SoundDeviceAudioOutput):
            return SimpleAudioOutput()
        if isinstance(current, SimpleAudioOutput):
            return SoundDeviceAudioOutput(output_device=self.policy.output_device)
        return NullAudioOutput()
