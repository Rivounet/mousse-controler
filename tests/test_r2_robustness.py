"""Deterministic R2 qualification without native HOGP, TLS keys, or remote hosts."""

from __future__ import annotations

import http.client
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from mousse_controler.actions import ActionExecutor, ActionRegistry
from mousse_controler.controller import MouseController, PositionStore
from mousse_controler.position_server import (
    BoundedThreadingHTTPServer, PositionReceiver, handler_factory,
)
from mousse_controler.security import HmacVerifier, sign
from mousse_controler.transport import (
    NativeHogpTransport, TransportError, TransportTimeoutError,
)
from tests.r0_doubles import BlockingLineStream, ProcessDouble


TERMINAL = {"EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED"}

ENGINE_SCRIPT = r"""
import pathlib
import sys
import time

mode = sys.argv[1]
log_path = pathlib.Path(sys.argv[2])

def emit(value):
    sys.stdout.write(value + "\n")
    sys.stdout.flush()

if mode == "startup-silent":
    time.sleep(60)
elif mode == "startup-partial":
    sys.stdout.write('{"ok":')
    sys.stdout.flush()
    time.sleep(60)
elif mode == "interrupted":
    raise SystemExit(23)
else:
    if mode == "stderr-saturated":
        for _ in range(4096):
            sys.stderr.write("diagnostic-without-sensitive-data-" + ("x" * 480) + "\n")
        sys.stderr.flush()
    emit('{"event":"prepared","ok":true}')
    for raw in sys.stdin:
        command = raw.strip()
        with log_path.open("a", encoding="utf-8") as log:
            log.write(command + "\n")
        if mode in ("command-silent", "button-silent"):
            time.sleep(60)
        elif mode == "command-partial":
            sys.stdout.write('{"event":"report","ok":')
            sys.stdout.flush()
            time.sleep(60)
        elif mode == "command-exit":
            raise SystemExit(31)
        elif command == "status":
            emit('{"event":"status","ok":true,"detail":"prepared=True,subscribed=True,buttons=0"}')
        elif command == "release":
            emit('{"event":"release","ok":true}')
        elif command == "stop":
            emit('{"event":"stopped","ok":true}')
            break
        else:
            emit('{"event":"report","ok":true}')
"""


class FakeEngineTransport(NativeHogpTransport):
    def __init__(self, mode: str, log_path: Path, **kwargs) -> None:
        super().__init__(Path("fake-engine.exe"), **kwargs)
        self.mode = mode
        self.log_path = log_path

    def _engine_command(self) -> list[str]:
        return [sys.executable, "-u", "-c", ENGINE_SCRIPT, self.mode, str(self.log_path)]


