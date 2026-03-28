from __future__ import annotations

import argparse
from pathlib import Path

from kome_assistant.core.benchmark import run_voice_benchmark
from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.factory import build_voice_backends
from kome_assistant.tools.registry import default_tool_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Kome local assistant")
    parser.add_argument(
        "--mode",
        choices=("text", "voice-sim", "bench"),
        default="text",
        help="Run text loop, simulated voice loop, or local benchmark",
    )
    parser.add_argument(
        "--voice-profile",
        choices=("mock", "local"),
        default="mock",
        help="Select voice backend profile",
    )
    args = parser.parse_args()

    router = IntentRouter()
    tools = default_tool_registry(data_dir=Path("data"))
    orchestrator = AssistantOrchestrator(router=router, tools=tools)

    if args.mode == "voice-sim":
        _run_voice_sim_loop(orchestrator, profile=args.voice_profile)
        return

    if args.mode == "bench":
        _run_benchmark(orchestrator, profile=args.voice_profile)
        return

    print("Kome local assistant (text mode). Type 'exit' to quit.")
    while True:
        user_input = input("you> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("bye")
            break
        result = orchestrator.handle_text_turn(user_input)
        print(f"assistant> {result.reply_text}")


def _run_voice_sim_loop(orchestrator: AssistantOrchestrator, profile: str) -> None:
    backends = build_voice_backends(profile)
    voice_loop = VoiceLoop(vad=backends.vad, stt=backends.stt, orchestrator=orchestrator, tts=backends.tts)
    print(f"Kome local assistant (voice-sim mode, profile={backends.selected_profile}). Type 'exit' to quit.")
    print("Each line is treated as mock audio and sent through VAD -> STT -> assistant -> TTS.")

    while True:
        simulated_audio_text = input("audio> ").strip()
        if simulated_audio_text.lower() in {"exit", "quit"}:
            print("bye")
            break
        result = voice_loop.handle_audio_turn(simulated_audio_text.encode("utf-8"))
        if result is None:
            print("assistant> [no speech detected]")
            continue
        print(f"stt> {result.user_text}")
        print(f"assistant> {result.assistant_text}")
        print(f"tts-bytes> {len(result.synthesized_audio_bytes)}")


def _run_benchmark(orchestrator: AssistantOrchestrator, profile: str) -> None:
    backends = build_voice_backends(profile)
    voice_loop = VoiceLoop(vad=backends.vad, stt=backends.stt, orchestrator=orchestrator, tts=backends.tts)
    utterances = [
        "quelle heure est-il",
        "mets un minuteur 5",
        "allume la lumiere du salon",
        "liste minuteurs",
        "search raspberry pi docs",
    ]
    summary = run_voice_benchmark(voice_loop=voice_loop, utterances=utterances)

    print(f"Benchmark profile: {backends.selected_profile}")
    print(f"Turns: {summary.completed_turns}/{summary.turns}")
    print(f"Avg total: {summary.avg_total_ms:.2f} ms")
    print(f"Avg VAD: {summary.avg_vad_ms:.2f} ms")
    print(f"Avg STT: {summary.avg_stt_ms:.2f} ms")
    print(f"Avg orchestration: {summary.avg_orchestration_ms:.2f} ms")
    print(f"Avg TTS: {summary.avg_tts_ms:.2f} ms")


if __name__ == "__main__":
    main()
