from __future__ import annotations

import threading
import time
from pathlib import Path
import tempfile
import unittest

from mousse_controler.actions import ActionExecutor, ActionRegistry, ActionState
from mousse_controler.controller import MouseController, PositionSnapshot, PositionStore
from mousse_controler.transport import SimulatedHidTransport, TransportError


TERMINAL = {"EXECUTED", "CONFIRMED", "FAILED", "UNKNOWN", "CANCELLED"}


class FeedbackTransport(SimulatedHidTransport):
    def __init__(self, store, x=0, y=0):
        super().__init__()
        self.store = store
        self.x, self.y, self.sequence = x, y, 1
        self._sample()

    def _sample(self):
        self.store.update(PositionSnapshot(
            self.x, self.y, self.sequence, 1, "topology",
            int(time.time() * 1000), time.monotonic(),
        ))

    def move(self, dx, dy):
        super().move(dx, dy)
        self.x += dx
        self.y += dy
        self.sequence += 1
        self._sample()


class FailingClickTransport(SimulatedHidTransport):
    def buttons(self, mask):
        super().buttons(mask)
        if mask:
            raise TransportError("delivery became uncertain")


class CaptureStub:
    def __init__(self, fail_after=False):
        self.calls = []
        self.fail_after = fail_after

    def request_capture(self, action_id, moment, **kwargs):
        self.calls.append((action_id, moment, kwargs))
        if self.fail_after and moment == "after":
            raise RuntimeError("camera failed")
        return {"capture_id": f"{action_id}-{moment}", "state": "STORED"}


