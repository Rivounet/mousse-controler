"""R3 storage, lifecycle and transactional rollback qualification."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

from mousse_controler import app
from mousse_controler.capture import CaptureBroker, CaptureQuotaError
from tests.support.waiting import wait_until


ROOT = Path(__file__).resolve().parents[2]
PNG = b"\x89PNG\r\n\x1a\n" + b"r3-bounded-capture"


class CaptureHarness:
    def __init__(self, root: Path, *, limit: int = 16_384,
                 observer=None) -> None:
        self.root = root
        self.broker = CaptureBroker(
            root, max_bytes=1024, max_total_bytes=limit,
            storage_observer=observer,
        )

    def request(self, action_id: str = "r3-action") -> tuple[threading.Thread, dict, dict]:
        outcome: dict[str, object] = {}

        def run() -> None:
            try:
                outcome["result"] = self.broker.request_capture(
                    action_id, "after", timeout=2,
                )
            except BaseException as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=run)
        thread.start()
        request = wait_until(
            self.broker.next_request,
            description="capture request delivery",
        )
        return thread, outcome, request

    @staticmethod
    def upload(request: dict, image: bytes = PNG) -> bytes:
        return json.dumps({
            "capture_id": request["capture_id"],
            "action_id": request["action_id"],
            "moment": request["moment"],
            "state": "CAPTURED",
            "captured_at_ms": int(time.time() * 1000),
            "cursor": {"x": 1, "y": 1},
            "monitor": {"x": 0, "y": 0, "width": 10, "height": 10},
            "image_base64": base64.b64encode(image).decode("ascii"),
        }, separators=(",", ":")).encode()


class CaptureQuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_quota_admission_counts_index_orphans_and_temporary_peak(self) -> None:
        harness = CaptureHarness(self.root)
        thread, outcome, request = harness.request()
        orphan = self.root / "unrelated.orphan"
        orphan.write_bytes(b"o" * 300)
        used = harness.broker.quota_status()["used_bytes"]
        harness.broker._max_total_bytes = used + len(PNG)
        with self.assertRaises(CaptureQuotaError):
            harness.broker.accept_upload(harness.upload(request))
        thread.join(1)
        self.assertIsInstance(outcome.get("error"), RuntimeError)
        self.assertFalse((self.root / f"{request['capture_id']}.png").exists())
        self.assertFalse((self.root / f".{request['capture_id']}.tmp").exists())
        status = harness.broker.quota_status()
        self.assertLessEqual(status["used_bytes"], status["max_total_bytes"])
        self.assertEqual(orphan.stat().st_size, 300)

    def test_exact_limit_is_observed_at_each_physical_coexistence_stage(self) -> None:
        observations: list[tuple[str, int, set[str]]] = []

        def observe(stage: str, used: int) -> None:
            names = {path.name for path in self.root.iterdir() if path.is_file()}
            observations.append((stage, used, names))

        harness = CaptureHarness(self.root, limit=64_000, observer=observe)
        thread, outcome, request = harness.request()
        observations.clear()
        orphan = self.root / "orphan-retained.bin"
        preexisting = self.root / ".preexisting.tmp"
        orphan.write_bytes(b"o" * 211)
        preexisting.write_bytes(b"t" * 173)
        original = harness.broker._ensure_upload_capacity_locked

        def set_exact_limit(image_size: int, index_size: int) -> int:
            exact = harness.broker._directory_usage_locked() + image_size + index_size
            harness.broker._max_total_bytes = exact
            return original(image_size, index_size)

        with mock.patch.object(
                harness.broker, "_ensure_upload_capacity_locked",
                side_effect=set_exact_limit):
            stored = harness.broker.accept_upload(harness.upload(request))
        thread.join(1)
        self.assertNotIn("error", outcome)
        self.assertEqual(stored["state"], "STORED")
        quota = harness.broker.quota_status()["max_total_bytes"]
        self.assertTrue(observations)
        self.assertTrue(all(used <= quota for _stage, used, _names in observations))
        image_stage = next(item for item in observations
                           if item[0] == "image_temporary_written")
        self.assertIn(".capture-index.json", image_stage[2])
        self.assertIn(f".{request['capture_id']}.tmp", image_stage[2])
        index_stage = next(item for item in observations
                           if item[0] == "index_temporary_written")
        self.assertIn(".capture-index.json", index_stage[2])
        self.assertIn(f"{request['capture_id']}.png", index_stage[2])
        self.assertTrue(any(name.startswith(".capture-index.") and name.endswith(".tmp")
                            for name in index_stage[2]))
        self.assertEqual(index_stage[1], quota)
        self.assertTrue(orphan.exists())
        self.assertTrue(preexisting.exists())

    def test_disk_free_space_is_checked_before_writing(self) -> None:
        harness = CaptureHarness(self.root)
        thread, outcome, request = harness.request()
        usage = types.SimpleNamespace(total=1000, used=1000, free=0)
        with mock.patch("mousse_controler.capture.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(CaptureQuotaError, "free space"):
                harness.broker.accept_upload(harness.upload(request))
        thread.join(1)
        self.assertIn("error", outcome)
        self.assertEqual(list(self.root.glob("*.png")), [])

    def test_concurrent_uploads_are_serialized_and_never_exceed_quota(self) -> None:
        observations: list[int] = []
        harness = CaptureHarness(
            self.root, limit=32_768,
            observer=lambda _stage, used: observations.append(used),
        )
        requests = [harness.request(f"action-{index}") for index in range(2)]
        used = harness.broker.quota_status()["used_bytes"]
        harness.broker._max_total_bytes = used * 2 + len(PNG) + 128
        results: list[str] = []

        def upload(item) -> None:
            try:
                results.append(harness.broker.accept_upload(harness.upload(item[2]))["state"])
            except CaptureQuotaError:
                results.append("QUOTA")

        workers = [threading.Thread(target=upload, args=(item,)) for item in requests]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        for thread, _outcome, _request in requests:
            thread.join(1)
        self.assertIn("STORED", results)
        self.assertIn("QUOTA", results)
        status = harness.broker.quota_status()
        self.assertLessEqual(status["used_bytes"], status["max_total_bytes"])
        self.assertTrue(observations)
        self.assertTrue(all(used <= status["max_total_bytes"]
                            for used in observations))

    def test_missing_and_invalid_indexes_reconcile_orphans_without_deletion(self) -> None:
        for invalid in (None, "{broken", '{"version":1,"records":[{}]}'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "orphan.png").write_bytes(PNG)
                (root / ".abandoned.tmp").write_bytes(b"partial")
                if invalid is not None:
                    (root / ".capture-index.json").write_text(invalid, encoding="utf-8")
                broker = CaptureBroker(root, max_bytes=1024, max_total_bytes=16_384)
                recovered = broker.list_for_action("__recovered__")
                self.assertEqual(len(recovered), 2)
                self.assertTrue(all(item["state"] == "DELETE_FAILED" for item in recovered))
                self.assertTrue((root / "orphan.png").exists())
                self.assertTrue((root / ".abandoned.tmp").exists())
                self.assertTrue((root / ".capture-index.json").exists())
                if invalid is not None:
                    self.assertEqual(len(list(root.glob(".capture-index.invalid-*.json"))), 1)
                status = broker.quota_status()
                actual = sum(path.stat().st_size for path in root.iterdir() if path.is_file())
                self.assertEqual(status["used_bytes"], actual)

    def test_interrupted_write_is_recovered_and_delete_failure_remains_retryable(self) -> None:
        harness = CaptureHarness(self.root)
        thread, _outcome, request = harness.request()
        temporary = self.root / f".{request['capture_id']}.tmp"
        temporary.write_bytes(PNG)
        thread.join(3)
        restarted = CaptureBroker(self.root, max_bytes=1024, max_total_bytes=16_384)
        recovered = restarted.get(request["capture_id"])
        self.assertEqual(recovered["state"], "DELETE_FAILED")
        self.assertEqual(recovered["storage_path"], str(temporary))
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            failed = restarted.delete(request["capture_id"])
        self.assertEqual(failed["state"], "DELETE_FAILED")
        self.assertTrue(temporary.exists())
        status = restarted.quota_status()
        self.assertLessEqual(status["used_bytes"], status["max_total_bytes"])
        self.assertEqual(restarted.delete(request["capture_id"])["state"], "DELETED")
        self.assertFalse(temporary.exists())

    def test_interruption_after_image_commit_preserves_and_reconciles_file(self) -> None:
        observations: list[tuple[str, int]] = []
        harness = CaptureHarness(
            self.root, observer=lambda stage, used: observations.append((stage, used)),
        )
        thread, outcome, request = harness.request()
        original = harness.broker._persist_index_locked

        def interrupt_commit() -> None:
            destination = self.root / f"{request['capture_id']}.png"
            if destination.exists():
                raise OSError("simulated interruption before index commit")
            original()

        with mock.patch.object(
                harness.broker, "_persist_index_locked", side_effect=interrupt_commit):
            with self.assertRaisesRegex(OSError, "before index commit"):
                harness.broker.accept_upload(harness.upload(request))
        thread.join(1)
        destination = self.root / f"{request['capture_id']}.png"
        self.assertTrue(destination.exists())
        self.assertEqual(
            harness.broker.get(request["capture_id"])["state"], "DELETE_FAILED",
        )
        self.assertTrue(all(used <= harness.broker.quota_status()["max_total_bytes"]
                            for _stage, used in observations))
        restarted = CaptureBroker(self.root, max_bytes=1024, max_total_bytes=16_384)
        self.assertEqual(restarted.get(request["capture_id"])["state"], "DELETE_FAILED")


class ServerDouble:
    def __init__(self, name: str, calls: list[str], *, shutdown_error=False,
                 close_error=False) -> None:
        self.name = name
        self.calls = calls
        self.shutdown_error = shutdown_error
        self.close_error = close_error

    def serve_forever(self) -> None:
        self.calls.append(f"{self.name}.serve")

    def shutdown(self) -> None:
        self.calls.append(f"{self.name}.shutdown")
        if self.shutdown_error:
            raise RuntimeError(f"{self.name} shutdown failure")

    def server_close(self) -> None:
        self.calls.append(f"{self.name}.close")
        if self.close_error:
            raise RuntimeError(f"{self.name} close failure")


class ActionsDouble:
    def __init__(self, *args, calls=None, close_error=False, **kwargs) -> None:
        self.calls = calls if calls is not None else []
        self.close_error = close_error

    def close(self) -> None:
        self.calls.append("actions.close")
        if self.close_error:
            raise RuntimeError("actions close failure")


class ControllerDouble:
    def __init__(self, transport, store, *, calls=None, start_error=False,
                 stop_error=False) -> None:
        self.calls = calls if calls is not None else []
        self.start_error = start_error
        self.stop_error = stop_error

    def start(self) -> None:
        self.calls.append("controller.start")
        if self.start_error:
            raise RuntimeError("controller start failure")

    def emergency_stop(self) -> None:
        self.calls.append("controller.stop")
        if self.stop_error:
            raise RuntimeError("controller stop failure")

    def is_stopped(self) -> bool:
        return True


class ImmediateEvent:
    def __init__(self) -> None:
        self.value = False

    def set(self) -> None:
        self.value = True

    def wait(self, timeout=None) -> bool:
        return True


class ThreadDouble:
    starts = 0
    fail_at: int | None = None
    remain_alive = False

    def __init__(self, target=None, name=None, daemon=None) -> None:
        self.target = target
        self.name = name
        self.started = False

    def start(self) -> None:
        type(self).starts += 1
        if type(self).fail_at == type(self).starts:
            raise RuntimeError(f"thread {type(self).starts} start failure")
        self.started = True

    def join(self, timeout=None) -> None:
        return

    def is_alive(self) -> bool:
        return self.started and type(self).remain_alive


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.calls: list[str] = []
        self.servers = {
            name: ServerDouble(name, self.calls)
            for name in ("position", "command", "events")
        }
        ThreadDouble.starts = 0
        ThreadDouble.fail_at = None
        ThreadDouble.remain_alive = False

    def config(self) -> Path:
        path = Path(self.temporary.name) / "config.json"
        path.write_text(json.dumps({
            "agent_keys_dpapi": {"agent": "key"},
            "command_token_dpapi": "token", "hogp_executable": "engine.exe",
            "position_bind": "127.0.0.1", "position_port": 0,
            "tls_certificate": "cert", "tls_private_key": "key",
        }), encoding="utf-8")
        return path

    def patches(self, *, factory_failure: str | None = None,
                start_error=False, actions_error=False, controller_error=False):
        calls = self.calls
        controller = ControllerDouble(None, None, calls=calls, start_error=start_error,
                                      stop_error=controller_error)
        actions = ActionsDouble(calls=calls, close_error=actions_error)

        def factory(name):
            if factory_failure == name:
                raise RuntimeError(f"{name} creation failure")
            return self.servers[name]

        facade = mock.Mock(wraps=threading)
        facade.Thread = ThreadDouble
        facade.Event = ImmediateEvent
        return [
            mock.patch.object(app, "unprotect", side_effect=lambda value: b"secret"),
            mock.patch.object(app, "CaptureBroker", return_value=object()),
            mock.patch.object(app, "PositionStore", return_value=object()),
            mock.patch.object(app, "HmacVerifier", return_value=object()),
            mock.patch.object(app, "PositionReceiver", return_value=object()),
            mock.patch.object(app, "NativeHogpTransport", return_value=types.SimpleNamespace(
                advertise=lambda: None, status=lambda: {"subscribed": "true"})),
            mock.patch.object(app, "MouseController", return_value=controller),
            mock.patch.object(app, "ActionRegistry", return_value=object()),
            mock.patch.object(app, "ActionExecutor", return_value=actions),
            mock.patch.object(app, "CommandGateway", return_value=object()),
            mock.patch.object(app, "make_https_server", side_effect=lambda *a, **k: factory("position")),
            mock.patch.object(app, "make_command_server", side_effect=lambda *a, **k: factory("command")),
            mock.patch.object(app, "make_event_server", side_effect=lambda *a, **k: factory("events")),
            mock.patch.object(app, "threading", facade),
            mock.patch.object(app.signal, "signal", return_value=None),
        ]

    def run_with(self, patches) -> BaseException | None:
        with _PatchStack(patches):
            try:
                app.serve(self.config())
            except BaseException as exc:
                return exc
        return None

    def test_partial_initialization_closes_every_created_server_in_reverse(self) -> None:
        expectations = {
            "position": [],
            "command": ["position.close"],
            "events": ["command.close", "position.close"],
        }
        for failure, closed in expectations.items():
            with self.subTest(failure=failure):
                self.calls.clear()
                error = self.run_with(self.patches(factory_failure=failure))
                self.assertIn(f"{failure} creation failure", str(error))
                actual = [call for call in self.calls
                          if call in {"position.close", "command.close", "events.close"}]
                self.assertEqual(actual, closed)
                self.assertIn("actions.close", self.calls)
                self.assertIn("controller.stop", self.calls)

    def test_composition_failure_closes_partial_runtime(self) -> None:
        original_close = app._RuntimeLifecycle.close

        for component in ("MouseApplicationService", "CommandGateway"):
            with self.subTest(component=component):
                self.calls.clear()
                closed_lifecycles = []

                def observe_close(lifecycle):
                    result = original_close(lifecycle)
                    closed_lifecycles.append(lifecycle)
                    return result

                patches = self.patches()
                patches.append(mock.patch.object(
                    app, component,
                    side_effect=RuntimeError(f"{component} composition failure"),
                ))
                patches.append(mock.patch.object(
                    app._RuntimeLifecycle, "close", new=observe_close,
                ))

                error = self.run_with(patches)

                self.assertIsInstance(error, RuntimeError)
                self.assertIn(f"{component} composition failure", str(error))
                self.assertIn("actions.close", self.calls)
                self.assertIn("controller.stop", self.calls)
                self.assertEqual(len(closed_lifecycles), 1)
                lifecycle = closed_lifecycles[0]
                self.assertFalse(any(lifecycle.command_token))
                self.assertTrue(all(
                    not any(secret) for secret in lifecycle.keys.values()
                ))

    def test_each_thread_start_failure_cleans_started_and_unstarted_servers(self) -> None:
        for failure in (1, 2, 3):
            with self.subTest(thread=failure):
                self.calls.clear()
                ThreadDouble.starts = 0
                ThreadDouble.fail_at = failure
                error = self.run_with(self.patches())
                self.assertIn("start failure", str(error))
                self.assertEqual(
                    [call for call in self.calls
                     if call in {"position.close", "command.close", "events.close"}],
                    ["events.close", "command.close", "position.close"],
                )
                self.assertEqual(
                    len([call for call in self.calls if call.endswith(".shutdown")]),
                    failure - 1,
                )

    def test_all_close_failures_are_aggregated_without_skipping_resources(self) -> None:
        for server in self.servers.values():
            server.shutdown_error = True
            server.close_error = True
        error = self.run_with(self.patches(actions_error=True, controller_error=True))
        self.assertIsInstance(error, app.RuntimeCleanupError)
        labels = [label for label, _failure in error.cleanup_errors]
        for expected in (
            "events-websocket shutdown", "events-websocket server_close",
            "command-loopback shutdown", "command-loopback server_close",
            "position-https shutdown", "position-https server_close",
            "actions close", "controller emergency_stop",
        ):
            self.assertIn(expected, labels)
        self.assertIn("actions.close", self.calls)
        self.assertIn("controller.stop", self.calls)

    def test_lifecycle_close_is_idempotent(self) -> None:
        actions = ActionsDouble(calls=self.calls)
        controller = ControllerDouble(None, None, calls=self.calls)
        lifecycle = app._RuntimeLifecycle(actions, controller, b"token", {})
        lifecycle.add_server("position", self.servers["position"])
        self.assertEqual(lifecycle.close(), [])
        self.assertEqual(lifecycle.close(), [])
        self.assertEqual(self.calls.count("position.close"), 1)
        self.assertEqual(self.calls.count("actions.close"), 1)
        self.assertEqual(self.calls.count("controller.stop"), 1)

    def test_thread_join_timeout_is_observable_without_skipping_cleanup(self) -> None:
        ThreadDouble.remain_alive = True
        error = self.run_with(self.patches())
        self.assertIsInstance(error, app.RuntimeCleanupError)
        labels = [label for label, _failure in error.cleanup_errors]
        self.assertIn("events-websocket thread join", labels)
        self.assertIn("command-loopback thread join", labels)
        self.assertIn("position-https thread join", labels)
        self.assertIn("actions.close", self.calls)
        self.assertIn("controller.stop", self.calls)


class _PatchStack:
    def __init__(self, patches) -> None:
        self.patches = patches

    def __enter__(self):
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        for patch in reversed(self.patches):
            patch.stop()
        return False


class PositionAgentTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = shutil.which("pwsh") or shutil.which("powershell")
        if cls.shell is None:
            raise unittest.SkipTest("PowerShell is required for transaction tests")
        cls.updater = ROOT / "scripts" / "target" / "Update-InteractivePositionAgent.ps1"
        cls.harness = ROOT / "tests" / "support" / "position_agent_transaction_harness.ps1"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.install = root / "install"
        self.artifacts = root / "artifact"
        self.install.mkdir()
        self.artifacts.mkdir()
        self.target = self.install / "PositionAgent.exe"
        self.artifact = self.artifacts / "PositionAgent.exe"
        self.target.write_bytes(b"old-agent-version")
        self.artifact.write_bytes(b"new-agent-version")
        self.runtime_state = root / "runtime-state.json"

    @property
    def state_path(self) -> Path:
        return Path(str(self.target) + ".mc-update-state.json")

    def invoke(self, phase="None", action="Install", initial_state="Running") -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["MC_POSITION_AGENT_TRANSACTION_TEST"] = "1"
        return subprocess.run([
            self.shell, "-NoProfile", "-File", str(self.harness),
            "-Updater", str(self.updater), "-Target", str(self.target),
            "-Artifact", str(self.artifact), "-Action", action, "-Phase", phase,
            "-StateOutput", str(self.runtime_state),
            "-InitialTaskState", initial_state,
        ], text=True, capture_output=True, timeout=15, env=environment)

    def runtime(self) -> dict:
        return json.loads(self.runtime_state.read_text(encoding="utf-8"))

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()

    def test_successful_install_and_explicit_rollback_are_hash_verified(self) -> None:
        installed = self.invoke()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertEqual(self.target.read_bytes(), b"new-agent-version")
        self.assertEqual(
            Path(str(self.target) + ".mc-mouse-actions.previous").read_bytes(),
            b"old-agent-version",
        )
        self.assertFalse(self.state_path.exists())
        rolled_back = self.invoke(action="Rollback")
        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
        self.assertEqual(self.target.read_bytes(), b"old-agent-version")

    def test_failures_before_replacement_restore_original_runtime(self) -> None:
        for index, phase in enumerate(
                ("Preparation", "Stop", "Backup", "Staging", "Replacement")):
            with self.subTest(phase=phase):
                self.prepare_clean_case(f"pre-replacement-{index}")
                result = self.invoke(phase)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.target.read_bytes(), b"old-agent-version")
                self.assertEqual(self.sha256(self.target), self.runtime()["target_sha256"])
                self.assertEqual(self.runtime()["task_state"], "Running")
                self.assertEqual(self.runtime()["process_count"], 1)
                self.assertFalse(self.state_path.exists())
                retry = self.invoke()
                self.assertEqual(retry.returncode, 0, retry.stderr)
                self.assertEqual(self.target.read_bytes(), b"new-agent-version")

    def test_pre_replacement_failure_preserves_initial_inactive_state(self) -> None:
        self.prepare_clean_case("initially-inactive")
        result = self.invoke("Backup", initial_state="Ready")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"old-agent-version")
        runtime = self.runtime()
        self.assertEqual(runtime["task_state"], "Ready")
        self.assertEqual(runtime["process_count"], 0)
        self.assertFalse(self.state_path.exists())

    def test_failed_pre_replacement_recovery_is_durable_and_blocks_install(self) -> None:
        for index, phase in enumerate(("RecoveryRestart", "RecoveryVerification")):
            with self.subTest(phase=phase):
                self.prepare_clean_case(f"recovery-{index}")
                result = self.invoke(phase)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.target.read_bytes(), b"old-agent-version")
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
                self.assertEqual(state["phase"], "RECOVERY_REQUIRED")
                self.assertEqual(state["restore_attempts"], 2)
                self.assertEqual(state["initial_task_state"], "Running")
                self.assertEqual(state["initial_process_count"], 1)
                retry = self.invoke()
                self.assertNotEqual(retry.returncode, 0)
                self.assertIn("explicit recovery", retry.stderr)

    def test_failures_after_replacement_restore_and_restart_previous_version(self) -> None:
        for phase in ("Installation", "Start", "Verification", "Confirmation"):
            with self.subTest(phase=phase):
                result = self.invoke(phase)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("previous version was restored", result.stderr)
                self.assertEqual(self.target.read_bytes(), b"old-agent-version")
                self.assertFalse(self.state_path.exists())

    def test_failed_restore_is_bounded_and_blocks_ambiguous_reinstall(self) -> None:
        result = self.invoke("Restore")
        self.assertNotEqual(result.returncode, 0)
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "RECOVERY_REQUIRED")
        self.assertEqual(state["restore_attempts"], 2)
        self.assertEqual(state["initial_task_state"], "Running")
        self.assertEqual(state["initial_process_count"], 1)
        self.assertEqual(self.target.read_bytes(), b"new-agent-version")
        retry = self.invoke()
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("explicit recovery", retry.stderr)

    def test_restart_after_restore_failure_keeps_old_content_and_recovery_state(self) -> None:
        result = self.invoke("RestartAfterRestore")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), b"old-agent-version")
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "RECOVERY_REQUIRED")
        self.assertEqual(state["restore_attempts"], 2)

    def prepare_clean_case(self, name: str) -> None:
        root = Path(self.temporary.name) / name
        self.install = root / "install"
        self.artifacts = root / "artifact"
        self.install.mkdir(parents=True)
        self.artifacts.mkdir()
        self.target = self.install / "PositionAgent.exe"
        self.artifact = self.artifacts / "PositionAgent.exe"
        self.runtime_state = root / "runtime-state.json"
        self.target.write_bytes(b"old-agent-version")
        self.artifact.write_bytes(b"new-agent-version")

    def prepare_rollback_case(self, name: str) -> None:
        self.prepare_clean_case(name)
        installed = self.invoke()
        self.assertEqual(installed.returncode, 0, installed.stderr)

    def test_explicit_rollback_faults_restore_original_runtime(self) -> None:
        phases = (
            "RollbackBeforeMutation", "RollbackAfterPreserve", "RollbackCopy",
            "RollbackPartialCopy", "RollbackBeforeValidation", "RollbackValidation",
            "RollbackAfterMutation", "RollbackStart", "RollbackVerification",
        )
        for index, phase in enumerate(phases):
            with self.subTest(phase=phase):
                self.prepare_rollback_case(f"rollback-{index}")
                current_hash = self.sha256(self.target)
                result = self.invoke(phase, action="Rollback")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.sha256(self.target), current_hash)
                runtime = self.runtime()
                self.assertEqual(runtime["task_state"], "Running")
                self.assertEqual(runtime["process_count"], 1)
                self.assertFalse(self.state_path.exists())
                self.assertFalse(Path(str(self.target) + ".mc-mouse-actions.failed").exists())
                self.assertFalse(Path(str(self.target) + ".mc-mouse-actions.rollback").exists())

    def test_explicit_rollback_compensation_failure_requires_recovery(self) -> None:
        self.prepare_rollback_case("rollback-compensation")
        current_hash = self.sha256(self.target)
        result = self.invoke("RollbackCompensation", action="Rollback")
        self.assertNotEqual(result.returncode, 0)
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "RECOVERY_REQUIRED")
        self.assertEqual(state["restore_attempts"], 2)
        self.assertEqual(state["initial_task_state"], "Running")
        self.assertEqual(state["initial_process_count"], 1)
        preserved = Path(str(self.target) + ".mc-mouse-actions.failed")
        self.assertTrue(preserved.exists())
        self.assertEqual(self.sha256(preserved), current_hash)
        retry = self.invoke()
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("explicit recovery", retry.stderr)


if __name__ == "__main__":
    unittest.main()
