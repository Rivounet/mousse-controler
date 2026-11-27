from __future__ import annotations

import base64
from http.client import HTTPConnection
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest

from mousse_controler.app import (
    RuntimeFactories,
    build_runtime,
    register_runtime_servers,
)
from mousse_controler.command_server import make_command_server
from mousse_controler.event_server import EventWebSocketServer
from mousse_controler.position_server import BoundedThreadingHTTPServer, handler_factory
from mousse_controler.security import sign
from mousse_controler.transport import SimulatedHidTransport


AGENT_SECRET = b"hermetic-agent-secret"
COMMAND_TOKEN = b"hermetic-command-token"


class HermeticTransport(SimulatedHidTransport):
    """Real controller boundary with no operating-system HID effects."""

    def __init__(self, executable: Path, **limits: float) -> None:
        super().__init__()
        self.executable = executable
        self.limits = limits
        self.advertised = False

    def advertise(self) -> None:
        self._ready()
        self.advertised = True
        self.events.append(("advertise",))


def _plain_position_server(
    bind_host: str,
    port: int,
    receiver,
    certificate: str,
    private_key: str,
    **limits,
) -> BoundedThreadingHTTPServer:
    del certificate, private_key
    return BoundedThreadingHTTPServer(
        (bind_host, port), handler_factory(receiver), **limits,
    )


def _ephemeral_event_server(
    port: int, token: bytes, registry,
) -> EventWebSocketServer:
    del port
    return EventWebSocketServer(("127.0.0.1", 0), token, registry)


class _WebSocketReader:
    def __init__(self, connection: socket.socket) -> None:
        self.connection = connection
        self.buffer = bytearray()

    def _fill(self, size: int) -> None:
        while len(self.buffer) < size:
            chunk = self.connection.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket closed before a complete frame")
            self.buffer.extend(chunk)

    def handshake(self, port: int) -> None:
        key = base64.b64encode(b"0123456789abcdef").decode("ascii")
        request = (
            "GET /v1/events HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Bearer {COMMAND_TOKEN.decode('ascii')}\r\n\r\n"
        ).encode("ascii")
        self.connection.sendall(request)
        marker = b"\r\n\r\n"
        while marker not in self.buffer:
            self._fill(len(self.buffer) + 1)
        headers, remainder = bytes(self.buffer).split(marker, 1)
        self.buffer[:] = remainder
        if not headers.startswith(b"HTTP/1.1 101 "):
            raise AssertionError(headers.decode("ascii", errors="replace"))

    def json_frame(self) -> dict[str, object]:
        self._fill(2)
        first, second = self.buffer[0], self.buffer[1]
        del self.buffer[:2]
        if first & 0x0F != 0x1 or second & 0x80:
            raise AssertionError("expected an unmasked text frame")
        length = second & 0x7F
        if length == 126:
            self._fill(2)
            length = int.from_bytes(self.buffer[:2], "big")
            del self.buffer[:2]
        elif length == 127:
            self._fill(8)
            length = int.from_bytes(self.buffer[:8], "big")
            del self.buffer[:8]
        self._fill(length)
        payload = bytes(self.buffer[:length])
        del self.buffer[:length]
        return json.loads(payload.decode("utf-8"))


