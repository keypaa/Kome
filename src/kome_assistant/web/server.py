from __future__ import annotations

import base64
import json
from binascii import Error as BinasciiError
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.voice_loop import StreamingVoiceUpdate, VoiceLoop
from kome_assistant.integrations.stt import MockSTTEngine, MockStreamingSTTEngine
from kome_assistant.integrations.wake_word import PhraseWakeWordDetector


@dataclass(slots=True)
class WebUiApp:
    orchestrator: AssistantOrchestrator
    voice_loop: VoiceLoop
    static_dir: Path
    stream_intent_confidence: float
    stream_min_words: int
    stream_stability_chunks: int
    lock: Lock


def run_web_ui_server(
    orchestrator: AssistantOrchestrator,
    voice_loop: VoiceLoop,
    host: str = "127.0.0.1",
    port: int = 8765,
    stream_intent_confidence: float = 0.75,
    stream_min_words: int = 2,
    stream_stability_chunks: int = 2,
) -> None:
    app = WebUiApp(
        orchestrator=orchestrator,
        voice_loop=voice_loop,
        static_dir=Path(__file__).parent / "static",
        stream_intent_confidence=stream_intent_confidence,
        stream_min_words=stream_min_words,
        stream_stability_chunks=stream_stability_chunks,
        lock=Lock(),
    )

    class Handler(BaseHTTPRequestHandler):
        def _write_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_file(self, path: Path, content_type: str) -> None:
            if not path.exists() or not path.is_file():
                self.send_error(404, "Not found")
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route == "/api/health":
                self._write_json(200, {"ok": True})
                return
            if route == "/api/config":
                stt_engine = app.voice_loop.stt
                is_mock_stt = isinstance(stt_engine, (MockSTTEngine, MockStreamingSTTEngine))
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "streaming_stt": app.voice_loop.supports_streaming_stt(),
                        "mock_stt": is_mock_stt,
                        "stt_backend": type(stt_engine).__name__,
                    },
                )
                return
            if route == "/" or route == "/index.html":
                self._write_file(app.static_dir / "index.html", "text/html; charset=utf-8")
                return
            if route == "/app.js":
                self._write_file(app.static_dir / "app.js", "application/javascript; charset=utf-8")
                return
            if route == "/styles.css":
                self._write_file(app.static_dir / "styles.css", "text/css; charset=utf-8")
                return
            if route == "/mic-worklet.js":
                self._write_file(app.static_dir / "mic-worklet.js", "application/javascript; charset=utf-8")
                return
            self.send_error(404, "Not found")

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(content_length) if content_length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._write_json(400, {"ok": False, "error": "Invalid JSON payload"})
                return

            if route == "/api/intent":
                text = str(payload.get("text", "")).strip()
                intent = app.orchestrator.router.route(text)
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "intent": intent.name,
                        "confidence": intent.confidence,
                        "language": intent.language,
                        "slots": intent.slots,
                    },
                )
                return

            if route == "/api/turn":
                text = str(payload.get("text", "")).strip()
                if not text:
                    self._write_json(400, {"ok": False, "error": "text is required"})
                    return
                result = app.orchestrator.handle_text_turn(text)
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "reply": result.reply_text,
                        "language": result.language,
                        "tool": result.used_tool,
                        "timestamp": result.timestamp_utc.isoformat(),
                    },
                )
                return

            if route == "/api/stream/start":
                wake_word = str(payload.get("wake_word", "")).strip()
                wake_aliases = payload.get("wake_aliases", [])
                alias_list = wake_aliases if isinstance(wake_aliases, list) else []
                phrases = [item for item in [wake_word, *[str(x).strip() for x in alias_list]] if item]

                with app.lock:
                    if phrases and isinstance(app.voice_loop.wake_word_detector, PhraseWakeWordDetector):
                        app.voice_loop.wake_word_detector = PhraseWakeWordDetector(phrases)
                    app.voice_loop.reset_stream_state()
                self._write_json(200, {"ok": True})
                return

            if route == "/api/stream/chunk":
                wav_b64 = str(payload.get("wav_base64", "")).strip()
                is_final = bool(payload.get("is_final", False))
                if not wav_b64 and not is_final:
                    self._write_json(400, {"ok": False, "error": "wav_base64 is required"})
                    return
                try:
                    wav_bytes = base64.b64decode(wav_b64) if wav_b64 else b""
                except (BinasciiError, ValueError):
                    self._write_json(400, {"ok": False, "error": "Invalid base64 audio payload"})
                    return

                with app.lock:
                    update = app.voice_loop.handle_audio_stream_chunk_with_metrics(
                        wav_bytes,
                        is_final=is_final,
                        min_intent_confidence=app.stream_intent_confidence,
                        min_words=app.stream_min_words,
                        stability_chunks=app.stream_stability_chunks,
                    )

                self._write_json(200, _stream_update_payload(update))
                return

            if route == "/api/stream/stop":
                with app.lock:
                    update = app.voice_loop.handle_audio_stream_chunk_with_metrics(
                        b"",
                        is_final=True,
                        min_intent_confidence=app.stream_intent_confidence,
                        min_words=app.stream_min_words,
                        stability_chunks=app.stream_stability_chunks,
                    )
                    app.voice_loop.reset_stream_state()
                self._write_json(200, _stream_update_payload(update))
                return

            self._write_json(404, {"ok": False, "error": "Unknown endpoint"})

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            del format, args
            return

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Web UI running on http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()


def _stream_update_payload(update: StreamingVoiceUpdate) -> dict:
    payload: dict = {
        "ok": True,
        "actionable": update.actionable,
        "partial_text": update.partial_text,
        "processed_text": update.processed_text,
        "predicted_intent": update.predicted_intent,
        "is_final": update.is_final,
        "audio_wake_confidence": update.audio_wake_confidence,
    }
    if update.result is not None:
        payload["result"] = {
            "user_text": update.result.user_text,
            "assistant_text": update.result.assistant_text,
            "language": update.result.language,
        }
    if update.metrics is not None:
        payload["metrics"] = {
            "vad_ms": update.metrics.vad_ms,
            "stt_ms": update.metrics.stt_ms,
            "orchestration_ms": update.metrics.orchestration_ms,
            "tts_ms": update.metrics.tts_ms,
            "total_ms": update.metrics.total_ms,
            "audio_wake_confidence": update.metrics.audio_wake_confidence,
        }
    return payload
