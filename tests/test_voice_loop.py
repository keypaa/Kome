from pathlib import Path

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine
from kome_assistant.integrations.vad import MockVADEngine
from kome_assistant.tools.registry import default_tool_registry


def test_voice_loop_handles_timer_request(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )

    result = voice_loop.handle_audio_turn(b"mets un minuteur 4")

    assert result is not None
    assert result.user_text == "mets un minuteur 4"
    assert "Minuteur defini" in result.assistant_text
    assert result.synthesized_audio_bytes


def test_voice_loop_returns_none_without_speech(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )

    result = voice_loop.handle_audio_turn(b"   ")

    assert result is None
