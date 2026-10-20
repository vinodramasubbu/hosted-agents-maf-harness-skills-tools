from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore

from azure.core.exceptions import AzureError
from openai import APIError

from test import run_question


LOGGER = logging.getLogger(__name__)
PAGE = Path(__file__).with_name("demo.html")
RUN_LOCK = BoundedSemaphore(1)


class DemoHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict[str, str]) -> None:
        self._send(status, json.dumps(value).encode("utf-8"), "application/json")

    def _local_request(self) -> bool:
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in hosts:
            self._json(403, {"error": "Only localhost requests are allowed."})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{host}" for host in hosts}:
            self._json(403, {"error": "Cross-origin requests are not allowed."})
            return False
        return True

    def do_GET(self) -> None:
        if not self._local_request():
            return
        if self.path == "/":
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/health":
            self._json(200, {"status": "ready"})
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        if not self._local_request():
            return
        if self.path != "/api/ask":
            self._json(404, {"error": "Not found."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Send the question as application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid Content-Length."})
            return
        if not 1 <= length <= 16384:
            self._json(413, {"error": "Request must contain 1-16384 bytes."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "Invalid JSON."})
            return
        question = payload.get("question") if isinstance(payload, dict) else None
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            self._json(400, {"error": "Enter a question containing 1-4000 characters."})
            return
        if not RUN_LOCK.acquire(blocking=False):
            self._json(409, {"error": "An invocation is already running. Try again when it finishes."})
            return
        try:
            output = run_question(question)
        except (AzureError, APIError) as exc:
            error_type = type(exc).__name__
            LOGGER.error("Foundry invocation failed: %s", error_type)
            self._json(502, {
                "error": f"Foundry invocation failed ({error_type}). Check Azure sign-in, agent configuration, and network access.",
            })
        else:
            self._json(200, {"output": output})
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with ThreadingHTTPServer(("127.0.0.1", 8765), DemoHandler) as server:
        print("Open http://127.0.0.1:8765 in your browser. Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
