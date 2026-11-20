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
DEFAULT_MAX_CONNECTIONS = 8
DEFAULT_REQUEST_QUEUE_SIZE = 8
DEFAULT_TLS_HANDSHAKE_TIMEOUT = 3.0
DEFAULT_HEADER_TIMEOUT = 2.0
DEFAULT_BODY_TIMEOUT = 5.0
DEFAULT_WRITE_TIMEOUT = 2.0


class IncompleteBodyError(ValueError):
    pass


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server with admission and per-phase socket deadlines."""

    daemon_threads = True
    block_on_close = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler,
        *,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        request_queue_size: int = DEFAULT_REQUEST_QUEUE_SIZE,
        tls_handshake_timeout: float = DEFAULT_TLS_HANDSHAKE_TIMEOUT,
        header_timeout: float = DEFAULT_HEADER_TIMEOUT,
        body_timeout: float = DEFAULT_BODY_TIMEOUT,
        write_timeout: float = DEFAULT_WRITE_TIMEOUT,
    ) -> None:
        count_limits = {
            "max_connections": max_connections,
            "request_queue_size": request_queue_size,
        }
        timeout_limits = {
            "tls_handshake_timeout": tls_handshake_timeout,
            "header_timeout": header_timeout,
            "body_timeout": body_timeout,
            "write_timeout": write_timeout,
        }
        if any(isinstance(value, bool) or not isinstance(value, int) or
               not 1 <= value <= 64 for value in count_limits.values()):
            raise ValueError("server connection limits must be in [1, 64]")
        if any(not math.isfinite(value) or not 0 < value <= 60
               for value in timeout_limits.values()):
            raise ValueError("server timeouts must be finite and in (0, 60]")
        self.request_queue_size = int(request_queue_size)
        self.max_connections = int(max_connections)
        self.tls_handshake_timeout = float(tls_handshake_timeout)
        self.header_timeout = float(header_timeout)
        self.body_timeout = float(body_timeout)
        self.write_timeout = float(write_timeout)
        self._ssl_context = ssl_context
        self._connection_slots = threading.BoundedSemaphore(self.max_connections)
        self._connection_lock = threading.Lock()
        self._active_connections = 0
        self._max_active_connections = 0
        self._rejected_connections = 0
        super().__init__(server_address, request_handler)

    def _prepare_request(self, request: socket.socket) -> socket.socket:
        if self._ssl_context is not None:
            request.settimeout(self.tls_handshake_timeout)
            request = self._ssl_context.wrap_socket(
                request, server_side=True, do_handshake_on_connect=False,
            )
            request.settimeout(self.tls_handshake_timeout)
            request.do_handshake()
        request.settimeout(self.header_timeout)
        return request

    def get_request(self) -> tuple[socket.socket, Any]:
        request, client_address = super().get_request()
        if not self._connection_slots.acquire(blocking=False):
            with self._connection_lock:
                self._rejected_connections += 1
            request.close()
            raise ConnectionAbortedError("position server connection limit reached")
        try:
            request = self._prepare_request(request)
        except BaseException:
            self._connection_slots.release()
            request.close()
            raise
        with self._connection_lock:
            self._active_connections += 1
            self._max_active_connections = max(
                self._max_active_connections, self._active_connections,
            )
        return request, client_address

    def shutdown_request(self, request: socket.socket) -> None:
        try:
            super().shutdown_request(request)
        finally:
            with self._connection_lock:
                self._active_connections -= 1
            self._connection_slots.release()

    def limits_status(self) -> dict[str, int | float]:
        with self._connection_lock:
            return {
                "active_connections": self._active_connections,
                "max_active_connections_observed": self._max_active_connections,
                "rejected_connections": self._rejected_connections,
                "max_connections": self.max_connections,
                "request_queue_size": self.request_queue_size,
                "tls_handshake_timeout": self.tls_handshake_timeout,
                "header_timeout": self.header_timeout,
                "body_timeout": self.body_timeout,
                "write_timeout": self.write_timeout,
            }


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

        def _set_timeout(self, timeout: float) -> None:
            self.connection.settimeout(timeout)

        def _read_exact_body(self, length: int) -> bytes:
            self._set_timeout(float(getattr(self.server, "body_timeout", DEFAULT_BODY_TIMEOUT)))
            body = self.rfile.read(length)
            if len(body) != length:
                raise IncompleteBodyError(
                    f"incomplete request body: expected {length}, received {len(body)}"
                )
            return body

        def _send_error_bounded(self, status: HTTPStatus) -> None:
            self._set_timeout(float(getattr(self.server, "write_timeout", DEFAULT_WRITE_TIMEOUT)))
            try:
                self.send_error(status)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError,
                    ssl.SSLEOFError, socket.timeout):
                self.close_connection = True

        def handle_one_request(self) -> None:
            self._set_timeout(float(getattr(
                self.server, "header_timeout", DEFAULT_HEADER_TIMEOUT,
            )))
            super().handle_one_request()

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in ("/v1/position", "/v1/capture"):
                self._send_error_bounded(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                limit = MAX_BODY_BYTES if self.path == "/v1/position" else MAX_CAPTURE_BODY_BYTES
                if length <= 0 or length > limit:
                    raise ValueError("invalid body length")
                body = self._read_exact_body(length)
                if self.path == "/v1/position":
                    accepted = receiver.accept(self.headers, body, self.path)
                    response_body = {
                        "accepted_seq": accepted,
                        "capture_request": receiver.next_capture_request(),
                    }
                else:
                    response_body = {"capture": receiver.accept_capture(self.headers, body, self.path)}
                response = json.dumps(response_body, separators=(",", ":")).encode()
                self._set_timeout(float(getattr(
                    self.server, "write_timeout", DEFAULT_WRITE_TIMEOUT,
                )))
                self.send_response(HTTPStatus.ACCEPTED)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                try:
                    self.wfile.write(response)
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError,
                        ssl.SSLEOFError, socket.timeout):
                    self.close_connection = True
            except socket.timeout:
                self.close_connection = True
                self._send_error_bounded(HTTPStatus.REQUEST_TIMEOUT)
            except IncompleteBodyError:
                self.close_connection = True
                self._send_error_bounded(HTTPStatus.BAD_REQUEST)
            except (AuthenticationError, ValueError, json.JSONDecodeError):
                self._send_error_bounded(HTTPStatus.UNAUTHORIZED)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def make_https_server(
    bind_host: str,
    port: int,
    receiver: PositionReceiver,
    certificate: str,
    private_key: str,
    *,
    max_connections: int = DEFAULT_MAX_CONNECTIONS,
    request_queue_size: int = DEFAULT_REQUEST_QUEUE_SIZE,
    tls_handshake_timeout: float = DEFAULT_TLS_HANDSHAKE_TIMEOUT,
    header_timeout: float = DEFAULT_HEADER_TIMEOUT,
    body_timeout: float = DEFAULT_BODY_TIMEOUT,
    write_timeout: float = DEFAULT_WRITE_TIMEOUT,
) -> BoundedThreadingHTTPServer:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, private_key)
    return BoundedThreadingHTTPServer(
        (bind_host, port), handler_factory(receiver), ssl_context=context,
        max_connections=max_connections, request_queue_size=request_queue_size,
        tls_handshake_timeout=tls_handshake_timeout, header_timeout=header_timeout,
        body_timeout=body_timeout, write_timeout=write_timeout,
    )