def wait_terminal(registry: ActionRegistry, action_id: str, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = registry.get(action_id)
        if result["state"] in TERMINAL:
            return result
        time.sleep(0.005)
    raise AssertionError(f"action {action_id} did not terminate")


class HogpDeadlineTests(unittest.TestCase):
    def make_transport(self, mode: str, log_path: Path) -> FakeEngineTransport:
        return FakeEngineTransport(
            mode, log_path, startup_timeout=0.3, command_timeout=0.15,
            stop_timeout=0.2, termination_timeout=0.3,
        )

    def test_silent_partial_and_interrupted_startup_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for mode, error in (
                ("startup-silent", TransportTimeoutError),
                ("startup-partial", TransportTimeoutError),
                ("interrupted", TransportError),
            ):
                with self.subTest(mode=mode):
                    transport = self.make_transport(mode, Path(directory) / f"{mode}.log")
                    started = time.monotonic()
                    with self.assertRaises(error):
                        transport.start()
                    self.assertLess(time.monotonic() - started, 1.2)
                    status = transport.recovery_status()
                    self.assertEqual(status["channel_state"], "invalid")
                    self.assertEqual(status["lingering_workers"], 0)

    def test_stderr_is_drained_without_blocking_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self.make_transport(
                "stderr-saturated", Path(directory) / "commands.log")
            transport.start()
            status = transport.status()
            self.assertEqual(status["subscribed"], "True")
            self.assertGreater(
                transport.recovery_status()["stderr_lines_drained"], 1000)
            transport.stop()
            recovered = transport.recovery_status()
            self.assertEqual(recovered["channel_state"], "stopped")
            self.assertEqual(recovered["lingering_workers"], 0)

    def test_command_in_progress_and_concurrent_stops_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "commands.log"
            transport = self.make_transport("command-silent", log_path)
            transport.start()
            command_errors: list[BaseException] = []

            def command() -> None:
                try:
                    transport.move(1, 1)
                except BaseException as exc:
                    command_errors.append(exc)

            command_thread = threading.Thread(target=command)
            command_thread.start()
            deadline = time.monotonic() + 1
            while (not log_path.exists() or "move" not in log_path.read_text(encoding="utf-8")):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)

            stop_errors: list[BaseException] = []

            def stop() -> None:
                try:
                    transport.stop()
                except BaseException as exc:
                    stop_errors.append(exc)

            started = time.monotonic()
            stops = [threading.Thread(target=stop) for _ in range(3)]
            for thread in stops:
                thread.start()
            for thread in stops:
                thread.join(1)
                self.assertFalse(thread.is_alive())
            command_thread.join(1)
            self.assertFalse(command_thread.is_alive())
            self.assertLess(time.monotonic() - started, 1.2)
            self.assertTrue(command_errors)
            self.assertLessEqual(len(stop_errors), 1)
            status = transport.recovery_status()
            self.assertEqual(status["channel_state"], "invalid")
            self.assertEqual(status["lingering_workers"], 0)

    def test_partial_response_and_process_exit_during_command_invalidate_channel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for mode in ("command-partial", "command-exit"):
                with self.subTest(mode=mode):
                    transport = self.make_transport(mode, Path(directory) / f"{mode}.log")
                    transport.start()
                    started = time.monotonic()
                    with self.assertRaises(TransportError):
                        transport.move(1, 1)
                    self.assertLess(time.monotonic() - started, 1)
                    status = transport.recovery_status()
                    self.assertEqual(status["channel_state"], "invalid")
                    self.assertEqual(status["lingering_workers"], 0)

    def test_explicit_restart_recovers_only_after_failed_process_is_gone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self.make_transport(
                "command-silent", Path(directory) / "recovery.log")
            transport.start()
            with self.assertRaises(TransportTimeoutError):
                transport.move(1, 1)
            self.assertEqual(
                transport.recovery_status()["channel_state"], "invalid")
            transport.mode = "normal"
            transport.start()
            self.assertEqual(transport.status()["subscribed"], "True")
            recovered = transport.recovery_status()
            self.assertEqual(recovered["channel_state"], "ready")
            self.assertFalse(recovered["recovery_required"])
            self.assertIsNone(recovered["last_error"])
            transport.stop()

    def test_blocked_command_write_is_bounded_and_invalidates_channel(self) -> None:
        class BlockingWriter:
            def __init__(self) -> None:
                self.entered = threading.Event()
                self.release = threading.Event()

            def write(self, value: str) -> int:
                self.entered.set()
                self.release.wait(1)
                return len(value)

            def flush(self) -> None:
                pass

            def close(self) -> None:
                self.release.set()

        process = ProcessDouble(
            stdout=io.StringIO('{"event":"prepared","ok":true}\n')
        )
        writer = BlockingWriter()
        process.stdin = writer
        transport = NativeHogpTransport(
            Path("fake-engine.exe"), command_timeout=0.03,
            termination_timeout=0.1,
        )
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            transport.start()
        started = time.monotonic()
        with self.assertRaisesRegex(TransportTimeoutError, "write"):
            transport.move(1, 1)
        self.assertTrue(writer.entered.is_set())
        self.assertLess(time.monotonic() - started, 0.4)
        status = transport.recovery_status()
        self.assertEqual(status["channel_state"], "invalid")
        self.assertEqual(status["lingering_workers"], 0)

    def test_button_timeout_is_unknown_quarantined_and_not_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "commands.log"
            journal = root / "actions.jsonl"
            transport = self.make_transport("button-silent", log_path)
            controller = MouseController(transport, PositionStore())
            controller.start()
            registry = ActionRegistry(journal_path=journal)
            executor = ActionExecutor(controller, registry)
            try:
                executor.submit({
                    "kind": "press", "button": "left", "error_policy": "retry",
                    "max_attempts": 3,
                }, action_id="uncertain-native-button")
                result = wait_terminal(registry, "uncertain-native-button")
                self.assertEqual(result["state"], "UNKNOWN")
                deadline = time.monotonic() + 1
                while "safety_stop" not in result["result"]:
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.005)
                    result = registry.get("uncertain-native-button")
                self.assertFalse(result["result"]["safety_stop"]["release_confirmed"])
                self.assertEqual(
                    [line for line in log_path.read_text(encoding="utf-8").splitlines()
                     if line.startswith("buttons ")],
                    ["buttons 1"],
                )
                with self.assertRaisesRegex(RuntimeError, "safety-stopped"):
                    executor.submit({"kind": "wait", "duration_seconds": 0})
            finally:
                executor.close()
            recovered = ActionRegistry(journal_path=journal)
            self.assertEqual(recovered.get("uncertain-native-button")["state"], "UNKNOWN")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                recovered.create("uncertain-native-button", "press")

    def test_failed_process_termination_is_bounded_and_observable(self) -> None:
        class UnkillableProcess(ProcessDouble):
            def terminate(self) -> None:
                self.terminate_calls += 1

            def kill(self) -> None:
                self.kill_calls += 1

            def wait(self, timeout: float | None = None) -> int:
                raise subprocess.TimeoutExpired("fake-engine", timeout)

        stream = BlockingLineStream()
        process = UnkillableProcess(stream)
        transport = NativeHogpTransport(
            Path("fake-engine.exe"), startup_timeout=0.02,
            termination_timeout=0.05,
        )
        started = time.monotonic()
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            with self.assertRaises(TransportTimeoutError):
                transport.start()
        self.assertLess(time.monotonic() - started, 0.3)
        status = transport.recovery_status()
        self.assertTrue(status["termination_failed"])
        self.assertTrue(status["recovery_required"])
        self.assertGreaterEqual(status["lingering_workers"], 1)
        with self.assertRaisesRegex(TransportError, "recovery required"):
            transport.start()
        stream.release.set()


