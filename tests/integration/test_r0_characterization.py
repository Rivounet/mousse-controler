"""R0 characterization: records current robustness behaviour without fixing it.

Every double in this module is process-local.  The suite never opens Bluetooth,
never sends a native HID report, never captures a screen, and never contacts the
target Windows host.  Tests named ``current_defect`` deliberately pass when the
known baseline defect is reproduced; the qualification matrix gives the future
contract and owning correction lot.
"""

from __future__ import annotations

import base64
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from http.server import ThreadingHTTPServer
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

from mousse_controler import app
from mousse_controler.actions import ActionExecutor, ActionRegistry
from mousse_controler.capture import CaptureBroker
from mousse_controler.command_server import CommandGateway
from mousse_controler.controller import MouseController, PositionStore
from mousse_controler.position_server import BoundedThreadingHTTPServer, handler_factory
from mousse_controler.transport import (
    NativeHogpTransport, SimulatedHidTransport, TransportError,
    TransportTimeoutError,
)

from tests.support.r0_doubles import (
    ActionsDouble,
    BlockingLineStream,
    FailingAfterEffectTransport,
    ProcessDouble,
    SaturatingStderr,
    ControllerStopDouble,
    SequenceDouble,
)
from tests.support.waiting import wait_until


TERMINAL = {"EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED"}
PNG = b"\x89PNG\r\n\x1a\n" + b"r0-characterization"
ROOT = Path(__file__).resolve().parents[2]


def wait_for_record(registry: ActionRegistry, action_id: str, timeout: float = 1.0) -> dict:
    def terminal() -> dict | None:
        record = registry.get(action_id)
        return record if record["state"] in TERMINAL else None

    return wait_until(
        terminal,
        timeout=timeout,
        description=f"action {action_id} terminal state",
    )


class TransportCharacterizationTests(unittest.TestCase):
    def test_T01_alive_silent_engine_honours_startup_timeout(self):
        stream = BlockingLineStream()
        process = ProcessDouble(stream)
        transport = NativeHogpTransport(
            Path("engine.exe"), startup_timeout=0.02, termination_timeout=0.1,
        )
        started = time.monotonic()
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(TransportTimeoutError, "startup timed out"):
                transport.start()
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(transport.recovery_status()["channel_state"], "invalid")
        self.assertGreaterEqual(process.terminate_calls, 1)

    def test_T02_incomplete_engine_response_fails_closed(self):
        process = ProcessDouble(io.StringIO('{"ok":\n'))
        transport = NativeHogpTransport(Path("engine.exe"), termination_timeout=0.1)
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(TransportError, "invalid HOGP engine response"):
                transport.start()
        self.assertEqual(transport.recovery_status()["channel_state"], "invalid")

    def test_T03_interrupted_engine_reports_exit_code(self):
        process = ProcessDouble(io.StringIO(""), return_code=23)
        transport = NativeHogpTransport(Path("engine.exe"), termination_timeout=0.1)
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(TransportError, "exit=23"):
                transport.start()

    def test_T04_saturated_stderr_is_drained_and_forced_stop_is_observable(self):
        stdout = io.StringIO('{"ok":true,"event":"prepared"}\n')
        stderr = SaturatingStderr()
        process = ProcessDouble(stdout, stderr=stderr)
        transport = NativeHogpTransport(
            Path("engine.exe"), command_timeout=0.02, termination_timeout=0.1,
        )
        with mock.patch("mousse_controler.transport.subprocess.Popen", return_value=process):
            transport.start()
        self.assertTrue(stderr.finished.wait(0.5))
        self.assertGreaterEqual(stderr.read_calls, 2)
        transport.stop()
        status = transport.recovery_status()
        self.assertEqual(status["channel_state"], "stopped")
        self.assertEqual(status["last_stop_outcome"], "forced")
        self.assertFalse(status["recovery_required"])


