from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.integrations.stt import STTEngine
from kome_assistant.integrations.tts import TTSEngine
from kome_assistant.integrations.vad import VADEngine
from kome_assistant.integrations.wake_word import AudioWakeWordDetector, WakeWordDetector


@dataclass(slots=True)
class VoiceTurnResult:
    user_text: str
    assistant_text: str
    language: str
    synthesized_audio_bytes: bytes
    synthesized_sample_rate_hz: int


@dataclass(slots=True)
class VoiceTurnMetrics:
    vad_ms: float
    stt_ms: float
    orchestration_ms: float
    tts_ms: float
    total_ms: float
    audio_wake_confidence: float | None = None


@dataclass(slots=True)
class VoiceTurnResultWithMetrics:
    result: VoiceTurnResult | None
    metrics: VoiceTurnMetrics


@dataclass(slots=True)
class VoiceLoop:
    vad: VADEngine
    stt: STTEngine
    orchestrator: AssistantOrchestrator
    tts: TTSEngine
    wake_word_detector: WakeWordDetector | None = None
    audio_wake_word_detector: AudioWakeWordDetector | None = None

    def handle_audio_turn(self, audio_bytes: bytes) -> VoiceTurnResult | None:
        return self.handle_audio_turn_with_metrics(audio_bytes).result

    def handle_audio_turn_with_metrics(self, audio_bytes: bytes) -> VoiceTurnResultWithMetrics:
        start_total = perf_counter()
        audio_wake_confidence: float | None = None

        start_vad = perf_counter()
        if not self.vad.has_speech(audio_bytes):
            end_vad = perf_counter()
            total_ms = (perf_counter() - start_total) * 1000
            return VoiceTurnResultWithMetrics(
                result=None,
                metrics=VoiceTurnMetrics(
                    vad_ms=(end_vad - start_vad) * 1000,
                    stt_ms=0.0,
                    orchestration_ms=0.0,
                    tts_ms=0.0,
                    total_ms=total_ms,
                ),
            )
        end_vad = perf_counter()

        if self.audio_wake_word_detector is not None:
            audio_decision = self.audio_wake_word_detector.evaluate_audio(audio_bytes)
            audio_wake_confidence = audio_decision.confidence
            if not audio_decision.triggered:
                total_ms = (perf_counter() - start_total) * 1000
                return VoiceTurnResultWithMetrics(
                    result=None,
                    metrics=VoiceTurnMetrics(
                        vad_ms=(end_vad - start_vad) * 1000,
                        stt_ms=0.0,
                        orchestration_ms=0.0,
                        tts_ms=0.0,
                        total_ms=total_ms,
                        audio_wake_confidence=audio_wake_confidence,
                    ),
                )

        start_stt = perf_counter()
        transcription = self.stt.transcribe(audio_bytes)
        end_stt = perf_counter()
        if not transcription.text:
            total_ms = (perf_counter() - start_total) * 1000
            return VoiceTurnResultWithMetrics(
                result=None,
                metrics=VoiceTurnMetrics(
                    vad_ms=(end_vad - start_vad) * 1000,
                    stt_ms=(end_stt - start_stt) * 1000,
                    orchestration_ms=0.0,
                    tts_ms=0.0,
                    total_ms=total_ms,
                    audio_wake_confidence=audio_wake_confidence,
                ),
            )

        processed_text = transcription.text
        if self.wake_word_detector is not None:
            decision = self.wake_word_detector.evaluate(transcription.text)
            if not decision.triggered:
                total_ms = (perf_counter() - start_total) * 1000
                return VoiceTurnResultWithMetrics(
                    result=None,
                    metrics=VoiceTurnMetrics(
                        vad_ms=(end_vad - start_vad) * 1000,
                        stt_ms=(end_stt - start_stt) * 1000,
                        orchestration_ms=0.0,
                        tts_ms=0.0,
                        total_ms=total_ms,
                        audio_wake_confidence=audio_wake_confidence,
                    ),
                )
            processed_text = decision.text_without_wake_word
            if not processed_text:
                total_ms = (perf_counter() - start_total) * 1000
                return VoiceTurnResultWithMetrics(
                    result=None,
                    metrics=VoiceTurnMetrics(
                        vad_ms=(end_vad - start_vad) * 1000,
                        stt_ms=(end_stt - start_stt) * 1000,
                        orchestration_ms=0.0,
                        tts_ms=0.0,
                        total_ms=total_ms,
                        audio_wake_confidence=audio_wake_confidence,
                    ),
                )

        start_orchestration = perf_counter()
        assistant_result = self.orchestrator.handle_text_turn(processed_text)
        end_orchestration = perf_counter()

        start_tts = perf_counter()
        tts_result = self.tts.synthesize(
            text=assistant_result.reply_text,
            language=assistant_result.language,
        )
        end_tts = perf_counter()

        total_ms = (perf_counter() - start_total) * 1000
        return VoiceTurnResultWithMetrics(
            result=VoiceTurnResult(
                user_text=processed_text,
                assistant_text=assistant_result.reply_text,
                language=assistant_result.language,
                synthesized_audio_bytes=tts_result.audio_bytes,
                synthesized_sample_rate_hz=tts_result.sample_rate_hz,
            ),
            metrics=VoiceTurnMetrics(
                vad_ms=(end_vad - start_vad) * 1000,
                stt_ms=(end_stt - start_stt) * 1000,
                orchestration_ms=(end_orchestration - start_orchestration) * 1000,
                tts_ms=(end_tts - start_tts) * 1000,
                total_ms=total_ms,
                audio_wake_confidence=audio_wake_confidence,
            ),
        )
