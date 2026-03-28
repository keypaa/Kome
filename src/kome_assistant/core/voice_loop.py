from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.integrations.stt import STTEngine
from kome_assistant.integrations.tts import TTSEngine
from kome_assistant.integrations.vad import VADEngine


@dataclass(slots=True)
class VoiceTurnResult:
    user_text: str
    assistant_text: str
    language: str
    synthesized_audio_bytes: bytes


@dataclass(slots=True)
class VoiceLoop:
    vad: VADEngine
    stt: STTEngine
    orchestrator: AssistantOrchestrator
    tts: TTSEngine

    def handle_audio_turn(self, audio_bytes: bytes) -> VoiceTurnResult | None:
        if not self.vad.has_speech(audio_bytes):
            return None

        transcription = self.stt.transcribe(audio_bytes)
        if not transcription.text:
            return None

        assistant_result = self.orchestrator.handle_text_turn(transcription.text)
        tts_result = self.tts.synthesize(
            text=assistant_result.reply_text,
            language=assistant_result.language,
        )

        return VoiceTurnResult(
            user_text=transcription.text,
            assistant_text=assistant_result.reply_text,
            language=assistant_result.language,
            synthesized_audio_bytes=tts_result.audio_bytes,
        )
