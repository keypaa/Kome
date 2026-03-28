from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from kome_assistant.integrations.stt import FasterWhisperSTTEngine, MockSTTEngine, STTEngine
from kome_assistant.integrations.tts import MockTTSEngine, PiperExternalTTSEngine, TTSEngine
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
    mode = os.getenv("KOME_STT_MODE", "auto").strip().lower()
    if mode == "mock":
        return MockSTTEngine()

    wants_real = mode in {"auto", "faster-whisper", "faster_whisper", "real"}
    if wants_real and importlib.util.find_spec("faster_whisper") is not None:
        model_name = os.getenv("KOME_STT_MODEL", "small")
        device = os.getenv("KOME_STT_DEVICE", "cpu")
        compute_type = os.getenv("KOME_STT_COMPUTE_TYPE", "int8")
        return FasterWhisperSTTEngine(
            model_size_or_path=model_name,
            device=device,
            compute_type=compute_type,
        )

    return MockSTTEngine()


def _build_local_tts_or_mock() -> TTSEngine:
    mode = os.getenv("KOME_TTS_MODE", "auto").strip().lower()
    if mode == "mock":
        return MockTTSEngine()

    wants_real = mode in {"auto", "piper", "piper1-gpl", "real"}
    if wants_real:
        binary_name = os.getenv("KOME_PIPER_BIN", "piper")
        binary_path = shutil.which(binary_name)
        model_path_raw = os.getenv("KOME_PIPER_MODEL", "").strip()
        if binary_path and model_path_raw:
            model_path = Path(model_path_raw)
            if model_path.exists():
                sample_rate = int(os.getenv("KOME_PIPER_SAMPLE_RATE", "22050"))
                return PiperExternalTTSEngine(
                    binary_path=binary_path,
                    model_path=model_path,
                    sample_rate_hz=sample_rate,
                )

    return MockTTSEngine()
