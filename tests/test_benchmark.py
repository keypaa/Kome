from pathlib import Path

from kome_assistant.core.benchmark import run_voice_benchmark
from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine
from kome_assistant.integrations.vad import MockVADEngine
from kome_assistant.tools.registry import default_tool_registry


def test_voice_benchmark_returns_summary(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(router=IntentRouter(), tools=default_tool_registry(data_dir=tmp_path))
    voice_loop = VoiceLoop(vad=MockVADEngine(), stt=MockSTTEngine(), orchestrator=orchestrator, tts=MockTTSEngine())
    summary = run_voice_benchmark(
        voice_loop=voice_loop,
        utterances=["quelle heure est-il", "mets un minuteur 2"],
    )

    assert summary.turns == 2
    assert summary.completed_turns == 2
    assert summary.avg_total_ms >= 0
