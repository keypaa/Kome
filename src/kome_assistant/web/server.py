from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from kome_assistant.core.orchestrator import AssistantOrchestrator


@dataclass(slots=True)
class WebUiApp:
    orchestrator: AssistantOrchestrator
    static_dir: Path


def run_web_ui_server(orchestrator: AssistantOrchestrator, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = WebUiApp(orchestrator=orchestrator, static_dir=Path(__file__).parent / "static")

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
            if route == "/" or route == "/index.html":
                self._write_file(app.static_dir / "index.html", "text/html; charset=utf-8")
                return
            if route == "/app.js":
                self._write_file(app.static_dir / "app.js", "application/javascript; charset=utf-8")
                return
            if route == "/styles.css":
                self._write_file(app.static_dir / "styles.css", "text/css; charset=utf-8")
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
