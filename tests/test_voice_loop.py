from pathlib import Path

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine, MockStreamingSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine
from kome_assistant.integrations.vad import MockVADEngine
from kome_assistant.integrations.wake_word import AudioWakeWordDecision, AudioWakeWordDetector, PhraseWakeWordDetector
from kome_assistant.tools.registry import default_tool_registry


class _AlwaysTriggeredAudioWakeDetector(AudioWakeWordDetector):
    def evaluate_audio(self, wav_audio_bytes: bytes) -> AudioWakeWordDecision:
        del wav_audio_bytes
        return AudioWakeWordDecision(triggered=True, confidence=0.9)


class _NeverTriggeredAudioWakeDetector(AudioWakeWordDetector):
    def evaluate_audio(self, wav_audio_bytes: bytes) -> AudioWakeWordDecision:
        del wav_audio_bytes
        return AudioWakeWordDecision(triggered=False, confidence=0.1)


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
    assert result.synthesized_sample_rate_hz == 16000


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


def test_voice_loop_requires_wake_word_when_configured(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
        wake_word_detector=PhraseWakeWordDetector(["ok kome"]),
    )

    blocked = voice_loop.handle_audio_turn(b"mets un minuteur 2")
    accepted = voice_loop.handle_audio_turn(b"ok kome mets un minuteur 2")

    assert blocked is None
    assert accepted is not None
    assert accepted.user_text == "mets un minuteur 2"


def test_voice_loop_audio_wake_word_blocks_turn(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
        audio_wake_word_detector=_NeverTriggeredAudioWakeDetector(),
    )

    result = voice_loop.handle_audio_turn(b"ok kome mets un minuteur 2")

    assert result is None


def test_voice_loop_audio_wake_word_allows_turn(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
        audio_wake_word_detector=_AlwaysTriggeredAudioWakeDetector(),
    )

    result = voice_loop.handle_audio_turn(b"mets un minuteur 2")

    assert result is not None


def test_streaming_stt_triggers_early_intent(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockStreamingSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )

    first = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"mets un",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )
    second = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"minuteur 3",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )

    assert first.actionable is False
    assert second.actionable is True
    assert second.result is not None
    assert "minuteur" in second.result.user_text.lower()


def test_streaming_stt_waits_for_silence_after_trigger(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockStreamingSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )

    triggered = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"mets un minuteur 2",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )
    blocked = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"quelle heure est-il",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )
    reset = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"   ",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )
    accepted = voice_loop.handle_audio_stream_chunk_with_metrics(
        b"quelle heure est-il",
        min_intent_confidence=0.7,
        min_words=2,
        stability_chunks=1,
    )

    assert triggered.actionable is True
    assert blocked.actionable is False
    assert reset.actionable is False
    assert accepted.actionable is True