class ActionCharacterizationTests(unittest.TestCase):
    def make_executor(self, transport=None):
        transport = transport or SimulatedHidTransport()
        controller = MouseController(transport, PositionStore())
        controller.start()
        registry = ActionRegistry()
        return transport, controller, registry, ActionExecutor(controller, registry)

    def test_A01_ambiguous_press_continue_enters_safety_stop(self):
        transport, controller, registry, executor = self.make_executor(
            FailingAfterEffectTransport("buttons"))
        try:
            accepted = executor.submit({
                "kind": "press", "button": "left", "error_policy": "continue",
            })
            result = wait_for_record(registry, accepted["action_id"])
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertTrue(controller.is_stopped())
            self.assertEqual(controller.buttons_mask(), 0)
            self.assertEqual(transport.buttons_mask, 0)
            self.assertFalse(result["result"]["safety_stop"]["release_confirmed"])
            with self.assertRaisesRegex(RuntimeError, "safety-stopped"):
                executor.submit({"kind": "wait", "duration_seconds": 0})
        finally:
            executor.close()

    def test_A02_uncertain_non_idempotent_move_is_not_replayed(self):
        transport, _controller, registry, executor = self.make_executor(
            FailingAfterEffectTransport("move"))
        try:
            accepted = executor.submit({
                "kind": "move_relative", "dx": 2, "dy": 3,
                "error_policy": "retry", "max_attempts": 3,
            })
            result = wait_for_record(registry, accepted["action_id"])
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(len([event for event in transport.events if event[0] == "move"]), 1)
        finally:
            executor.close()

    def test_A03_emergency_stop_releases_suspended_wait(self):
        transport, controller, registry, executor = self.make_executor()
        try:
            accepted = executor.submit({"kind": "wait", "duration_seconds": 5})
            wait_until(
                lambda: registry.get(accepted["action_id"])["state"] == "RUNNING",
                description="paused action start",
            )
            executor.pause(accepted["action_id"])
            executor.emergency_stop()
            self.assertEqual(wait_for_record(registry, accepted["action_id"])["state"], "CANCELLED")
            self.assertTrue(controller.is_stopped())
            stop_index = transport.events.index(("stop",))
            self.assertFalse(any(event[0] in {"move", "buttons", "scroll"}
                                 for event in transport.events[stop_index + 1:]))
        finally:
            executor.close()

    def test_A04_close_cancels_queued_action(self):
        _transport, _controller, registry, executor = self.make_executor()
        first = executor.submit({"kind": "wait", "duration_seconds": 5}, action_id="running")
        wait_until(
            lambda: registry.get(first["action_id"])["state"] == "RUNNING",
            description="running action start",
        )
        executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="queued")
        executor.close()
        self.assertEqual(registry.get("running")["state"], "CANCELLED")
        self.assertEqual(registry.get("queued")["state"], "CANCELLED")
        self.assertEqual(registry.get("queued")["error_code"], "EXECUTOR_CLOSED")

    def test_A05_global_stop_coordinates_both_engines(self):
        actions = ActionsDouble()
        controller = ControllerStopDouble()
        gateway = CommandGateway(b"token", controller, object(), object(), actions)
        sequence = SequenceDouble()
        gateway._sequence = sequence
        gateway.execute({
            "command_id": "stop-r0", "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000, "command": "stop", "arguments": {},
        })
        self.assertEqual(actions.request_stop_calls, 1)
        self.assertEqual(sequence.stop_calls, 1)
        self.assertEqual(controller.emergency_stop_calls, 1)


class ReceiverDouble:
    def __init__(self, *, block: bool = False) -> None:
        self.bodies: list[bytes] = []
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.block = block

    def accept(self, headers, body: bytes, path: str) -> int:
        with self.lock:
            self.bodies.append(body)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.entered.set()
        if self.block:
            self.release.wait(2)
        with self.lock:
            self.active -= 1
        return 1

    def next_capture_request(self):
        return None


