"""Bounded HTTPS endpoint receiving outbound-only cursor measurements."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import deque
import json
import math
import socket
import ssl
import threading
import time
from typing import Any

from .controller import PositionSnapshot, PositionStore
from .geometry import DesktopTopology, Display
from .security import AuthenticationError, HmacVerifier


MAX_BODY_BYTES = 4096
MAX_CAPTURE_BODY_BYTES = 24 * 1024 * 1024


class PositionReceiver:
    def __init__(self, store: PositionStore, verifier: HmacVerifier, capture_broker: Any | None = None):
        self.store = store
        self.verifier = verifier
        self.capture_broker = capture_broker
        self._topology: DesktopTopology | None = None
        self._lock = threading.Lock()
        self._last_received_monotonic: float | None = None
        self._interarrival_ms: deque[float] = deque(maxlen=2048)
        self._transit_ms: deque[float] = deque(maxlen=2048)
        self._hmac_ms: deque[float] = deque(maxlen=2048)
        self._processing_ms: deque[float] = deque(maxlen=2048)
        self._cursor_read_us: deque[float] = deque(maxlen=2048)

    @staticmethod
    def _summary(values: deque[float]) -> dict[str, float | int | None]:
        if not values:
            return {"count": 0, "median": None, "p95": None, "max": None}
        ordered = sorted(values)
        return {
            "count": len(ordered),
            "median": round(ordered[len(ordered) // 2], 3),
            "p95": round(ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)], 3),
            "max": round(ordered[-1], 3),
        }

    def metrics(self) -> dict[str, dict[str, float | int | None]]:
        with self._lock:
            return {
                "sample_interval_ms": self._summary(self._interarrival_ms),
                "observed_to_receiver_ms": self._summary(self._transit_ms),
                "hmac_verify_ms": self._summary(self._hmac_ms),
                "receiver_processing_ms": self._summary(self._processing_ms),
                "cursor_read_us": self._summary(self._cursor_read_us),
            }

    def topology(self) -> DesktopTopology:
        with self._lock:
            if self._topology is None:
                raise ValueError("display topology has not been received")
            return self._topology

    def accept(self, headers: Any, body: bytes, path: str = "/v1/position") -> int:
        processing_started = time.perf_counter()
        received_wall_ms = int(time.time() * 1000)
        received_monotonic = time.monotonic()
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("body too large")
        key_id = headers.get("X-Agent-Key", "")
        signature = headers.get("X-Signature", "")
        timestamp_ms = int(headers.get("X-Timestamp", "-1"))
        sequence = int(headers.get("X-Sequence", "-1"))
        hmac_started = time.perf_counter()
        self.verifier.verify(key_id, signature, "POST", path, timestamp_ms, sequence, body)
        hmac_ms = (time.perf_counter() - hmac_started) * 1000.0
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
            received_monotonic=received_monotonic,
        ))
        with self._lock:
            self._topology = topology
            if self._last_received_monotonic is not None:
                self._interarrival_ms.append((received_monotonic - self._last_received_monotonic) * 1000.0)
            self._last_received_monotonic = received_monotonic
            self._transit_ms.append(float(received_wall_ms - observed))
            self._hmac_ms.append(hmac_ms)
            self._processing_ms.append((time.perf_counter() - processing_started) * 1000.0)
            if "cursor_read_us" in payload:
                self._cursor_read_us.append(float(payload["cursor_read_us"]))
        return sequence

    def next_capture_request(self) -> dict[str, Any] | None:
        if self.capture_broker is None:
            return None
        return self.capture_broker.next_request()

    def accept_capture(self, headers: Any, body: bytes, path: str = "/v1/capture") -> dict[str, Any]:
        if self.capture_broker is None:
            raise ValueError("capture receiver is disabled")
        if len(body) > MAX_CAPTURE_BODY_BYTES:
            raise ValueError("capture body too large")
        key_id = headers.get("X-Agent-Key", "")
        signature = headers.get("X-Signature", "")
        timestamp_ms = int(headers.get("X-Timestamp", "-1"))
        sequence = int(headers.get("X-Sequence", "-1"))
        self.verifier.verify(key_id, signature, "POST", path, timestamp_ms, sequence, body)
        return self.capture_broker.accept_upload(body)


def handler_factory(receiver: PositionReceiver):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MoussePosition/1"
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in ("/v1/position", "/v1/capture"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                limit = MAX_BODY_BYTES if self.path == "/v1/position" else MAX_CAPTURE_BODY_BYTES
                if length <= 0 or length > limit:
                    raise ValueError("invalid body length")
                body = self.rfile.read(length)
                if self.path == "/v1/position":
                    accepted = receiver.accept(self.headers, body, self.path)
                    response_body = {
                        "accepted_seq": accepted,
                        "capture_request": receiver.next_capture_request(),
                    }
                else:
                    response_body = {"capture": receiver.accept_capture(self.headers, body, self.path)}
                response = json.dumps(response_body, separators=(",", ":")).encode()
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
