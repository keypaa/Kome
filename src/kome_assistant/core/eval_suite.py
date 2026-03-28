from __future__ import annotations

import math
from dataclasses import dataclass

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.voice_loop import VoiceLoop


@dataclass(slots=True)
class EvalScenario:
    utterance: str
    expected_intent: str
    expected_tool: str | None


@dataclass(slots=True)
class EvalSummary:
    total: int
    intent_ok: int
    tool_ok: int
    completed_turns: int
    p50_total_ms: float
    p95_total_ms: float


def default_fr_eval_scenarios() -> list[EvalScenario]:
    return [
        EvalScenario("quelle heure est-il", "ask_time", "get_time"),
        EvalScenario("mets un minuteur de 5", "set_timer", "set_timer"),
        EvalScenario("allume la lumiere du salon", "toggle_light", "toggle_light"),
        EvalScenario("cherche docs raspberry pi", "search_docs", "search_docs"),
        EvalScenario("liste minuteurs", "list_timers", "list_timers"),
    ]


def run_eval_suite(
    orchestrator: AssistantOrchestrator,
    voice_loop: VoiceLoop,
    scenarios: list[EvalScenario],
) -> EvalSummary:
    if not scenarios:
        return EvalSummary(0, 0, 0, 0, 0.0, 0.0)

    intent_ok = 0
    tool_ok = 0
    completed = 0
    totals: list[float] = []

    for scenario in scenarios:
        intent = orchestrator.router.route(scenario.utterance)
        if intent.name == scenario.expected_intent:
            intent_ok += 1

        outcome = voice_loop.handle_audio_turn_with_metrics(scenario.utterance.encode("utf-8"))
        totals.append(outcome.metrics.total_ms)

        if outcome.result is None:
            continue
        completed += 1

        turn = orchestrator.handle_text_turn(scenario.utterance)
        if turn.used_tool == scenario.expected_tool:
            tool_ok += 1

    totals.sort()
    return EvalSummary(
        total=len(scenarios),
        intent_ok=intent_ok,
        tool_ok=tool_ok,
        completed_turns=completed,
        p50_total_ms=_percentile(totals, 0.50),
        p95_total_ms=_percentile(totals, 0.95),
    )


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[index]
