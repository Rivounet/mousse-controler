from __future__ import annotations

import threading
import time
import unittest

from mousse_controler.controller import (
    MouseController,
    PositionError,
    PositioningError,
    PositionSnapshot,
    PositionStore,
)
from mousse_controler.transport import SimulatedHidTransport


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedHidTransport()
        self.store = PositionStore()
        self.controller = MouseController(self.transport, self.store)
        self.controller.start()

    def sample(self, x=10, y=20, sequence=1, session=7, topology="a"):
        return PositionSnapshot(x, y, sequence, session, topology, int(time.time() * 1000), time.monotonic())

    def attach_feedback(self, transform):
        current = self.store.latest(max_age_ms=10_000)
        state = {"x": current.x, "y": current.y, "sequence": current.sequence}
        original = self.transport.move

        def move(dx, dy):
            original(dx, dy)
            updated = transform(state["x"], state["y"], dx, dy)
            if updated is None:
                return
            state["x"], state["y"] = updated
            state["sequence"] += 1
            self.store.update(self.sample(
                x=state["x"], y=state["y"], sequence=state["sequence"],
            ))

        self.transport.move = move
        return state

    def run_queued_command_during_stop(self, command):
        command_started = threading.Event()
        command_errors = []

        def invoke():
            command_started.set()
            try:
                command()
            except Exception as exc:  # asserted by the caller
                command_errors.append(exc)

        self.controller._lock.acquire()
        try:
            command_thread = threading.Thread(target=invoke)
            command_thread.start()
            self.assertTrue(command_started.wait(1))
            stop_thread = threading.Thread(target=self.controller.emergency_stop)
            stop_thread.start()
            self.assertTrue(self.controller._stopped.wait(1))
        finally:
            self.controller._lock.release()
        command_thread.join(1)
        stop_thread.join(1)
        self.assertFalse(command_thread.is_alive())
        self.assertFalse(stop_thread.is_alive())
        self.assertEqual(len(command_errors), 1)
        self.assertIsInstance(command_errors[0], RuntimeError)
        self.assertEqual(str(command_errors[0]), "controller is stopped")
        return list(self.transport.events)

    def test_bounds_rejected_before_transport(self):
        with self.assertRaises(ValueError):
            self.controller.move(40000, 0)
        self.assertNotIn(("move", 40000, 0, 0), self.transport.events)

    def test_position_loop_uses_bounded_proportional_correction(self):
        self.store.update(self.sample(x=0, y=0))

        def feedback():
            while not any(event[0] == "move" for event in self.transport.events):
                time.sleep(0.001)
            self.store.update(self.sample(x=100, y=0, sequence=2))

        thread = threading.Thread(target=feedback)
        thread.start()
        self.controller.move_to(100, 0, max_step=2048, adaptive_acceleration=False)
        thread.join()

        self.assertIn(("move", 35, 0, 0), self.transport.events)

    def test_position_loop_uses_acceleration_aware_default(self):
        self.store.update(self.sample(x=0, y=0))

        def feedback():
            while not any(event[0] == "move" for event in self.transport.events):
                time.sleep(0.001)
            self.store.update(self.sample(x=100, y=0, sequence=2))

        thread = threading.Thread(target=feedback)
        thread.start()
        self.controller.move_to(100, 0)
        thread.join()

        self.assertIn(("move", 44, 0, 0), self.transport.events)

    def test_adaptive_position_loop_honors_explicit_step_cap(self):
        self.store.update(self.sample(x=0, y=0))

        def feedback():
            while not any(event[0] == "move" for event in self.transport.events):
                time.sleep(0.001)
            self.store.update(self.sample(x=100, y=0, sequence=2))

        thread = threading.Thread(target=feedback)
        thread.start()
        self.controller.move_to(100, 0, max_step=8)
        thread.join()

        self.assertIn(("move", 8, 0, 0), self.transport.events)

    def test_emergency_stop_releases_buttons(self):
        self.controller.set_buttons(1)
        self.controller.emergency_stop()
        self.assertEqual(self.transport.buttons_mask, 0)
        self.assertIn(("release",), self.transport.events)
        self.assertFalse(self.transport.started)

    def test_move_waiting_for_lock_is_rejected_by_simultaneous_stop(self):
        events = self.run_queued_command_during_stop(lambda: self.controller.move(5, -2))

        self.assertNotIn(("move", 5, -2, 0), events)
        self.assertEqual(events[-1], ("stop",))

    def test_scroll_waiting_for_lock_is_rejected_by_simultaneous_stop(self):
        events = self.run_queued_command_during_stop(lambda: self.controller.scroll(1))

        self.assertFalse(any(event[0] == "scroll" for event in events))
        self.assertEqual(events[-1], ("stop",))

    def test_button_command_waiting_for_lock_is_rejected_after_stop_request(self):
        events = self.run_queued_command_during_stop(lambda: self.controller.set_buttons(1))

        self.assertFalse(any(event[0] == "buttons" for event in events))
        self.assertEqual(events[-1], ("stop",))

    def test_click_waiting_for_lock_is_rejected_by_simultaneous_stop(self):
        events = self.run_queued_command_during_stop(
            lambda: self.controller.click(1, hold_seconds=0)
        )

        self.assertFalse(any(event[0] == "buttons" for event in events))
        self.assertEqual(events[-1], ("stop",))

    def test_click_in_progress_releases_before_simultaneous_stop_becomes_effective(self):
        pressed = threading.Event()
        original_buttons = self.transport.buttons

        def observed_buttons(mask):
            original_buttons(mask)
            if mask == 1:
                pressed.set()

        self.transport.buttons = observed_buttons
        click_errors = []

        def click():
            try:
                self.controller.click(1, hold_seconds=5)
            except Exception as exc:  # asserted below
                click_errors.append(exc)

        click_thread = threading.Thread(target=click)
        click_thread.start()
        self.assertTrue(pressed.wait(1))
        stop_thread = threading.Thread(target=self.controller.emergency_stop)
        stop_thread.start()
        click_thread.join(1)
        stop_thread.join(1)

        self.assertEqual([str(exc) for exc in click_errors], ["controller stopped during click"])
        self.assertEqual(self.transport.events[-1], ("stop",))
        stop_index = len(self.transport.events) - 1
        self.assertLess(self.transport.events.index(("buttons", 0)), stop_index)
        self.assertFalse(any(event[0] in {"move", "buttons", "scroll"}
                             for event in self.transport.events[stop_index + 1:]))
        self.assertEqual(self.transport.buttons_mask, 0)

    def test_restart_transport_releases_buttons_and_starts_again(self):
        self.controller.set_buttons(1)

        self.controller.restart_transport()

        self.assertTrue(self.transport.started)
        self.assertEqual(self.transport.buttons_mask, 0)
        self.assertIn(("stop",), self.transport.events)

    def test_restart_transport_is_disabled_after_emergency_stop(self):
        self.controller.emergency_stop()
        count = len(self.transport.events)

        self.controller.restart_transport()

        self.assertEqual(len(self.transport.events), count)

    def test_restart_waiting_for_lock_does_not_run_during_stop(self):
        restart_started = threading.Event()

        def restart():
            restart_started.set()
            self.controller.restart_transport()

        self.controller._lock.acquire()
        try:
            restart_thread = threading.Thread(target=restart)
            restart_thread.start()
            self.assertTrue(restart_started.wait(1))
            stop_thread = threading.Thread(target=self.controller.emergency_stop)
            stop_thread.start()
            self.assertTrue(self.controller._stopped.wait(1))
        finally:
            self.controller._lock.release()
        restart_thread.join(1)
        stop_thread.join(1)

        self.assertEqual(self.transport.events.count(("start",)), 1)
        self.assertEqual(self.transport.events[-1], ("stop",))
        self.assertFalse(self.transport.started)

    def test_repeated_stop_is_idempotent(self):
        self.controller.emergency_stop()
        events_after_first_stop = list(self.transport.events)

        self.controller.emergency_stop()

        self.assertEqual(self.transport.events, events_after_first_stop)

    def test_start_after_stop_creates_a_new_command_epoch(self):
        self.controller.set_buttons(1)
        self.controller.emergency_stop()
        stopped_at = len(self.transport.events)

        self.controller.start()
        self.controller.move(3, 4)

        self.assertEqual(self.transport.events[stopped_at], ("start",))
        self.assertEqual(self.transport.events[stopped_at + 1], ("move", 3, 4, 0))
        self.assertTrue(self.transport.started)

    def test_failed_start_cleans_partial_transport_and_remains_stopped(self):
        self.controller.emergency_stop()
        original_start = self.transport.start

        def failing_start():
            original_start()
            raise RuntimeError("injected start failure")

        self.transport.start = failing_start

        with self.assertRaisesRegex(RuntimeError, "injected start failure"):
            self.controller.start()

        self.assertTrue(self.controller.is_stopped())
        self.assertFalse(self.transport.started)
        self.assertEqual(self.transport.events[-1], ("stop",))

    def test_position_loop_uses_new_feedback(self):
        self.store.update(self.sample())

        def feedback():
            while not any(event[0] == "move" for event in self.transport.events):
                time.sleep(0.001)
            self.store.update(self.sample(x=100, y=200, sequence=2))

        thread = threading.Thread(target=feedback)
        thread.start()
        result = self.controller.move_to(100, 200)
        thread.join()
        self.assertEqual((result.x, result.y), (100, 200))
        metrics = self.controller.positioning_metrics()
        self.assertGreater(metrics["corrections"], 0)
        self.assertGreaterEqual(metrics["transport_ms"], 0)
        self.assertGreaterEqual(metrics["feedback_wait_ms"], 0)

    def test_position_loop_stops_on_session_change(self):
        self.store.update(self.sample())

        def feedback():
            while not any(event[0] == "move" for event in self.transport.events):
                time.sleep(0.001)
            self.store.update(self.sample(sequence=2, session=8))

        thread = threading.Thread(target=feedback)
        thread.start()
        with self.assertRaisesRegex(PositionError, "session changed"):
            self.controller.move_to(100, 200)
        thread.join()

    def test_stale_sample_rejected(self):
        sample = self.sample()
        self.store.update(PositionSnapshot(
            sample.x, sample.y, sample.sequence, sample.session_id,
            sample.topology_generation, sample.observed_at_unix_ms,
            time.monotonic() - 1,
        ))
        with self.assertRaisesRegex(PositionError, "stale"):
            self.controller.move_to(100, 200)

    def test_confirmed_relative_return_is_exact_after_one_pixel_residual(self):
        self.store.update(self.sample(x=100, y=50))

        def accelerated(_x, _y, dx, dy):
            def effect(value):
                if abs(value) <= 1:
                    return value
                return value - (1 if value > 0 else -1)
            return _x + effect(dx), _y + effect(dy)

        self.attach_feedback(accelerated)
        first_initial, outbound = self.controller.move_relative_confirmed(
            -10, 0, tolerance_px=0,
        )
        return_initial, returned = self.controller.move_relative_confirmed(
            10, 0, tolerance_px=0,
        )

        self.assertEqual((first_initial.x, outbound.x), (100, 90))
        self.assertEqual((return_initial.x, returned.x, returned.y), (90, 100, 50))
        self.assertEqual(self.controller.positioning_metrics()["final_error_px"], 0.0)
        self.assertGreaterEqual(
            len([event for event in self.transport.events if event[0] == "move"]), 4,
        )

    def test_confirmed_relative_rejects_unavailable_measurement_without_hid(self):
        with self.assertRaises(PositioningError) as raised:
            self.controller.move_relative_confirmed(10, 0)

        self.assertEqual(raised.exception.code, "POSITION_FEEDBACK_UNAVAILABLE")
        self.assertFalse(raised.exception.emitted)
        self.assertFalse(any(event[0] == "move" for event in self.transport.events))

    def test_confirmed_relative_rejects_stale_measurement_without_hid(self):
        sample = self.sample(x=0, y=0)
        self.store.update(PositionSnapshot(
            sample.x, sample.y, sample.sequence, sample.session_id,
            sample.topology_generation, sample.observed_at_unix_ms,
            time.monotonic() - 1,
        ))
        with self.assertRaises(PositioningError) as raised:
            self.controller.move_relative_confirmed(10, 0, max_age_ms=100)

        self.assertEqual(raised.exception.code, "POSITION_FEEDBACK_UNAVAILABLE")
        self.assertFalse(raised.exception.emitted)
        self.assertFalse(any(event[0] == "move" for event in self.transport.events))

    def test_position_loop_detects_ineffective_corrections(self):
        self.store.update(self.sample(x=0, y=0))
        self.attach_feedback(lambda x, y, _dx, _dy: (x, y + 1))

        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(
                10, 0, tolerance_px=0, no_progress_limit=2,
                stagnation_limit=10, oscillation_limit=10,
            )

        self.assertEqual(raised.exception.code, "POSITION_NO_PROGRESS")
        self.assertTrue(raised.exception.emitted)

    def test_position_loop_detects_stagnation(self):
        self.store.update(self.sample(x=0, y=0))
        self.attach_feedback(lambda x, y, _dx, _dy: (x, y))

        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(
                10, 0, tolerance_px=0, stagnation_limit=2,
                no_progress_limit=10, oscillation_limit=10,
            )

        self.assertEqual(raised.exception.code, "POSITION_STAGNATION")
        self.assertTrue(raised.exception.emitted)

    def test_position_loop_detects_oscillation(self):
        self.store.update(self.sample(x=0, y=0))
        state = {"alternate": False}

        def oscillate(_x, y, _dx, _dy):
            state["alternate"] = not state["alternate"]
            return (-1 if state["alternate"] else 0), y

        self.attach_feedback(oscillate)
        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(
                10, 0, tolerance_px=0, oscillation_limit=2,
                stagnation_limit=10, no_progress_limit=10,
            )

        self.assertEqual(raised.exception.code, "POSITION_OSCILLATION")
        self.assertTrue(raised.exception.emitted)

    def test_position_loop_enforces_iteration_limit(self):
        self.store.update(self.sample(x=0, y=0))
        self.attach_feedback(lambda x, y, _dx, _dy: (x + 1, y))

        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(
                10, 0, tolerance_px=0, max_iterations=2,
                stagnation_limit=10, oscillation_limit=10, no_progress_limit=10,
            )

        self.assertEqual(raised.exception.code, "POSITION_ITERATION_LIMIT")
        self.assertEqual(raised.exception.metrics["corrections"], 2)

    def test_position_loop_enforces_cumulative_movement_limit(self):
        self.store.update(self.sample(x=0, y=0))

        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(10, 0, tolerance_px=0, max_total_movement=1)

        self.assertEqual(raised.exception.code, "POSITION_MOVEMENT_LIMIT")
        self.assertFalse(raised.exception.emitted)
        self.assertFalse(any(event[0] == "move" for event in self.transport.events))

    def test_emergency_stop_interrupts_feedback_wait(self):
        self.store.update(self.sample(x=0, y=0))
        errors = []

        def position():
            try:
                self.controller.move_to(10, 0, feedback_timeout=5)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=position)
        started = time.monotonic()
        thread.start()
        deadline = time.monotonic() + 1
        while not any(event[0] == "move" for event in self.transport.events):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.controller.emergency_stop()
        thread.join(1)

        self.assertFalse(thread.is_alive())
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], PositioningError)
        self.assertEqual(errors[0].code, "POSITION_INTERRUPTED")
        self.assertTrue(errors[0].emitted)
        self.assertEqual(self.transport.events[-1], ("stop",))

    def test_uncertain_hid_emission_is_explicit(self):
        self.store.update(self.sample(x=0, y=0))
        original = self.transport.move

        def uncertain(dx, dy):
            original(dx, dy)
            raise RuntimeError("delivery acknowledgement lost")

        self.transport.move = uncertain
        with self.assertRaises(PositioningError) as raised:
            self.controller.move_to(10, 0)

        self.assertEqual(raised.exception.code, "POSITION_EMISSION_UNCERTAIN")
        self.assertTrue(raised.exception.emitted)
        self.assertEqual(
            len([event for event in self.transport.events if event[0] == "move"]), 1,
        )