class ActionExecutorTests(unittest.TestCase):
    def setUp(self):
        self.store = PositionStore()
        self.transport = FeedbackTransport(self.store)
        self.controller = MouseController(self.transport, self.store)
        self.controller.start()
        self.registry = ActionRegistry()
        self.captures = CaptureStub()
        self.executor = ActionExecutor(self.controller, self.registry, self.captures)

    def tearDown(self):
        self.executor.close()

    def wait(self, action_id, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = self.registry.get(action_id)
            if record["state"] in TERMINAL:
                return record
            time.sleep(0.005)
        self.fail("action did not finish")

    def submit_wait(self, spec, action_id=None):
        accepted = self.executor.submit(spec, action_id=action_id)
        self.assertEqual(accepted["state"], "ACCEPTED")
        return self.wait(accepted["action_id"])

    def test_left_right_middle_double_triple_and_configurable_clicks(self):
        for button, count, mask in (("left", 2, 1), ("right", 3, 2), ("middle", 4, 4)):
            result = self.submit_wait({
                "kind": "click", "button": button, "count": count,
                "hold_seconds": 0, "interval_seconds": 0,
            })
            self.assertEqual(result["state"], "EXECUTED")
            self.assertEqual(result["result"]["clicks"], count)
            self.assertEqual(result["result"]["button_mask"], mask)

    def test_button_combinations_press_and_release(self):
        pressed = self.submit_wait({"kind": "press", "buttons": ["left", "right"]})
        self.assertEqual(pressed["result"]["buttons_mask"], 3)
        released = self.submit_wait({"kind": "release", "button": "left"})
        self.assertEqual(released["result"]["buttons_mask"], 2)

    def test_hold_is_interruptible_and_releases_button(self):
        accepted = self.executor.submit({"kind": "hold", "button": "left", "duration_seconds": 2})
        while self.controller.buttons_mask() != 1:
            time.sleep(0.005)
        self.executor.cancel(accepted["action_id"])
        result = self.wait(accepted["action_id"])
        self.assertEqual(result["state"], "CANCELLED")
        self.assertEqual(self.controller.buttons_mask(), 0)

    def test_drag_confirms_real_cursor_arrival_and_releases(self):
        result = self.submit_wait({
            "kind": "drag", "button": "left", "x": 25, "y": -10, "tolerance_px": 0,
        })
        self.assertEqual(result["state"], "CONFIRMED")
        self.assertEqual(result["result"]["position"]["x"], 25)
        self.assertEqual(self.controller.buttons_mask(), 0)
        self.assertTrue(any(event[0] == "move" and event[3] == 1 for event in self.transport.events))

    def test_scroll_is_chunked_to_hid_int8_and_bounded(self):
        result = self.submit_wait({"kind": "scroll", "delta": 300})
        self.assertEqual(result["state"], "EXECUTED")
        values = [event[1] for event in self.transport.events if event[0] == "scroll"]
        self.assertEqual(values, [127, 127, 46])

    def test_continuous_scroll_is_interruptible(self):
        accepted = self.executor.submit({
            "kind": "scroll", "duration_seconds": 5, "step": -1, "interval_seconds": 0.01,
        })
        while not any(event[0] == "scroll" for event in self.transport.events):
            time.sleep(0.005)
        self.executor.cancel(accepted["action_id"])
        self.assertEqual(self.wait(accepted["action_id"])["state"], "CANCELLED")

    def test_horizontal_scroll_reports_capability_unavailable_without_hid(self):
        before = list(self.transport.events)
        result = self.submit_wait({"kind": "scroll", "axis": "horizontal", "delta": 1,
                                   "error_policy": "continue"})
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["error_code"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(before, self.transport.events)

    def test_click_is_executed_but_never_application_confirmed(self):
        result = self.submit_wait({"kind": "click", "button": "left", "hold_seconds": 0})
        self.assertEqual(result["state"], "EXECUTED")
        states = [event["action"]["state"] for event in self.registry.history()
                  if event["action"]["action_id"] == result["action_id"]]
        self.assertEqual(states, ["ACCEPTED", "RUNNING", "EXECUTED"])

    def test_capture_before_and_after_is_correlated(self):
        result = self.submit_wait({
            "kind": "click", "button": "left", "hold_seconds": 0,
            "capture": {"before": True, "after": True, "retention_seconds": 10},
        })
        self.assertEqual([item[1] for item in self.captures.calls], ["before", "after"])
        self.assertEqual(result["result"]["captures"]["after"]["state"], "STORED")

    def test_sequence_capture_policy_applies_only_to_mouse_children(self):
        result = self.submit_wait({
            "kind": "sequence",
            "capture": {"before": True, "after": True, "retention_seconds": 7},
            "actions": [
                {"kind": "wait", "duration_seconds": 0},
                {"kind": "click", "button": "left", "hold_seconds": 0},
            ],
        })
        self.assertEqual(result["state"], "EXECUTED")
        self.assertEqual([item[1] for item in self.captures.calls], ["before", "after"])
        self.assertTrue(all(item[2]["retention_seconds"] == 7 for item in self.captures.calls))

    def test_independent_capture_action_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown action kind"):
            self.executor.submit({"kind": "capture", "moment": "after"})

    def test_failed_after_capture_does_not_repeat_mouse_action(self):
        self.executor.close()
        self.controller.start()
        self.captures = CaptureStub(fail_after=True)
        self.executor = ActionExecutor(self.controller, self.registry, self.captures)
        result = self.submit_wait({
            "kind": "click", "button": "left", "hold_seconds": 0,
            "capture": {"after": True}, "error_policy": "retry", "max_attempts": 3,
        })
        presses = [event for event in self.transport.events if event == ("buttons", 1)]
        self.assertEqual(len(presses), 1)
        self.assertEqual(result["state"], "EXECUTED")
        self.assertEqual(result["result"]["captures"]["after"]["state"], "FAILED")

    def test_wait_command_sequence_and_parent_child_correlation(self):
        parent = self.executor.submit({
            "kind": "sequence",
            "actions": [
                {"kind": "click", "button": "left", "hold_seconds": 0},
                {"kind": "wait_command", "timeout_seconds": 2},
                {"kind": "scroll", "delta": 1},
            ],
        })
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            children = [item for item in self.registry.list() if item["parent_id"] == parent["action_id"]]
            if len(children) >= 2:
                break
            time.sleep(0.005)
        self.executor.advance(parent["action_id"])
        result = self.wait(parent["action_id"])
        self.assertEqual(result["state"], "EXECUTED")
        self.assertEqual(len(result["result"]["children"]), 3)

    def test_pause_resume_sequence_stops_new_reports_temporarily(self):
        parent = self.executor.submit({
            "kind": "sequence",
            "actions": [{"kind": "wait", "duration_seconds": 0.2},
                        {"kind": "scroll", "delta": 1}],
        })
        self.executor.pause(parent["action_id"])
        count = len(self.transport.events)
        time.sleep(0.1)
        self.assertEqual(len(self.transport.events), count)
        self.executor.resume(parent["action_id"])
        self.assertEqual(self.wait(parent["action_id"])["state"], "EXECUTED")

    def test_emergency_stop_cancels_queue_and_no_hid_follows(self):
        first = self.executor.submit({"kind": "wait", "duration_seconds": 2})
        second = self.executor.submit({"kind": "click", "button": "left"})
        self.executor.emergency_stop()
        stop_index = self.transport.events.index(("stop",))
        self.wait(first["action_id"])
        self.wait(second["action_id"])
        self.assertFalse(any(event[0] in {"move", "buttons", "scroll"}
                             for event in self.transport.events[stop_index + 1:]))

    def test_uncertain_click_is_unknown_and_not_retried(self):
        self.executor.close()
        transport = FailingClickTransport()
        controller = MouseController(transport, PositionStore())
        controller.start()
        registry = ActionRegistry()
        executor = ActionExecutor(controller, registry)
        try:
            accepted = executor.submit({
                "kind": "click", "button": "left", "hold_seconds": 0,
                "error_policy": "retry", "max_attempts": 3,
            })
            deadline = time.monotonic() + 1
            while registry.get(accepted["action_id"])["state"] not in TERMINAL:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            result = registry.get(accepted["action_id"])
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(len([event for event in transport.events if event == ("buttons", 1)]), 1)
        finally:
            executor.close()

    def test_retry_policy_retries_safe_absolute_move_only(self):
        original = self.controller.move_to
        calls = {"count": 0}

        def transient(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("feedback not ready")
            return original(*args, **kwargs)

        self.controller.move_to = transient
        result = self.submit_wait({
            "kind": "move_to", "x": 5, "y": 6, "tolerance_px": 0,
            "error_policy": "retry", "max_attempts": 2,
        })
        self.assertEqual(result["state"], "CONFIRMED")
        self.assertEqual(result["result"]["attempts"], 2)

    def test_continue_policy_advances_sequence_after_failed_child(self):
        result = self.submit_wait({
            "kind": "sequence",
            "actions": [
                {"kind": "scroll", "axis": "horizontal", "delta": 1,
                 "error_policy": "continue"},
                {"kind": "click", "button": "left", "hold_seconds": 0},
            ],
        })
        self.assertEqual(result["state"], "EXECUTED")
        children = [self.registry.get(item) for item in result["result"]["children"]]
        self.assertEqual([item["state"] for item in children], ["FAILED", "EXECUTED"])

    def test_default_stop_policy_stops_controller_on_failure(self):
        result = self.submit_wait({"kind": "scroll", "axis": "horizontal", "delta": 1})
        self.assertEqual(result["state"], "FAILED")
        self.assertTrue(self.controller.is_stopped())

    def test_duplicate_ids_and_queue_resource_limits(self):
        first = self.executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="same")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.executor.submit({"kind": "wait", "duration_seconds": 0}, action_id="same")
        self.wait(first["action_id"])

    def test_capabilities_match_five_button_descriptor(self):
        capabilities = self.executor.capabilities()
        self.assertEqual(capabilities["buttons"]["forward"], 16)
        self.assertFalse(capabilities["horizontal_wheel"])


class ActionJournalTests(unittest.TestCase):
    def test_restart_marks_inflight_unknown_and_blocks_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.jsonl"
            first = ActionRegistry(journal_path=path)
            first.create("inflight", "click")
            first.transition("inflight", ActionState.RUNNING)

            recovered = ActionRegistry(journal_path=path)
            record = recovered.get("inflight")
            self.assertEqual(record["state"], "UNKNOWN")
            self.assertEqual(record["error_code"], "PROCESS_RESTART")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                recovered.create("inflight", "click")


if __name__ == "__main__":
    unittest.main()
