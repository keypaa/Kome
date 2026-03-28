from __future__ import annotations

import argparse
from pathlib import Path

from kome_assistant.core.benchmark import run_voice_benchmark
from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.core.voice_loop import VoiceLoop
from kome_assistant.integrations.audio_input import MicrophoneAudioInput
from kome_assistant.integrations.audio_output import NullAudioOutput, PlaybackHandle, SimpleAudioOutput
from kome_assistant.integrations.factory import build_voice_backends
from kome_assistant.integrations.wake_word import OpenWakeWordAudioDetector, PhraseWakeWordDetector
from kome_assistant.tools.registry import default_tool_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Kome local assistant")
    parser.add_argument(
        "--mode",
        choices=("text", "voice-sim", "voice-live", "bench"),
        default="text",
        help="Run text loop, simulated/live voice loop, or local benchmark",
    )
    parser.add_argument(
        "--voice-profile",
        choices=("mock", "local"),
        default="mock",
        help="Select voice backend profile",
    )
    parser.add_argument(
        "--wake-word",
        default="",
        help="Optional wake word phrase, e.g. 'ok kome'",
    )
    parser.add_argument(
        "--record-seconds",
        type=float,
        default=2.5,
        help="Audio capture length per live turn in seconds",
    )
    parser.add_argument(
        "--live-mode",
        choices=("continuous", "manual"),
        default="continuous",
        help="Continuous loops microphone capture automatically; manual waits for Enter each turn",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=0,
        help="Optional limit for live turns (0 means unlimited)",
    )
    parser.add_argument(
        "--wake-backend",
        choices=("phrase", "openwakeword"),
        default="phrase",
        help="Wake-word backend: phrase gate after STT or openWakeWord audio gate",
    )
    parser.add_argument(
        "--wake-threshold",
        type=float,
        default=0.5,
        help="Confidence threshold for openWakeWord backend",
    )
    parser.add_argument(
        "--openwakeword-model",
        default="",
        help="Optional path to custom openWakeWord model",
    )
    parser.add_argument(
        "--no-barge-in",
        action="store_true",
        help="Disable interrupting TTS playback when user speech is detected",
    )
    parser.add_argument(
        "--no-adaptive-chunk",
        action="store_true",
        help="Disable adaptive chunk sizing in continuous live mode",
    )
    parser.add_argument(
        "--chunk-min-seconds",
        type=float,
        default=1.0,
        help="Lower bound for adaptive chunk size",
    )
    parser.add_argument(
        "--chunk-max-seconds",
        type=float,
        default=4.0,
        help="Upper bound for adaptive chunk size",
    )
    parser.add_argument(
        "--chunk-step-seconds",
        type=float,
        default=0.25,
        help="Step used by adaptive chunk controller",
    )
    args = parser.parse_args()

    router = IntentRouter()
    tools = default_tool_registry(data_dir=Path("data"))
    orchestrator = AssistantOrchestrator(router=router, tools=tools)

    if args.mode == "voice-sim":
        _run_voice_sim_loop(orchestrator, profile=args.voice_profile, wake_word=args.wake_word)
        return

    if args.mode == "voice-live":
        _run_voice_live_loop(
            orchestrator,
            profile=args.voice_profile,
            wake_word=args.wake_word,
            record_seconds=args.record_seconds,
            live_mode=args.live_mode,
            max_turns=args.max_turns,
            wake_backend=args.wake_backend,
            wake_threshold=args.wake_threshold,
            openwakeword_model=args.openwakeword_model,
            enable_barge_in=not args.no_barge_in,
            enable_adaptive_chunk=not args.no_adaptive_chunk,
            chunk_min_seconds=args.chunk_min_seconds,
            chunk_max_seconds=args.chunk_max_seconds,
            chunk_step_seconds=args.chunk_step_seconds,
        )
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


def _build_voice_loop(orchestrator: AssistantOrchestrator, profile: str, wake_word: str) -> VoiceLoop:
    backends = build_voice_backends(profile)
    detector = PhraseWakeWordDetector([wake_word]) if wake_word.strip() else None
    return VoiceLoop(
        vad=backends.vad,
        stt=backends.stt,
        orchestrator=orchestrator,
        tts=backends.tts,
        wake_word_detector=detector,
    )