class RuntimeCompositionSystemTests(unittest.TestCase):
    @staticmethod
    def _server(runtime, name: str):
        return next(
            entry["server"] for entry in runtime.lifecycle.servers
            if entry["name"] == name
        )

    @staticmethod
    def _post(
        port: int,
        path: str,
        body: bytes,
        headers: dict[str, str],
    ) -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    @staticmethod
    def _command(port: int, command_id: str, command: str,
                 arguments: dict[str, object]) -> tuple[int, dict[str, object]]:
        body = json.dumps({
            "command_id": command_id,
            "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 5_000,
            "command": command,
            "arguments": arguments,
        }, separators=(",", ":")).encode("utf-8")
        status, response = RuntimeCompositionSystemTests._post(
            port,
            "/v1/command",
            body,
            {
                "Authorization": f"Bearer {COMMAND_TOKEN.decode('ascii')}",
                "Content-Type": "application/json",
            },
        )
        return status, json.loads(response.decode("utf-8"))

    def test_real_composition_connects_position_command_and_event_protocols(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(json.dumps({
                "agent_keys_dpapi": {"system-agent": "agent-secret"},
                "command_token_dpapi": "command-token",
                "hogp_executable": "unused-hermetic-engine.exe",
                "position_bind": "127.0.0.1",
                "position_port": 0,
                "command_port": 0,
                "event_port": 0,
                "tls_certificate": "unused-test-certificate",
                "tls_private_key": "unused-test-key",
                "capture_directory": str(root / "captures"),
                "action_journal": str(root / "action-journal.jsonl"),
            }), encoding="utf-8")

            secrets = {
                "agent-secret": AGENT_SECRET,
                "command-token": COMMAND_TOKEN,
            }
            factories = RuntimeFactories(
                unprotect_secret=secrets.__getitem__,
                transport=HermeticTransport,
                position_server=_plain_position_server,
                command_server=make_command_server,
                event_server=_ephemeral_event_server,
            )
            runtime = build_runtime(config_path, factories=factories)
            websocket: socket.socket | None = None
            cleanup_errors = []
            try:
                runtime.controller.start()
                runtime.transport.advertise()
                register_runtime_servers(runtime)
                for name in ("position-https", "command-loopback", "events-websocket"):
                    runtime.lifecycle.start_server(name)

                position_port = self._server(
                    runtime, "position-https",
                ).server_address[1]
                command_port = self._server(
                    runtime, "command-loopback",
                ).server_address[1]
                event_port = self._server(
                    runtime, "events-websocket",
                ).server_address[1]

                observed_at = int(time.time() * 1000)
                position_body = json.dumps({
                    "x": 41,
                    "y": 73,
                    "session_id": 1,
                    "session_active": True,
                    "topology_generation": "system-topology",
                    "observed_at_unix_ms": observed_at,
                    "displays": [{"x": 0, "y": 0, "width": 1920, "height": 1080}],
                }, separators=(",", ":")).encode("utf-8")
                signature = sign(
                    AGENT_SECRET, "POST", "/v1/position", observed_at, 1, position_body,
                )
                status, response = self._post(
                    position_port,
                    "/v1/position",
                    position_body,
                    {
                        "X-Agent-Key": "system-agent",
                        "X-Signature": signature,
                        "X-Timestamp": str(observed_at),
                        "X-Sequence": "1",
                        "Content-Type": "application/json",
                    },
                )
                self.assertEqual(status, 202)
                self.assertEqual(json.loads(response)["accepted_seq"], 1)

                unauthorized_body = b'{}'
                status, _ = self._post(
                    command_port,
                    "/v1/command",
                    unauthorized_body,
                    {"Content-Type": "application/json"},
                )
                self.assertEqual(status, 401)

                status, result = self._command(
                    command_port, "system-position", "position_status", {},
                )
                self.assertEqual(status, 200)
                self.assertEqual(result["position"]["x"], 41)
                self.assertEqual(result["position"]["y"], 73)

                websocket = socket.create_connection(
                    ("127.0.0.1", event_port), timeout=2,
                )
                reader = _WebSocketReader(websocket)
                reader.handshake(event_port)
                self.assertEqual(reader.json_frame()["event_type"], "connected")

                status, result = self._command(
                    command_port,
                    "system-action-submit",
                    "action_submit",
                    {
                        "action_id": "system-wait",
                        "action": {"kind": "wait", "duration_seconds": 0.01},
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(result["action"]["action_id"], "system-wait")

                states = []
                deadline = time.monotonic() + 2
                while "EXECUTED" not in states:
                    if time.monotonic() >= deadline:
                        self.fail(f"action did not complete; observed states: {states}")
                    websocket.settimeout(max(0.01, deadline - time.monotonic()))
                    event = reader.json_frame()
                    action = event.get("action")
                    if isinstance(action, dict) and action.get("action_id") == "system-wait":
                        states.append(action["state"])
                self.assertIn("ACCEPTED", states)
                self.assertIn("RUNNING", states)
                self.assertEqual(states[-1], "EXECUTED")
            finally:
                if websocket is not None:
                    websocket.close()
                cleanup_errors = runtime.lifecycle.close()

            self.assertEqual(cleanup_errors, [])
            self.assertTrue(runtime.transport.advertised)
            self.assertFalse(runtime.transport.started)
            self.assertFalse(any(runtime.lifecycle.command_token))
            self.assertTrue(all(
                not any(secret) for secret in runtime.lifecycle.keys.values()
            ))
            self.assertFalse(any(
                event[0] in {"move", "buttons", "scroll"}
                for event in runtime.transport.events
            ))


if __name__ == "__main__":
    unittest.main()
