from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import NamedTemporaryFile


@dataclass(slots=True)
class SynthesisResult:
    audio_bytes: bytes
    sample_rate_hz: int


class TTSEngine:
    """Placeholder TTS adapter.

    Future backend: Piper local runtime.
    """

    def synthesize(self, text: str, language: str = "fr") -> SynthesisResult:
        del text, language
        raise NotImplementedError("TTS backend not configured yet")


class MockTTSEngine(TTSEngine):
    """Simple local mock TTS that returns encoded text bytes."""

    def synthesize(self, text: str, language: str = "fr") -> SynthesisResult:
        payload = f"[{language}] {text}".encode("utf-8")
        return SynthesisResult(audio_bytes=payload, sample_rate_hz=16000)


class PiperExternalTTSEngine(TTSEngine):
    """TTS adapter that calls a local piper binary (including Piper1-GPL builds)."""

    def __init__(self, binary_path: str, model_path: Path, sample_rate_hz: int = 22050) -> None:
        self.binary_path = binary_path
        self.model_path = model_path
        self.sample_rate_hz = sample_rate_hz

    def synthesize(self, text: str, language: str = "fr") -> SynthesisResult:
        del language
        if not text.strip():
            return SynthesisResult(audio_bytes=b"", sample_rate_hz=self.sample_rate_hz)

        with NamedTemporaryFile(suffix=".wav", delete=True) as out_file:
            cmd = [
                self.binary_path,
                "--model",
                str(self.model_path),
                "--output_file",
                out_file.name,
            ]
            completed: CompletedProcess[str] = run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                raise RuntimeError(f"Piper process failed: {stderr}")
            audio_bytes = Path(out_file.name).read_bytes()

        return SynthesisResult(audio_bytes=audio_bytes, sample_rate_hz=self.sample_rate_hz)
