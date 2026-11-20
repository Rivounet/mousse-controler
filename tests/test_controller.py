from __future__ import annotations

import threading
import time
import unittest

from mousse_controler.controller import MouseController, PositionError, PositionSnapshot, PositionStore
from mousse_controler.transport import SimulatedHidTransport


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedHidTransport()
        self.store = PositionStore()
        self.controller = MouseController(self.transport, self.store)
        self.controller.start()

    def sample(self, x=10, y=20, sequence=1, session=7, topology="a"):
        return PositionSnapshot(x, y, sequence, session, topology, int(time.time() * 1000), time.monotonic())

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
