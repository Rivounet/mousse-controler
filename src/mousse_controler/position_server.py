"""Bounded HTTPS endpoint receiving outbound-only cursor measurements."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import ssl
import threading
import time
from typing import Any

from .controller import PositionSnapshot, PositionStore
from .geometry import DesktopTopology, Display
from .security import AuthenticationError, HmacVerifier


MAX_BODY_BYTES = 4096


class PositionReceiver:
    def __init__(self, store: PositionStore, verifier: HmacVerifier):
        self.store = store
        self.verifier = verifier
        self._topology: DesktopTopology | None = None
        self._lock = threading.Lock()

    def topology(self) -> DesktopTopology:
        with self._lock:
            if self._topology is None:
                raise ValueError("display topology has not been received")
            return self._topology

    def accept(self, headers: Any, body: bytes, path: str = "/v1/position") -> int:
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("body too large")
        key_id = headers.get("X-Agent-Key", "")
        signature = headers.get("X-Signature", "")
        timestamp_ms = int(headers.get("X-Timestamp", "-1"))
        sequence = int(headers.get("X-Sequence", "-1"))
        self.verifier.verify(key_id, signature, "POST", path, timestamp_ms, sequence, body)
        payload = json.loads(body.decode("utf-8"))
        required = {"x", "y", "session_id", "topology_generation", "observed_at_unix_ms"}
        if not required.issubset(payload):
            raise ValueError("position payload is incomplete")
        observed = int(payload["observed_at_unix_ms"])
        if abs(int(time.time() * 1000) - observed) > 5_000:
            raise ValueError("measurement timestamp outside allowed window")
        if payload.get("session_active") is False:
            raise ValueError("agent session is not interactive")
        displays_payload = payload.get("displays")
        if not isinstance(displays_payload, list) or not displays_payload:
            raise ValueError("display topology is missing")
        displays = tuple(Display(
            int(item["x"]), int(item["y"]), int(item["width"]), int(item["height"])
        ) for item in displays_payload)
        topology = DesktopTopology(displays, str(payload["topology_generation"]))
        self.store.update(PositionSnapshot(
            x=int(payload["x"]),
            y=int(payload["y"]),
            sequence=sequence,
            session_id=int(payload["session_id"]),
            topology_generation=str(payload["topology_generation"]),
            observed_at_unix_ms=observed,
            received_monotonic=time.monotonic(),
        ))
        with self._lock:
            self._topology = topology
        return sequence


def handler_factory(receiver: PositionReceiver):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MoussePosition/1"
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/position":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    raise ValueError("invalid body length")
                body = self.rfile.read(length)
                accepted = receiver.accept(self.headers, body, self.path)
                response = json.dumps({"accepted_seq": accepted}, separators=(",", ":")).encode()
                self.send_response(HTTPStatus.ACCEPTED)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                try:
                    self.wfile.write(response)
                except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError, socket.timeout):
                    self.close_connection = True
            except (AuthenticationError, ValueError, json.JSONDecodeError):
                try:
                    self.send_error(HTTPStatus.UNAUTHORIZED)
                except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError, socket.timeout):
                    self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def make_https_server(
    bind_host: str,
    port: int,
    receiver: PositionReceiver,
    certificate: str,
    private_key: str,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((bind_host, port), handler_factory(receiver))
    server.daemon_threads = True
    server.request_queue_size = 4
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, private_key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