def _build_voice_loop_with_wake_backend(
    orchestrator: AssistantOrchestrator,
    profile: str,
    wake_word: str,
    wake_backend: str,
    wake_threshold: float,
    openwakeword_model: str,
) -> VoiceLoop:
    backends = build_voice_backends(profile)
    text_detector = PhraseWakeWordDetector([wake_word]) if wake_word.strip() else None
    audio_detector = None

    if wake_word.strip() and wake_backend == "openwakeword":
        model_path = Path(openwakeword_model) if openwakeword_model.strip() else None
        try:
            audio_detector = OpenWakeWordAudioDetector(
                wake_phrases=[wake_word],
                threshold=wake_threshold,
                custom_model_path=model_path,
            )
        except RuntimeError as exc:
            print(f"assistant> openWakeWord unavailable ({exc}), fallback to phrase wake-word")

    return VoiceLoop(
        vad=backends.vad,
        stt=backends.stt,
        orchestrator=orchestrator,
        tts=backends.tts,
        wake_word_detector=text_detector,
        audio_wake_word_detector=audio_detector,
    )


def _run_voice_sim_loop(orchestrator: AssistantOrchestrator, profile: str, wake_word: str) -> None:
    backends = build_voice_backends(profile)
    voice_loop = _build_voice_loop(orchestrator=orchestrator, profile=profile, wake_word=wake_word)
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


def _run_voice_live_loop(
    orchestrator: AssistantOrchestrator,
    profile: str,
    wake_word: str,
    record_seconds: float,
    live_mode: str,
    max_turns: int,
    wake_backend: str,
    wake_threshold: float,
    openwakeword_model: str,
    enable_barge_in: bool,
    enable_adaptive_chunk: bool,
    chunk_min_seconds: float,
    chunk_max_seconds: float,
    chunk_step_seconds: float,
) -> None:
    backends = build_voice_backends(profile)
    voice_loop = _build_voice_loop_with_wake_backend(
        orchestrator=orchestrator,
        profile=profile,
        wake_word=wake_word,
        wake_backend=wake_backend,
        wake_threshold=wake_threshold,
        openwakeword_model=openwakeword_model,
    )
    audio_in = MicrophoneAudioInput(channels=1)
    audio_out = SimpleAudioOutput()

    print(f"Kome local assistant (voice-live mode={live_mode}, profile={backends.selected_profile}).")
    if wake_word.strip():
        print(f"Wake-word required: {wake_word} (backend={wake_backend})")
    if enable_barge_in:
        print("Barge-in: enabled")
    if live_mode == "continuous" and enable_adaptive_chunk:
        print(
            "Adaptive chunk: enabled "
            f"(min={chunk_min_seconds:.2f}s, max={chunk_max_seconds:.2f}s, step={chunk_step_seconds:.2f}s)"
        )

    if live_mode == "manual":
        print("Press Enter to capture one turn, or type 'exit' to quit.")
        turns = 0
        while True:
            action = input("live> ").strip().lower()
            if action in {"exit", "quit"}:
                print("bye")
                break
            actionable, _ = _run_single_live_turn(
                voice_loop,
                audio_in,
                audio_out,
                record_seconds,
                enable_barge_in=enable_barge_in,
            )
            if actionable:
                turns += 1
            if max_turns and turns >= max_turns:
                print("assistant> reached max turns")
                break
        return

    print("Continuous chunk streaming active (Ctrl+C to stop).")
    turns = 0
    current_record_seconds = max(chunk_min_seconds, min(record_seconds, chunk_max_seconds))
    try:
        while True:
            for wav_audio in audio_in.capture_wav_stream(
                duration_s=current_record_seconds,
                sample_rate_hz=16000,
                max_turns=1,
            ):
                actionable, total_ms = _run_single_live_turn(
                    voice_loop,
                    audio_in,
                    audio_out,
                    current_record_seconds,
                    wav_audio=wav_audio,
                    enable_barge_in=enable_barge_in,
                )
                turns += 1
                if enable_adaptive_chunk:
                    next_record_seconds = _next_chunk_size(
                        current=current_record_seconds,
                        min_seconds=chunk_min_seconds,
                        max_seconds=chunk_max_seconds,
                        step_seconds=chunk_step_seconds,
                        actionable=actionable,
                        total_ms=total_ms,
                    )
                    if abs(next_record_seconds - current_record_seconds) > 1e-9:
                        print(
                            f"tuning> chunk {current_record_seconds:.2f}s -> {next_record_seconds:.2f}s"
                        )
                    current_record_seconds = next_record_seconds

                if max_turns and turns >= max_turns:
                    print("assistant> reached max turns")
                    return
    except RuntimeError as exc:
        print(f"assistant> microphone streaming backend unavailable: {exc}")
        print("assistant> install optional audio dependencies and retry")
    except KeyboardInterrupt:
        print("\nbye")


