"""Behavioural qualification for R1 functional safety; simulated HID only."""

from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import time
import unittest

from mousse_controler.actions import ActionExecutor, ActionRegistry
from mousse_controler.command_server import CommandError, CommandGateway
from mousse_controler.controller import MouseController, PositionSnapshot, PositionStore
from mousse_controler.transport import SimulatedHidTransport, TransportError


TERMINAL = {"EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED"}


def wait_terminal(registry: ActionRegistry, action_id: str, timeout: float = 1.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = registry.get(action_id)
        if record["state"] in TERMINAL:
            return record
        time.sleep(0.005)
    raise AssertionError(f"action {action_id} did not become terminal")


class ArmedButtonFailureTransport(SimulatedHidTransport):
    """Fails after applying a selected simulated button report."""

    def __init__(self) -> None:
        super().__init__()
        self.remaining: int | None = None
        self.armed_calls = 0

    def arm(self, fail_on_call: int) -> None:
        self.remaining = fail_on_call
        self.armed_calls = 0

    def buttons(self, mask: int) -> None:
        super().buttons(mask)
        if self.remaining is None:
            return
        self.armed_calls += 1
        self.remaining -= 1
        if self.remaining == 0:
            self.remaining = None
            raise TransportError("simulated acknowledgement loss after button effect")


class StopBeforeReleaseController(MouseController):
    """Pauses the selected release before the controller lock is acquired."""

    def __init__(self, transport: SimulatedHidTransport, positions: PositionStore) -> None:
        super().__init__(transport, positions)
        self.release_entered = threading.Event()
        self.allow_release = threading.Event()
        self._race_armed = False

    def arm_release_race(self) -> None:
        self._race_armed = True

    def release_buttons(self, mask: int) -> int:
        if self._race_armed:
            self._race_armed = False
            self.release_entered.set()
            if not self.allow_release.wait(1):
                raise AssertionError("test did not release the deterministic race gate")
        return super().release_buttons(mask)


class FeedbackTransport(SimulatedHidTransport):
    def __init__(self, store: PositionStore) -> None:
        super().__init__()
        self.store = store
        self.x = 0
        self.y = 0
        self.sequence = 1
        self._sample()

    def _sample(self) -> None:
        self.store.update(PositionSnapshot(
            self.x, self.y, self.sequence, 1, "topology",
            int(time.time() * 1000), time.monotonic(),
        ))

    def move(self, dx: int, dy: int) -> None:
        super().move(dx, dy)
        self.x += dx
        self.y += dy
        self.sequence += 1
        self._sample()


class ButtonSafetyTests(unittest.TestCase):
    CASES = (
        ("press", {"kind": "press", "button": "left"}, 1, False),
        ("release", {"kind": "release", "button": "left"}, 1, True),
        ("hold", {"kind": "hold", "button": "left", "duration_seconds": 0}, 1, False),
        ("drag", {"kind": "drag", "button": "left", "x": 5, "y": 5}, 1, False),
        ("move_with_buttons", {
            "kind": "move_with_buttons", "button": "left", "dx": 2, "dy": 3,
        }, 1, False),
        ("click", {"kind": "click", "button": "left", "hold_seconds": 0}, 2, False),
    )

    def test_every_ambiguous_button_action_and_policy_enters_quarantine(self):
        for name, base_spec, fail_on_call, preheld in self.CASES:
            for policy in ("stop", "continue", "retry"):
                with self.subTest(kind=name, policy=policy):
                    transport = ArmedButtonFailureTransport()
                    controller = MouseController(transport, PositionStore())
                    controller.start()
                    if preheld:
                        controller.press_buttons(1)
                    transport.arm(fail_on_call)
                    registry = ActionRegistry()
                    executor = ActionExecutor(controller, registry)
                    try:
                        spec = dict(base_spec, error_policy=policy, max_attempts=3)
                        accepted = executor.submit(spec, action_id=f"{name}-{policy}")
                        result = wait_terminal(registry, accepted["action_id"])
                        self.assertEqual(result["state"], "UNKNOWN")
                        self.assertTrue(controller.is_stopped())
                        self.assertEqual(controller.buttons_mask(), 0)
                        self.assertEqual(transport.buttons_mask, 0)
                        self.assertEqual(transport.armed_calls, fail_on_call)
                        self.assertFalse(
                            result["result"]["safety_stop"]["release_confirmed"])
                        stop_index = transport.events.index(("stop",))
                        self.assertFalse(any(
                            event[0] in {"move", "buttons", "scroll"}
                            for event in transport.events[stop_index + 1:]
                        ))
                        with self.assertRaisesRegex(RuntimeError, "safety-stopped"):
                            executor.submit({"kind": "wait", "duration_seconds": 0})
                    finally:
                        executor.close()

    def test_sequence_continue_cannot_pass_ambiguous_button_child(self):
        transport = ArmedButtonFailureTransport()
        controller = MouseController(transport, PositionStore())
        controller.start()
        transport.arm(1)
        registry = ActionRegistry()
        executor = ActionExecutor(controller, registry)
        try:
            parent = executor.submit({
                "kind": "sequence", "error_policy": "continue", "actions": [
                    {"kind": "press", "button": "left", "error_policy": "continue",
                     "action_id": "ambiguous-child"},
                    {"kind": "click", "button": "left", "hold_seconds": 0,
                     "action_id": "must-not-run"},
                ],
            }, action_id="parent")
            result = wait_terminal(registry, parent["action_id"])
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(registry.get("ambiguous-child")["state"], "UNKNOWN")
            with self.assertRaises(KeyError):
                registry.get("must-not-run")
            self.assertTrue(controller.is_stopped())
        finally:
            executor.close()

    def test_hold_stop_between_wait_and_release_is_unknown_for_every_policy(self):
        for policy in ("stop", "continue", "retry"):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as directory:
                transport = SimulatedHidTransport()
                controller = StopBeforeReleaseController(transport, PositionStore())
                controller.start()
                controller.arm_release_race()
                journal = Path(directory) / "actions.jsonl"
                registry = ActionRegistry(journal_path=journal)
                executor = ActionExecutor(controller, registry)
                action_id = f"hold-release-race-{policy}"
                try:
                    executor.submit({
                        "kind": "hold", "button": "left", "duration_seconds": 0,
                        "error_policy": policy, "max_attempts": 3,
                    }, action_id=action_id)
                    self.assertTrue(controller.release_entered.wait(1))
                    controller.emergency_stop()
                    controller.allow_release.set()
                    result = wait_terminal(registry, action_id)
                    self.assertEqual(result["state"], "UNKNOWN")
                    self.assertEqual(result["error_code"], "BUTTON_UNCERTAIN")
                    self.assertFalse(
                        result["result"]["safety_stop"]["release_confirmed"])
                    self.assertEqual(
                        [event for event in transport.events if event == ("buttons", 1)],
                        [("buttons", 1)],
                    )
                    with self.assertRaisesRegex(RuntimeError, "safety-stopped"):
                        executor.submit({"kind": "wait", "duration_seconds": 0})
                finally:
                    controller.allow_release.set()
                    executor.close()

                recovered = ActionRegistry(journal_path=journal)
                self.assertEqual(recovered.get(action_id)["state"], "UNKNOWN")
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    recovered.create(action_id, "hold")

    def test_hold_release_race_in_sequence_stops_before_next_child(self):
        transport = SimulatedHidTransport()
        controller = StopBeforeReleaseController(transport, PositionStore())
        controller.start()
        controller.arm_release_race()
        registry = ActionRegistry()
        executor = ActionExecutor(controller, registry)
        try:
            executor.submit({
                "kind": "sequence", "error_policy": "continue", "actions": [
                    {"kind": "hold", "button": "left", "duration_seconds": 0,
                     "error_policy": "continue", "action_id": "hold-race-child"},
                    {"kind": "wait", "duration_seconds": 0,
                     "action_id": "must-not-run-after-hold"},
                ],
            }, action_id="hold-race-parent")
            self.assertTrue(controller.release_entered.wait(1))
            controller.emergency_stop()
            controller.allow_release.set()
            parent = wait_terminal(registry, "hold-race-parent")
            self.assertEqual(parent["state"], "UNKNOWN")
            self.assertEqual(registry.get("hold-race-child")["state"], "UNKNOWN")
            with self.assertRaises(KeyError):
                registry.get("must-not-run-after-hold")
            with self.assertRaisesRegex(RuntimeError, "safety-stopped"):
                executor.submit({"kind": "wait", "duration_seconds": 0})
        finally:
            controller.allow_release.set()
            executor.close()

    def test_drag_and_move_with_buttons_success_paths_are_unchanged(self):
        store = PositionStore()
        transport = FeedbackTransport(store)
        controller = MouseController(transport, store)
        controller.start()
        registry = ActionRegistry()
        executor = ActionExecutor(controller, registry)
        try:
            executor.submit({
                "kind": "drag", "button": "left", "x": 4, "y": -3,
                "tolerance_px": 0,
            }, action_id="drag-regression")
            self.assertEqual(
                wait_terminal(registry, "drag-regression")["state"], "CONFIRMED")
            executor.submit({
                "kind": "move_with_buttons", "button": "left", "dx": 2, "dy": 3,
            }, action_id="move-buttons-regression")
            self.assertEqual(
                wait_terminal(registry, "move-buttons-regression")["state"], "EXECUTED")
            self.assertEqual(controller.buttons_mask(), 0)
            self.assertGreaterEqual(sum(
                event[0] == "move" and event[3] == 1 for event in transport.events
            ), 2)
        finally:
            executor.close()


class ExecutorCloseTests(unittest.TestCase):
    @staticmethod
    def make_executor(*, max_queue: int = 256, journal: Path | None = None):
        transport = SimulatedHidTransport()
        controller = MouseController(transport, PositionStore())
        controller.start()
        registry = ActionRegistry(journal_path=journal)
        executor = ActionExecutor(controller, registry, max_queue=max_queue)
        return transport, controller, registry, executor

    def test_close_wakes_suspended_action_and_cancels_queue(self):
        _transport, _controller, registry, executor = self.make_executor()
        running = executor.submit({"kind": "wait", "duration_seconds": 5},
                                  action_id="suspended")
        deadline = time.monotonic() + 1
        while registry.get(running["action_id"])["state"] != "RUNNING":
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        executor.pause("suspended")
        executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="queued")
        executor.close(timeout=1)
        self.assertEqual(registry.get("suspended")["state"], "CANCELLED")
        self.assertEqual(registry.get("queued")["state"], "CANCELLED")
        self.assertFalse(executor._worker.is_alive())
        with self.assertRaisesRegex(RuntimeError, "closed"):
            executor.submit({"kind": "wait", "duration_seconds": 0})

    def test_close_marks_inflight_hold_unknown_not_cancelled(self):
        transport, controller, registry, executor = self.make_executor()
        executor.submit({
            "kind": "hold", "button": "left", "duration_seconds": 5,
        }, action_id="inflight-hold")
        deadline = time.monotonic() + 1
        while controller.buttons_mask() != 1:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        executor.close(timeout=1)
        result = registry.get("inflight-hold")
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["error_code"], "BUTTON_UNCERTAIN")
        self.assertFalse(result["result"]["safety_stop"]["release_confirmed"])
        self.assertEqual(controller.buttons_mask(), 0)
        stop_index = transport.events.index(("stop",))
        self.assertFalse(any(event[0] in {"move", "buttons", "scroll"}
                             for event in transport.events[stop_index + 1:]))

    def test_full_queue_failure_and_close_leave_all_ids_terminal(self):
        _transport, _controller, registry, executor = self.make_executor(max_queue=1)
        executor.submit({"kind": "wait", "duration_seconds": 5}, action_id="running")
        deadline = time.monotonic() + 1
        while registry.get("running")["state"] != "RUNNING":
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="queued")
        with self.assertRaisesRegex(RuntimeError, "queue capacity"):
            executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="overflow")
        executor.close(timeout=1)
        self.assertEqual(registry.get("running")["state"], "CANCELLED")
        self.assertEqual(registry.get("queued")["state"], "CANCELLED")
        self.assertEqual(registry.get("overflow")["state"], "FAILED")

    def test_close_states_and_anti_replay_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "actions.jsonl"
            _transport, _controller, registry, executor = self.make_executor(journal=journal)
            executor.submit({"kind": "wait", "duration_seconds": 5}, action_id="running")
            deadline = time.monotonic() + 1
            while registry.get("running")["state"] != "RUNNING":
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="queued")
            executor.close(timeout=1)

            recovered = ActionRegistry(journal_path=journal)
            self.assertEqual(recovered.get("running")["state"], "CANCELLED")
            self.assertEqual(recovered.get("queued")["state"], "CANCELLED")
            for action_id in ("running", "queued"):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    recovered.create(action_id, "wait")

    def test_concurrent_submit_and_close_never_leave_nonterminal_acceptance(self):
        _transport, _controller, registry, executor = self.make_executor(max_queue=32)
        barrier = threading.Barrier(9)
        accepted: list[str] = []
        accepted_lock = threading.Lock()

        def submit(index: int) -> None:
            barrier.wait()
            try:
                record = executor.submit(
                    {"kind": "wait", "duration_seconds": 0.2}, action_id=f"race-{index}")
            except RuntimeError:
                return
            with accepted_lock:
                accepted.append(record["action_id"])

        threads = [threading.Thread(target=submit, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        barrier.wait()
        executor.close(timeout=1)
        for thread in threads:
            thread.join(1)
        for action_id in accepted:
            self.assertIn(registry.get(action_id)["state"], TERMINAL)

    def test_controller_stop_error_does_not_leave_actions_nonterminal(self):
        class FailingController:
            def emergency_stop(self):
                raise RuntimeError("simulated controller failure")

        registry = ActionRegistry()
        executor = ActionExecutor(FailingController(), registry)
        executor.submit({"kind": "wait", "duration_seconds": 5}, action_id="running")
        deadline = time.monotonic() + 1
        while registry.get("running")["state"] != "RUNNING":
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="queued")
        with self.assertRaisesRegex(RuntimeError, "controller stop failed"):
            executor.close(timeout=1)
        self.assertEqual(registry.get("running")["state"], "CANCELLED")
        self.assertEqual(registry.get("queued")["state"], "CANCELLED")
        self.assertFalse(executor._worker.is_alive())


class StopComponentDouble:
    def __init__(self, state: str = "RUNNING", *, fail: bool = False) -> None:
        self.state = state
        self.fail = fail
        self.calls = 0
        self.lock = threading.Lock()

    def request_stop(self) -> None:
        with self.lock:
            self.calls += 1
        if self.fail:
            raise RuntimeError("simulated stop error")
        self.state = "STOPPED"


class StopControllerDouble:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0
        self.lock = threading.Lock()

    def emergency_stop(self) -> None:
        with self.lock:
            self.calls += 1
        if self.fail:
            raise RuntimeError("simulated controller stop error")


class GlobalStopTests(unittest.TestCase):
    @staticmethod
    def envelope(identifier: str) -> dict:
        return {
            "command_id": identifier, "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000, "command": "stop", "arguments": {},
        }

    def test_global_stop_covers_historical_moving_waiting_and_paused_states(self):
        for state in ("MOVING", "WAITING", "PAUSED"):
            with self.subTest(state=state):
                actions = StopComponentDouble()
                sequence = StopComponentDouble(state)
                controller = StopControllerDouble()
                gateway = CommandGateway(b"token", controller, object(), object(), actions)
                gateway._sequence = sequence
                gateway.execute(self.envelope(f"stop-{state}"))
                self.assertEqual(actions.state, "STOPPED")
                self.assertEqual(sequence.state, "STOPPED")
                self.assertEqual(controller.calls, 1)

    def test_repeated_and_concurrent_global_stops_are_idempotent(self):
        actions = StopComponentDouble()
        sequence = StopComponentDouble("PAUSED")
        controller = StopControllerDouble()
        gateway = CommandGateway(b"token", controller, object(), object(), actions)
        gateway._sequence = sequence
        threads = [threading.Thread(
            target=gateway.execute, args=(self.envelope(f"concurrent-{index}"),)
        ) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(1)
        self.assertEqual(actions.state, "STOPPED")
        self.assertEqual(sequence.state, "STOPPED")
        self.assertEqual(actions.calls, 6)
        self.assertEqual(sequence.calls, 6)
        self.assertEqual(controller.calls, 6)

    def test_one_stop_error_does_not_skip_other_components(self):
        actions = StopComponentDouble(fail=True)
        sequence = StopComponentDouble("MOVING")
        controller = StopControllerDouble()
        gateway = CommandGateway(b"token", controller, object(), object(), actions)
        gateway._sequence = sequence
        with self.assertRaisesRegex(CommandError, "actions"):
            gateway.execute(self.envelope("partial-error"))
        self.assertEqual(actions.calls, 1)
        self.assertEqual(sequence.state, "STOPPED")
        self.assertEqual(controller.calls, 1)


if __name__ == "__main__":
    unittest.main()
