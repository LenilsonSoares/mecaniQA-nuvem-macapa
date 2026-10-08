"""HTTP local para a demonstração acadêmica; não possui autenticação de clientes."""

import json
import logging
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event
from urllib.parse import urlsplit

from prometheus_client import CONTENT_TYPE_LATEST

from .application import ReadingProcessor
from .domain import InvalidReading
from .metrics import PrometheusMetrics

LOGGER = logging.getLogger(__name__)
MAX_BODY_BYTES = 4096


def create_server(
    address: tuple[str, int], processor: ReadingProcessor, metrics: PrometheusMetrics, stop: Event
) -> ThreadingHTTPServer:
    class RequestHandler(BaseHTTPRequestHandler):
        # Um cliente que abandona o corpo não pode manter uma thread bloqueada indefinidamente.
        timeout = 5

        def respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            if self.command != "HEAD":
                self.wfile.write(body)

        def respond_json(self, status: int, payload: dict) -> None:
            self.respond(
                status, json.dumps(payload, ensure_ascii=False).encode(), "application/json"
            )

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/health":
                self.respond_json(
                    503 if stop.is_set() else 200, {"status": "UP" if not stop.is_set() else "DOWN"}
                )
            elif path == "/metrics":
                self.respond(200, metrics.render(), CONTENT_TYPE_LATEST)
            elif path == "/":
                self.respond_json(
                    200,
                    {"service": "mecaniqa-iot", "endpoints": ["/health", "/metrics", "/readings"]},
                )
            elif path == "/readings":
                self.method_not_allowed()
            else:
                self.respond_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path in {"/", "/health", "/metrics"}:
                self.method_not_allowed()
                return
            if path != "/readings":
                self.respond_json(404, {"error": "not_found"})
                return
            if self.headers.get_content_type() != "application/json":
                self.respond_json(415, {"error": "Use Content-Type: application/json."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.respond_json(400, {"error": "Content-Length inválido."})
                return
            if length <= 0 or length > MAX_BODY_BYTES:
                self.respond_json(
                    413 if length > MAX_BODY_BYTES else 400,
                    {"error": "Corpo ausente ou excede 4096 bytes."},
                )
                return
            try:
                body = self.rfile.read(length)
                if len(body) != length:
                    self.respond_json(400, {"error": "Corpo incompleto."})
                    return
                payload = json.loads(body)
            except (ValueError, UnicodeDecodeError, TimeoutError):
                self.respond_json(400, {"error": "JSON inválido ou leitura interrompida."})
                return
            try:
                reading = processor.process(payload)
            except InvalidReading as error:
                self.respond_json(422, {"error": str(error)})
                return
            self.respond_json(200, {"status": "success", "reading": asdict(reading)})

        def method_not_allowed(self) -> None:
            allowed = "POST" if urlsplit(self.path).path == "/readings" else "GET"
            self.send_response(405)
            self.send_header("Allow", allowed)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

        do_HEAD = method_not_allowed
        do_PUT = method_not_allowed
        do_DELETE = method_not_allowed
        do_PATCH = method_not_allowed
        do_OPTIONS = method_not_allowed

        def log_message(self, format: str, *args: object) -> None:
            # Probes e scrapes bem-sucedidos não precisam preencher os logs da aplicação.
            if len(args) > 1 and str(args[1]) not in {"200", "304"}:
                LOGGER.info("http method=%s status=%s", self.command, args[1])

    return ThreadingHTTPServer(address, RequestHandler)