class ReceiverDouble:
    def __init__(self, *, block: bool = False) -> None:
        self.block = block
        self.entered = threading.Event()
        self.release = threading.Event()
        self.bodies: list[bytes] = []
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def accept(self, headers, body: bytes, path: str) -> int:
        with self._lock:
            self.bodies.append(body)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.entered.set()
        if self.block:
            self.release.wait(1)
        with self._lock:
            self.active -= 1
        return 1

    def next_capture_request(self):
        return None


class LanBoundTests(unittest.TestCase):
    def start_server(self, receiver, *, max_connections: int = 2):
        server = BoundedThreadingHTTPServer(
            ("127.0.0.1", 0), handler_factory(receiver),
            max_connections=max_connections, request_queue_size=2,
            header_timeout=0.1, body_timeout=0.1, write_timeout=0.1,
            tls_handshake_timeout=0.1,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def test_server_rejects_unbounded_limit_configuration(self) -> None:
        receiver = ReceiverDouble()
        for kwargs in (
            {"max_connections": 65},
            {"request_queue_size": 0},
            {"body_timeout": float("inf")},
            {"write_timeout": 61},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                BoundedThreadingHTTPServer(
                    ("127.0.0.1", 0), handler_factory(receiver), **kwargs,
                )

    @staticmethod
    def post(server, body: bytes = b"x") -> int:
        connection = http.client.HTTPConnection(*server.server_address, timeout=1)
        try:
            connection.request("POST", "/v1/position", body=body, headers={
                "Content-Length": str(len(body)), "Connection": "close",
            })
            return connection.getresponse().status
        finally:
            connection.close()

    def test_slow_header_and_body_do_not_block_healthy_client(self) -> None:
        receiver = ReceiverDouble()
        server = self.start_server(receiver)
        slow_header = socket.create_connection(server.server_address, timeout=1)
        slow_header.sendall(b"POST /v1/position HTTP/1.1\r\nHost: local")
        time.sleep(0.15)
        slow_header.settimeout(0.5)
        self.assertEqual(slow_header.recv(1), b"")
        slow_header.close()

        slow_body = socket.create_connection(server.server_address, timeout=1)
        slow_body.sendall(
            b"POST /v1/position HTTP/1.1\r\nHost: local\r\n"
            b"Content-Length: 4\r\nConnection: close\r\n\r\nx"
        )
        slow_body.settimeout(1)
        response = slow_body.recv(4096)
        self.assertTrue(not response or b" 408 " in response.split(b"\r\n", 1)[0])
        slow_body.close()
        self.assertEqual(receiver.bodies, [])
        self.assertEqual(self.post(server), 202)

    def test_truncated_and_disconnected_requests_are_rejected_then_recover(self) -> None:
        receiver = ReceiverDouble()
        server = self.start_server(receiver)
        client = socket.create_connection(server.server_address, timeout=1)
        client.sendall(
            b"POST /v1/position HTTP/1.1\r\nHost: local\r\n"
            b"Content-Length: 4\r\nConnection: close\r\n\r\nxy"
        )
        client.shutdown(socket.SHUT_WR)
        response = b""
        while True:
            part = client.recv(4096)
            if not part:
                break
            response += part
        client.close()
        self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
        self.assertEqual(receiver.bodies, [])

        disconnected = socket.create_connection(server.server_address, timeout=1)
        disconnected.sendall(
            b"POST /v1/position HTTP/1.1\r\nHost: local\r\n"
            b"Content-Length: 1\r\nConnection: close\r\n\r\nx"
        )
        disconnected.close()
        time.sleep(0.05)
        self.assertEqual(self.post(server), 202)

    def test_connection_limit_rejects_excess_and_releases_slots(self) -> None:
        receiver = ReceiverDouble(block=True)
        server = self.start_server(receiver, max_connections=2)
        outcomes: list[int] = []

        def post() -> None:
            try:
                outcomes.append(self.post(server))
            except (OSError, http.client.HTTPException):
                outcomes.append(0)

        clients = [threading.Thread(target=post) for _ in range(2)]
        for client in clients:
            client.start()
        deadline = time.monotonic() + 1
        while receiver.max_active < 2:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        excess = threading.Thread(target=post)
        excess.start()
        while server.limits_status()["rejected_connections"] < 1:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        receiver.release.set()
        for client in [*clients, excess]:
            client.join(1)
        self.assertEqual(receiver.max_active, 2)
        self.assertGreaterEqual(server.limits_status()["rejected_connections"], 1)
        self.assertEqual(self.post(server), 202)
        deadline = time.monotonic() + 1
        while server.limits_status()["active_connections"]:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        self.assertEqual(server.limits_status()["active_connections"], 0)

    def test_tls_handshake_timeout_is_applied_before_headers(self) -> None:
        class FakeSocket:
            def __init__(self) -> None:
                self.timeouts: list[float] = []

            def settimeout(self, value: float) -> None:
                self.timeouts.append(value)

            def do_handshake(self) -> None:
                raise socket.timeout("simulated TLS timeout")

            def close(self) -> None:
                pass

        class FakeContext:
            def __init__(self, wrapped: FakeSocket) -> None:
                self.wrapped = wrapped

            def wrap_socket(self, request, **kwargs):
                return self.wrapped

        receiver = ReceiverDouble()
        server = self.start_server(receiver)
        wrapped = FakeSocket()
        server._ssl_context = FakeContext(wrapped)
        with self.assertRaises(socket.timeout):
            server._prepare_request(FakeSocket())
        self.assertEqual(wrapped.timeouts, [0.1])
        server._ssl_context = None
        self.assertEqual(self.post(server), 202)

    def test_hmac_and_replay_protection_are_preserved_through_server(self) -> None:
        secret = b"r2-test-secret"
        now = int(time.time() * 1000)
        body = json.dumps({
            "x": 1, "y": 2, "session_id": 1, "topology_generation": "r2",
            "observed_at_unix_ms": now, "session_active": True,
            "displays": [{"x": 0, "y": 0, "width": 100, "height": 100}],
        }, separators=(",", ":")).encode()
        receiver = PositionReceiver(PositionStore(), HmacVerifier({"agent": secret}))
        server = self.start_server(receiver)
        headers = {
            "Content-Length": str(len(body)), "Connection": "close",
            "X-Agent-Key": "agent", "X-Timestamp": str(now), "X-Sequence": "1",
            "X-Signature": sign(secret, "POST", "/v1/position", now, 1, body),
        }

        def authenticated_post() -> int:
            connection = http.client.HTTPConnection(*server.server_address, timeout=1)
            try:
                connection.request("POST", "/v1/position", body=body, headers=headers)
                return connection.getresponse().status
            finally:
                connection.close()

        self.assertEqual(authenticated_post(), 202)
        self.assertEqual(authenticated_post(), 401)


if __name__ == "__main__":
    unittest.main()
