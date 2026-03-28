from kome_assistant.core.eval_suite import EvalScenario, run_eval_suite
from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine
from kome_assistant.integrations.vad import MockVADEngine
from kome_assistant.tools.registry import default_tool_registry


def test_eval_suite_reports_accuracy_and_latency(tmp_path: Path) -> None:
    orchestrator = AssistantOrchestrator(
        router=IntentRouter(),
        tools=default_tool_registry(data_dir=tmp_path / "data"),
    )
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )

    scenarios = [
        EvalScenario("quelle heure est-il", expected_intent="ask_time", expected_tool="get_time"),
        EvalScenario("mets un minuteur 3", expected_intent="set_timer", expected_tool="set_timer"),
    ]
    summary = run_eval_suite(orchestrator=orchestrator, voice_loop=voice_loop, scenarios=scenarios)
    assert summary.total == 2
    assert summary.intent_ok == 2
    assert summary.tool_ok == 2
    assert summary.completed_turns == 2
    assert summary.p50_total_ms >= 0.0
    assert summary.p95_total_ms >= 0.0