class NetworkCharacterizationTests(unittest.TestCase):
    def start_server(self, receiver: ReceiverDouble):
        server = BoundedThreadingHTTPServer(
            ("127.0.0.1", 0), handler_factory(receiver), max_connections=2,
            header_timeout=0.1, body_timeout=0.1, write_timeout=0.1,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def test_N01_slow_client_is_bounded_and_healthy_client_recovers(self):
        receiver = ReceiverDouble()
        server = self.start_server(receiver)
        client = socket.create_connection(server.server_address, timeout=1)
        self.addCleanup(client.close)
        client.sendall(
            b"POST /v1/position HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 10\r\nConnection: close\r\n\r\nx"
        )
        client.settimeout(1)
        response = client.recv(4096)
        self.assertTrue(not response or b" 408 " in response.split(b"\r\n", 1)[0])
        self.assertEqual(receiver.bodies, [])
        connection = http.client.HTTPConnection(*server.server_address, timeout=1)
        connection.request("POST", "/v1/position", body=b"x",
                           headers={"Content-Length": "1", "Connection": "close"})
        self.assertEqual(connection.getresponse().status, 202)
        connection.close()

    def test_N02_incomplete_body_is_rejected_before_receiver(self):
        receiver = ReceiverDouble()
        server = self.start_server(receiver)
        client = socket.create_connection(server.server_address, timeout=1)
        client.sendall(
            b"POST /v1/position HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 10\r\nConnection: close\r\n\r\nabc"
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

    def test_N03_connection_limit_is_enforced_and_recovers(self):
        receiver = ReceiverDouble(block=True)
        server = self.start_server(receiver)
        outcomes: list[int] = []

        def post() -> None:
            connection = http.client.HTTPConnection(*server.server_address, timeout=2)
            try:
                connection.request("POST", "/v1/position", body=b"x",
                                   headers={"Content-Length": "1", "Connection": "close"})
                outcomes.append(connection.getresponse().status)
            except (OSError, http.client.HTTPException):
                outcomes.append(0)
            finally:
                connection.close()

        clients = [threading.Thread(target=post) for _ in range(2)]
        for client in clients:
            client.start()
        wait_until(
            lambda: receiver.max_active >= 2,
            description="characterized connection saturation",
        )
        excess = threading.Thread(target=post)
        excess.start()
        wait_until(
            lambda: server.limits_status()["rejected_connections"] >= 1,
            description="characterized excess connection rejection",
        )
        receiver.release.set()
        for client in [*clients, excess]:
            client.join(2)
        self.assertLessEqual(receiver.max_active, 2)
        self.assertGreaterEqual(server.limits_status()["rejected_connections"], 1)
        connection = http.client.HTTPConnection(*server.server_address, timeout=1)
        connection.request("POST", "/v1/position", body=b"x",
                           headers={"Content-Length": "1", "Connection": "close"})
        self.assertEqual(connection.getresponse().status, 202)
        connection.close()


class StorageCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def begin_request(self, broker: CaptureBroker, timeout: float = 1.0):
        outcome: dict[str, object] = {}

        def request() -> None:
            try:
                outcome["result"] = broker.request_capture("r0-action", "after", timeout=timeout)
            except Exception as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=request)
        thread.start()
        queued = wait_until(
            broker.next_request,
            description="characterized capture request delivery",
        )
        return thread, outcome, queued

    @staticmethod
    def upload(request: dict) -> bytes:
        return json.dumps({
            "capture_id": request["capture_id"], "action_id": request["action_id"],
            "moment": request["moment"], "state": "CAPTURED",
            "captured_at_ms": int(time.time() * 1000), "cursor": {"x": 1, "y": 1},
            "monitor": {"x": 0, "y": 0, "width": 10, "height": 10, "primary": True},
            "image_base64": base64.b64encode(PNG).decode("ascii"),
        }).encode()

    def test_S01_quota_pressure_retains_undeletable_file_as_error(self):
        broker = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                               max_total_bytes=4096)
        thread, _outcome, request = self.begin_request(broker)
        used = broker.quota_status()["used_bytes"]
        broker._max_total_bytes = used + len(PNG)
        with self.assertRaisesRegex(RuntimeError, "quota admission denied"):
            broker.accept_upload(self.upload(request))
        thread.join(1)
        self.assertEqual(broker.get(request["capture_id"])["state"], "FAILED")
        self.assertFalse((Path(self.temporary.name) / f"{request['capture_id']}.png").exists())
        status = broker.quota_status()
        self.assertLessEqual(status["used_bytes"], status["max_total_bytes"])

    def test_S02_delete_denied_survives_restart_and_can_be_retried(self):
        broker = CaptureBroker(Path(self.temporary.name), max_bytes=1024, max_total_bytes=4096)
        thread, _outcome, request = self.begin_request(broker)
        stored = broker.accept_upload(self.upload(request))
        thread.join(1)
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            failed = broker.delete(request["capture_id"])
        restarted = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                  max_total_bytes=4096)
        retained = restarted.get(request["capture_id"])
        self.assertEqual((failed["state"], retained["state"]),
                         ("DELETE_FAILED", "DELETE_FAILED"))
        self.assertTrue(Path(stored["storage_path"]).is_file())
        self.assertEqual(restarted.delete(request["capture_id"])["state"], "DELETED")

    def test_S03_restart_marks_incomplete_capture_failed(self):
        broker = CaptureBroker(Path(self.temporary.name), max_bytes=1024, max_total_bytes=4096)
        thread, _outcome, request = self.begin_request(broker, timeout=0.15)
        restarted = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                  max_total_bytes=4096)
        recovered = restarted.get(request["capture_id"])
        thread.join(1)
        self.assertEqual(recovered["state"], "FAILED")
        self.assertIn("restart", recovered["error"])


