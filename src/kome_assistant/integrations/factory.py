from __future__ import annotations

import os
from dataclasses import dataclass

from kome_assistant.integrations.stt import MockSTTEngine, STTEngine
from kome_assistant.integrations.tts import MockTTSEngine, TTSEngine
from kome_assistant.integrations.vad import EnergyVADEngine, MockVADEngine, VADEngine


@dataclass(slots=True)
class VoiceBackends:
    vad: VADEngine
    stt: STTEngine
    tts: TTSEngine
    selected_profile: str


def build_voice_backends(profile: str = "mock") -> VoiceBackends:
    selected = profile.lower()
    if selected == "mock":
        return VoiceBackends(
            vad=MockVADEngine(),
            stt=MockSTTEngine(),
            tts=MockTTSEngine(),
            selected_profile="mock",
        )

    if selected == "local":
        # Keep this local-only and dependency-safe: if optional real backends are
        # not configured yet, we still run with deterministic mocks.
        stt = _build_local_stt_or_mock()
        tts = _build_local_tts_or_mock()
        return VoiceBackends(
            vad=EnergyVADEngine(),
            stt=stt,
            tts=tts,
            selected_profile="local",
        )

    raise ValueError(f"Unknown voice backend profile: {profile}")


def _build_local_stt_or_mock() -> STTEngine:
    mode = os.getenv("KOME_STT_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockSTTEngine()
    # Placeholder for future real local backend registration.
    return MockSTTEngine()


def _build_local_tts_or_mock() -> TTSEngine:
    mode = os.getenv("KOME_TTS_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockTTSEngine()
    # Placeholder for future real local backend registration.
    return MockTTSEngine()