def _run_single_live_turn(
    voice_loop: VoiceLoop,
    audio_in: MicrophoneAudioInput,
    audio_out: SimpleAudioOutput,
    record_seconds: float,
    wav_audio: bytes | None = None,
    enable_barge_in: bool = True,
) -> tuple[bool, float]:
    try:
        wav_audio = wav_audio or audio_in.capture_wav(duration_s=record_seconds, sample_rate_hz=16000)
    except RuntimeError as exc:
        print(f"assistant> microphone backend unavailable: {exc}")
        print("assistant> install optional audio dependencies and retry")
        return False, 0.0

    outcome = voice_loop.handle_audio_turn_with_metrics(wav_audio)
    if outcome.result is None:
        print("assistant> no actionable speech detected")
        print(f"metrics> total={outcome.metrics.total_ms:.2f}ms")
        if outcome.metrics.audio_wake_confidence is not None:
            print(f"wake> confidence={outcome.metrics.audio_wake_confidence:.3f}")
        return False, outcome.metrics.total_ms

    print(f"stt> {outcome.result.user_text}")
    print(f"assistant> {outcome.result.assistant_text}")
    print(f"metrics> total={outcome.metrics.total_ms:.2f}ms")
    if outcome.metrics.audio_wake_confidence is not None:
        print(f"wake> confidence={outcome.metrics.audio_wake_confidence:.3f}")
    played = _play_assistant_audio(
        wav_bytes=outcome.result.synthesized_audio_bytes,
        audio_out=audio_out,
        audio_in=audio_in,
        voice_loop=voice_loop,
        enable_barge_in=enable_barge_in,
    )
    if not played:
        NullAudioOutput().play_wav_bytes(outcome.result.synthesized_audio_bytes)
        print("assistant> audio playback backend unavailable (install simpleaudio)")
    return True, outcome.metrics.total_ms


def _next_chunk_size(
    current: float,
    min_seconds: float,
    max_seconds: float,
    step_seconds: float,
    actionable: bool,
    total_ms: float,
) -> float:
    if step_seconds <= 0:
        return current

    if not actionable:
        return min(max_seconds, current + step_seconds)

    if total_ms > 2500:
        return max(min_seconds, current - step_seconds)

    if total_ms < 1200:
        return max(min_seconds, current - step_seconds / 2.0)

    return current


def _play_assistant_audio(
    wav_bytes: bytes,
    audio_out: SimpleAudioOutput,
    audio_in: MicrophoneAudioInput,
    voice_loop: VoiceLoop,
    enable_barge_in: bool,
) -> bool:
    handle = audio_out.play_wav_bytes_nonblocking(wav_bytes)
    if handle is None:
        return False

    if not enable_barge_in:
        handle.wait_done()
        return True

    return _play_with_barge_in(handle=handle, audio_in=audio_in, voice_loop=voice_loop)


def _play_with_barge_in(
    handle: PlaybackHandle,
    audio_in: MicrophoneAudioInput,
    voice_loop: VoiceLoop,
    monitor_chunk_seconds: float = 0.20,
) -> bool:
    while handle.is_playing():
        try:
            monitor_wav = audio_in.capture_wav(duration_s=monitor_chunk_seconds, sample_rate_hz=16000)
        except RuntimeError:
            # If monitor capture fails, finish playback without barge-in.
            handle.wait_done()
            return True

        if voice_loop.vad.has_speech(monitor_wav):
            handle.stop()
            print("assistant> playback interrupted (barge-in detected)")
            return True

    handle.wait_done()
    return True


def _run_benchmark(orchestrator: AssistantOrchestrator, profile: str) -> None:
    backends = build_voice_backends(profile)
    voice_loop = _build_voice_loop(orchestrator=orchestrator, profile=profile, wake_word="")
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