class FakeServer:
    def __init__(self, *, shutdown_error: bool = False) -> None:
        self.shutdown_calls = 0
        self.server_close_calls = 0
        self.shutdown_error = shutdown_error

    def serve_forever(self) -> None:
        return

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        if self.shutdown_error:
            raise RuntimeError("simulated close failure")

    def server_close(self) -> None:
        self.server_close_calls += 1


class ImmediateEvent:
    def __init__(self) -> None:
        self.value = False

    def set(self) -> None:
        self.value = True

    def wait(self, timeout=None) -> bool:
        return True

    def is_set(self) -> bool:
        return self.value


class RuntimeTransport:
    def __init__(self, path, **kwargs) -> None:
        self.path = path
        self.limits = kwargs

    def advertise(self) -> None:
        return

    def status(self) -> dict[str, str]:
        return {"subscribed": "true"}


class RuntimeController:
    instances: list["RuntimeController"] = []

    def __init__(self, transport, store) -> None:
        self.stop_calls = 0
        self.__class__.instances.append(self)

    def start(self) -> None:
        return

    def emergency_stop(self) -> None:
        self.stop_calls += 1

    def is_stopped(self) -> bool:
        return False


class RuntimeActions:
    instances: list["RuntimeActions"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.close_calls = 0
        self.__class__.instances.append(self)

    def close(self) -> None:
        self.close_calls += 1


class LifecycleCharacterizationTests(unittest.TestCase):
    def runtime(self, directory: str):
        config = Path(directory) / "config.json"
        config.write_text(json.dumps({
            "agent_keys_dpapi": {"agent": "key"}, "command_token_dpapi": "token",
            "hogp_executable": "engine.exe", "position_bind": "127.0.0.1",
            "position_port": 0, "tls_certificate": "cert", "tls_private_key": "key",
        }), encoding="utf-8")
        RuntimeController.instances.clear()
        RuntimeActions.instances.clear()
        patches = [
            mock.patch.object(app, "unprotect", side_effect=lambda value: b"secret"),
            mock.patch.object(app, "CaptureBroker", side_effect=lambda *a, **k: object()),
            mock.patch.object(app, "PositionStore", side_effect=lambda: object()),
            mock.patch.object(app, "HmacVerifier", side_effect=lambda *a, **k: object()),
            mock.patch.object(app, "PositionReceiver", side_effect=lambda *a, **k: object()),
            mock.patch.object(app, "NativeHogpTransport", RuntimeTransport),
            mock.patch.object(app, "MouseController", RuntimeController),
            mock.patch.object(app, "ActionRegistry", side_effect=lambda *a, **k: object()),
            mock.patch.object(app, "ActionExecutor", RuntimeActions),
            mock.patch.object(app, "CommandGateway", side_effect=lambda *a, **k: object()),
        ]
        return config, patches

    def test_L01_partial_server_creation_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            config, patches = self.runtime(directory)
            position = FakeServer()
            patches.extend([
                mock.patch.object(app, "make_https_server", return_value=position),
                mock.patch.object(app, "make_command_server",
                                  side_effect=RuntimeError("simulated creation failure")),
            ])
            with self._stack(patches):
                with self.assertRaisesRegex(RuntimeError, "creation failure"):
                    app.serve(config)
            self.assertEqual(position.shutdown_calls, 0)
            self.assertEqual(position.server_close_calls, 1)
            self.assertEqual(RuntimeActions.instances[-1].close_calls, 1)
            self.assertEqual(RuntimeController.instances[-1].stop_calls, 1)

    def test_L02_close_failure_does_not_skip_remaining_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            config, patches = self.runtime(directory)
            position = FakeServer(shutdown_error=True)
            command = FakeServer()
            events = FakeServer()
            thread_facade = types.SimpleNamespace(Thread=threading.Thread, Event=ImmediateEvent)
            patches.extend([
                mock.patch.object(app, "make_https_server", return_value=position),
                mock.patch.object(app, "make_command_server", return_value=command),
                mock.patch.object(app, "make_event_server", return_value=events),
                mock.patch.object(app, "threading", thread_facade),
                mock.patch.object(app.signal, "signal", return_value=None),
            ])
            with self._stack(patches):
                with self.assertRaisesRegex(app.RuntimeCleanupError, "close failure"):
                    app.serve(config)
            self.assertEqual(command.shutdown_calls, 1)
            self.assertEqual(events.shutdown_calls, 1)
            self.assertEqual(position.server_close_calls, 1)
            self.assertEqual(command.server_close_calls, 1)
            self.assertEqual(events.server_close_calls, 1)
            self.assertEqual(RuntimeActions.instances[-1].close_calls, 1)
            self.assertEqual(RuntimeController.instances[-1].stop_calls, 1)

    def test_L03_failed_update_restores_previous_content_with_real_script(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            self.skipTest("PowerShell is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install = root / "install"
            artifact_dir = root / "artifact"
            install.mkdir()
            artifact_dir.mkdir()
            target = install / "PositionAgent.exe"
            artifact = artifact_dir / "PositionAgent.exe"
            target.write_bytes(b"old-agent")
            artifact.write_bytes(b"new-agent")
            state_output = root / "runtime-state.json"
            environment = dict(os.environ)
            environment["MC_POSITION_AGENT_TRANSACTION_TEST"] = "1"
            result = subprocess.run([
                shell, "-NoProfile", "-File",
                str(ROOT / "tests" / "support" / "position_agent_transaction_harness.ps1"),
                "-Updater", str(ROOT / "scripts" / "target" /
                                 "Update-InteractivePositionAgent.ps1"),
                "-Target", str(target), "-Artifact", str(artifact),
                "-Action", "Install", "-Phase", "Installation",
                "-StateOutput", str(state_output),
            ], capture_output=True, text=True, timeout=15, env=environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("previous version was restored", result.stderr)
            self.assertEqual(target.read_bytes(), b"old-agent")
            self.assertFalse(Path(str(target) + ".mc-update-state.json").exists())

    @staticmethod
    def _stack(patches):
        class Stack:
            def __enter__(self):
                for patch in patches:
                    patch.start()
                return self

            def __exit__(self, exc_type, exc, traceback):
                for patch in reversed(patches):
                    patch.stop()
                return False
        return Stack()


if __name__ == "__main__":
    unittest.main()
