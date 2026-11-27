"""Minimal authenticated loopback WebSocket broadcaster for action events."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import queue
import socket
import socketserver
import struct
import time
from typing import Any

from .actions import ActionRegistry


WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_HANDSHAKE_BYTES = 16_384


def _frame(payload: bytes, opcode: int = 0x1) -> bytes:
    if len(payload) <= 125:
        header = bytes((0x80 | opcode, len(payload)))
    elif len(payload) <= 65_535:
        header = bytes((0x80 | opcode, 126)) + struct.pack("!H", len(payload))
    else:
        header = bytes((0x80 | opcode, 127)) + struct.pack("!Q", len(payload))
    return header + payload


class EventWebSocketHandler(socketserver.BaseRequestHandler):
    server: "EventWebSocketServer"

    def handle(self) -> None:
        self.request.settimeout(5.0)
        try:
            raw = self._read_headers()
            request_line, headers = self._parse_headers(raw)
            if request_line != "GET /v1/events HTTP/1.1":
                self._reject(404, "Not Found")
                return
            authorization = headers.get("authorization", "")
            expected = b"Bearer " + self.server.token
            if not hmac.compare_digest(authorization.encode("utf-8"), expected):
                self._reject(401, "Unauthorized")
                return
            if headers.get("upgrade", "").lower() != "websocket" or "upgrade" not in headers.get("connection", "").lower():
                self._reject(400, "Bad Request")
                return
            key = headers.get("sec-websocket-key", "")
            try:
                decoded = base64.b64decode(key, validate=True)
            except ValueError:
                decoded = b""
            if len(decoded) != 16:
                self._reject(400, "Bad Request")
                return
            accept = base64.b64encode(hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode("ascii")
            self.request.sendall(response)
            subscription = self.server.registry.subscribe()
            self.request.settimeout(1.0)
            connected_at = int(time.time() * 1000)
            hello = {
                "event_id": None,
                "event_type": "connected",
                "emitted_at_ms": connected_at,
                "protocol": "mousse.actions.v1",
            }
            self.request.sendall(_frame(json.dumps(hello, separators=(",", ":")).encode("utf-8")))
            last_sent = time.monotonic()
            try:
                while True:
                    try:
                        event = subscription.get(timeout=1.0)
                    except queue.Empty:
                        if time.monotonic() - last_sent < 15:
                            continue
                        self.request.sendall(_frame(b"", opcode=0x9))
                        last_sent = time.monotonic()
                        continue
                    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                    self.request.sendall(_frame(payload))
                    last_sent = time.monotonic()
            finally:
                self.server.registry.unsubscribe(subscription)
        except (ConnectionError, OSError, TimeoutError, UnicodeError, ValueError, RuntimeError):
            return

    def _read_headers(self) -> bytes:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(2048)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            data.extend(chunk)
            if len(data) > MAX_HANDSHAKE_BYTES:
                raise ValueError("WebSocket handshake too large")
        return bytes(data).split(b"\r\n\r\n", 1)[0]

    @staticmethod
    def _parse_headers(raw: bytes) -> tuple[str, dict[str, str]]:
        lines = raw.decode("iso-8859-1").split("\r\n")
        headers: dict[str, str] = {}
        for line in lines[1:]:
            name, separator, value = line.partition(":")
            if not separator:
                raise ValueError("invalid HTTP header")
            headers[name.strip().lower()] = value.strip()
        return lines[0], headers

    def _reject(self, status: int, reason: str) -> None:
        body = reason.encode("ascii")
        self.request.sendall(
            f"HTTP/1.1 {status} {reason}\r\nConnection: close\r\nContent-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        )


class EventWebSocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8

    def __init__(self, address: tuple[str, int], token: bytes | bytearray,
                 registry: ActionRegistry):
        host, _ = address
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise ValueError("event WebSocket must bind to loopback")
        # Keep the runtime-owned mutable token so lifecycle cleanup also
        # invalidates the authentication secret held by this server.
        self.token = token
        self.registry = registry
        super().__init__(address, EventWebSocketHandler)


def make_event_server(port: int, token: bytes | bytearray,
                      registry: ActionRegistry) -> EventWebSocketServer:
    if not 1 <= port <= 65_535:
        raise ValueError("invalid WebSocket port")
    return EventWebSocketServer(("127.0.0.1", port), token, registry)
