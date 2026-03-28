from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.core.voice_loop import VoiceLoop, VoiceTurnMetrics


@dataclass(slots=True)
class BenchmarkSummary:
    turns: int
    completed_turns: int
    avg_total_ms: float
    avg_vad_ms: float
    avg_stt_ms: float
    avg_orchestration_ms: float
    avg_tts_ms: float


def run_voice_benchmark(voice_loop: VoiceLoop, utterances: list[str]) -> BenchmarkSummary:
    if not utterances:
        raise ValueError("utterances must not be empty")

    metrics: list[VoiceTurnMetrics] = []
    completed_turns = 0
    for utterance in utterances:
        outcome = voice_loop.handle_audio_turn_with_metrics(utterance.encode("utf-8"))
        metrics.append(outcome.metrics)
        if outcome.result is not None:
            completed_turns += 1

    turns = len(metrics)
    return BenchmarkSummary(
        turns=turns,
        completed_turns=completed_turns,
        avg_total_ms=_avg([m.total_ms for m in metrics]),
        avg_vad_ms=_avg([m.vad_ms for m in metrics]),
        avg_stt_ms=_avg([m.stt_ms for m in metrics]),
        avg_orchestration_ms=_avg([m.orchestration_ms for m in metrics]),
        avg_tts_ms=_avg([m.tts_ms for m in metrics]),
    )


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
