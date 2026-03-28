from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.integrations.stt import STTEngine, StreamingSTTEngine
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
class StreamingVoiceUpdate:
    partial_text: str
    processed_text: str
    predicted_intent: str | None
    actionable: bool
    result: VoiceTurnResult | None
    metrics: VoiceTurnMetrics | None
    is_final: bool
    audio_wake_confidence: float | None = None


@dataclass(slots=True)
class VoiceLoop:
    vad: VADEngine
    stt: STTEngine
    orchestrator: AssistantOrchestrator
    tts: TTSEngine
    wake_word_detector: WakeWordDetector | None = None
    audio_wake_word_detector: AudioWakeWordDetector | None = None
    _stream_started_at: float | None = field(default=None, init=False, repr=False)
    _stream_vad_ms: float = field(default=0.0, init=False, repr=False)
    _stream_stt_ms: float = field(default=0.0, init=False, repr=False)
    _stream_wait_silence_reset: bool = field(default=False, init=False, repr=False)
    _stream_last_candidate: str = field(default="", init=False, repr=False)
    _stream_candidate_hits: int = field(default=0, init=False, repr=False)
    _stream_audio_wake_open: bool = field(default=False, init=False, repr=False)

    def handle_audio_turn(self, audio_bytes: bytes) -> VoiceTurnResult | None:
        return self.handle_audio_turn_with_metrics(audio_bytes).result

    def reset_stream_state(self) -> None:
        if isinstance(self.stt, StreamingSTTEngine):
            try:
                self.stt.transcribe_stream_chunk(b"", is_final=True)
            except Exception:  # noqa: BLE001
                pass
        self._stream_started_at = None
        self._stream_vad_ms = 0.0
        self._stream_stt_ms = 0.0
        self._stream_wait_silence_reset = False
        self._stream_last_candidate = ""
        self._stream_candidate_hits = 0
        self._stream_audio_wake_open = False

    def supports_streaming_stt(self) -> bool:
        return isinstance(self.stt, StreamingSTTEngine)

    def handle_audio_stream_chunk_with_metrics(
        self,
        audio_bytes: bytes,
        is_final: bool = False,
        min_intent_confidence: float = 0.75,
        min_words: int = 2,
        stability_chunks: int = 2,
    ) -> StreamingVoiceUpdate:
        if not isinstance(self.stt, StreamingSTTEngine):
            outcome = self.handle_audio_turn_with_metrics(audio_bytes)
            return StreamingVoiceUpdate(
                partial_text=outcome.result.user_text if outcome.result is not None else "",
                processed_text=outcome.result.user_text if outcome.result is not None else "",
                predicted_intent=None,
                actionable=outcome.result is not None,
                result=outcome.result,
                metrics=outcome.metrics,
                is_final=True,
                audio_wake_confidence=outcome.metrics.audio_wake_confidence,
            )

        if self._stream_started_at is None:
            self._stream_started_at = perf_counter()

        if self._stream_wait_silence_reset:
            if self.vad.has_speech(audio_bytes):
                return StreamingVoiceUpdate(
                    partial_text="",
                    processed_text="",
                    predicted_intent=None,
                    actionable=False,
                    result=None,
                    metrics=None,
                    is_final=False,
                )
            self.reset_stream_state()
            return StreamingVoiceUpdate(
                partial_text="",
                processed_text="",
                predicted_intent=None,
                actionable=False,
                result=None,
                metrics=None,
                is_final=True,
            )

        start_vad = perf_counter()
        has_speech = self.vad.has_speech(audio_bytes)
        self._stream_vad_ms += (perf_counter() - start_vad) * 1000

        if self.audio_wake_word_detector is not None and has_speech:
            audio_decision = self.audio_wake_word_detector.evaluate_audio(audio_bytes)
            if audio_decision.triggered:
                self._stream_audio_wake_open = True
            audio_wake_confidence = audio_decision.confidence
        else:
            audio_wake_confidence = None

        # No speech chunk: flush pending transcript as final hypothesis.
        if not has_speech:
            is_final = True

        start_stt = perf_counter()
        transcription = self.stt.transcribe_stream_chunk(audio_bytes if has_speech else b"", is_final=is_final)
        self._stream_stt_ms += (perf_counter() - start_stt) * 1000
        partial_text = transcription.text.strip()

        processed_text = partial_text
        if self.wake_word_detector is not None:
            decision = self.wake_word_detector.evaluate(partial_text)
            if not decision.triggered:
                return StreamingVoiceUpdate(
                    partial_text=partial_text,
                    processed_text="",
                    predicted_intent=None,
                    actionable=False,
                    result=None,
                    metrics=None,
                    is_final=is_final,
                    audio_wake_confidence=audio_wake_confidence,
                )
            processed_text = decision.text_without_wake_word.strip()

        if self.audio_wake_word_detector is not None and not self._stream_audio_wake_open:
            return StreamingVoiceUpdate(
                partial_text=partial_text,
                processed_text="",
                predicted_intent=None,
                actionable=False,
                result=None,
                metrics=None,
                is_final=is_final,
                audio_wake_confidence=audio_wake_confidence,
            )

        if not processed_text:
            return StreamingVoiceUpdate(
                partial_text=partial_text,
                processed_text="",
                predicted_intent=None,
                actionable=False,
                result=None,
                metrics=None,
                is_final=is_final,
                audio_wake_confidence=audio_wake_confidence,
            )

        intent = self.orchestrator.router.route(processed_text)
        should_trigger = False

        if processed_text == self._stream_last_candidate:
            self._stream_candidate_hits += 1
        else:
            self._stream_last_candidate = processed_text
            self._stream_candidate_hits = 1

        enough_words = len([word for word in processed_text.split(" ") if word]) >= min_words
        stable_enough = self._stream_candidate_hits >= max(stability_chunks, 1)
        intent_ok = intent.name != "fallback" and intent.confidence >= min_intent_confidence

        if intent_ok and enough_words and (stable_enough or is_final):
            should_trigger = True

        if not should_trigger:
            return StreamingVoiceUpdate(
                partial_text=partial_text,
                processed_text=processed_text,
                predicted_intent=intent.name,
                actionable=False,
                result=None,
                metrics=None,
                is_final=is_final,
                audio_wake_confidence=audio_wake_confidence,
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

        total_ms = 0.0
        if self._stream_started_at is not None:
            total_ms = (perf_counter() - self._stream_started_at) * 1000

        metrics = VoiceTurnMetrics(
            vad_ms=self._stream_vad_ms,
            stt_ms=self._stream_stt_ms,
            orchestration_ms=(end_orchestration - start_orchestration) * 1000,
            tts_ms=(end_tts - start_tts) * 1000,
            total_ms=total_ms,
            audio_wake_confidence=audio_wake_confidence,
        )
        result = VoiceTurnResult(
            user_text=processed_text,
            assistant_text=assistant_result.reply_text,
            language=assistant_result.language,
            synthesized_audio_bytes=tts_result.audio_bytes,
            synthesized_sample_rate_hz=tts_result.sample_rate_hz,
        )

        # After an early trigger, require a silence chunk before accepting another command.
        self._stream_wait_silence_reset = True
        self._stream_last_candidate = ""
        self._stream_candidate_hits = 0

        return StreamingVoiceUpdate(
            partial_text=partial_text,
            processed_text=processed_text,
            predicted_intent=intent.name,
            actionable=True,
            result=result,
            metrics=metrics,
            is_final=is_final,
            audio_wake_confidence=audio_wake_confidence,
        )

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
