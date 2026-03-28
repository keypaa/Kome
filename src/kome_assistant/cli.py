from __future__ import annotations

import argparse

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine
from kome_assistant.integrations.tts import MockTTSEngine
from kome_assistant.integrations.vad import MockVADEngine
from kome_assistant.tools.registry import default_tool_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Kome local assistant")
    parser.add_argument(
        "--mode",
        choices=("text", "voice-sim"),
        default="text",
        help="Run either text loop or simulated voice loop",
    )
    args = parser.parse_args()

    router = IntentRouter()
    tools = default_tool_registry()
    orchestrator = AssistantOrchestrator(router=router, tools=tools)

    if args.mode == "voice-sim":
        _run_voice_sim_loop(orchestrator)
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


def _run_voice_sim_loop(orchestrator: AssistantOrchestrator) -> None:
    voice_loop = VoiceLoop(
        vad=MockVADEngine(),
        stt=MockSTTEngine(),
        orchestrator=orchestrator,
        tts=MockTTSEngine(),
    )
    print("Kome local assistant (voice-sim mode). Type 'exit' to quit.")
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


if __name__ == "__main__":
    main()
