from __future__ import annotations

import math
import random
import threading
import time
import unittest

from mousse_controler.controller import MouseController, PositionSnapshot, PositionStore
from mousse_controler.geometry import CircleZone, DesktopTopology, Display, PolygonZone, RectangleZone
from mousse_controler.sequence import SequenceRunner, SequenceState, SequenceStep, WaitMode
from mousse_controler.trajectory import TrajectoryConfig, TrajectoryEngine
from mousse_controler.transport import SimulatedHidTransport
from tests.support.waiting import wait_until


TOPOLOGY = DesktopTopology((Display(0, 0, 1920, 1080), Display(1920, 0, 1920, 1080)), "two")


class GeometryTests(unittest.TestCase):
    def test_rectangle_circle_polygon_seeded_points_inside(self):
        zones = [
            RectangleZone(10, 20, 100, 80),
            CircleZone(500, 500, 50),
            PolygonZone([(800, 100), (900, 120), (850, 250), (780, 180)]),
        ]
        for zone in zones:
            zone.validate(TOPOLOGY)
            first = zone.random_point(random.Random(42))
            second = zone.random_point(random.Random(42))
            self.assertEqual(first, second)
            self.assertTrue(zone.contains(first))

    def test_invalid_geometries_rejected(self):
        with self.assertRaises(ValueError):
            RectangleZone(0, 0, 0, 10)
        with self.assertRaises(ValueError):
            CircleZone(0, 0, -1)
        with self.assertRaises(ValueError):
            PolygonZone([(0, 0), (10, 10), (0, 10), (10, 0)])

    def test_zone_crossing_monitor_boundary_is_conservatively_rejected(self):
        with self.assertRaisesRegex(ValueError, "one physical display"):
            RectangleZone(1900, 100, 100, 100).validate(TOPOLOGY)

    def test_extreme_polygons_are_seeded_and_always_sampled_inside(self):
        polygons = [
            PolygonZone([(0, 0), (16_383, 1), (16_382, 1)]),  # very thin
            PolygonZone([(0, 0), (8, 0), (8, 2), (2, 2), (2, 8), (0, 8)]),  # concave
            PolygonZone([(-20, -10), (-1, -10), (-3, -1), (-18, -2)]),
            PolygonZone([(1_000_000_000, 1_000_000_000),
                         (1_000_016_383, 1_000_000_001),
                         (1_000_016_382, 1_000_000_001)]),
            PolygonZone([(0, 0), (5, 0), (10, 0), (10, 4), (0, 4)]),  # collinear vertices
            PolygonZone([(0, 0), (1_000_000, 1), (999_999, 1)]),  # near-degenerate
        ]
        for polygon in polygons:
            for seed in range(50):
                first = polygon.random_point(random.Random(seed))
                second = polygon.random_point(random.Random(seed))
                self.assertEqual(first, second)
                self.assertTrue(polygon.contains(first), (polygon.vertices, seed, first))


class TrajectoryTests(unittest.TestCase):
    def test_curved_seeded_trajectory_and_exact_target(self):
        engine = TrajectoryEngine(TrajectoryConfig(curvature=0.3, micro_variation_px=0))
        first = engine.generate((100, 100), (900, 100), TOPOLOGY, random.Random(7))
        second = engine.generate((100, 100), (900, 100), TOPOLOGY, random.Random(7))
        self.assertEqual(first, second)
        self.assertEqual(first[-1], (900, 100))
        self.assertTrue(any(y != 100 for _, y in first[:-1]))

    def test_progressive_speed_profile(self):
        engine = TrajectoryEngine(TrajectoryConfig(spacing_px=20, curvature=0, speed_variation=0, micro_variation_px=0))
        points = [(0, 100)] + engine.generate((0, 100), (1000, 100), TOPOLOGY, random.Random(1))
        distances = [math.dist(a, b) for a, b in zip(points, points[1:])]
        self.assertLess(distances[0], max(distances))
        self.assertLess(distances[-1], max(distances))

    def test_micro_variations_absent_at_rest(self):
        engine = TrajectoryEngine(TrajectoryConfig(micro_variation_px=3))
        self.assertEqual(engine.generate((100, 100), (100, 100), TOPOLOGY, random.Random(1)), [(100, 100)])

    def test_long_trajectory_respects_configurable_point_cap(self):
        engine = TrajectoryEngine(TrajectoryConfig(spacing_px=10, minimum_points=3, maximum_points=7))
        points = engine.generate((100, 100), (900, 100), TOPOLOGY, random.Random(1))
        self.assertLessEqual(len(points), 7)
        self.assertEqual(points[-1], (900, 100))


class FeedbackTransport(SimulatedHidTransport):
    def __init__(self, store: PositionStore, start=(10, 10), delay=0.0):
        super().__init__()
        self.store = store
        self.x, self.y = start
        self.sequence = 1
        self.delay = delay
        self.store.update(self._sample())

    def _sample(self):
        return PositionSnapshot(
            self.x, self.y, self.sequence, 1, TOPOLOGY.generation,
            int(time.time() * 1000), time.monotonic(),
        )

    def move(self, dx: int, dy: int) -> None:
        super().move(dx, dy)
        if self.delay:
            time.sleep(self.delay)
        self.x += dx
        self.y += dy
        self.sequence += 1
        self.store.update(self._sample())


class SequenceTests(unittest.TestCase):
    def make_runner(self, steps, *, delay=0.0, seed=3):
        store = PositionStore()
        transport = FeedbackTransport(store, delay=delay)
        controller = MouseController(transport, store)
        controller.start()
        runner = SequenceRunner(controller, TrajectoryEngine(), TOPOLOGY, steps, seed=seed)

        def cleanup() -> None:
            runner.stop()
            runner.join(1)

        self.addCleanup(cleanup)
        return runner, transport

    def test_a_b_c_sequence_confirmed_by_measurements(self):
        steps = [
            SequenceStep(RectangleZone(100, 100, 20, 20)),
            SequenceStep(CircleZone(300, 300, 10)),
            SequenceStep(PolygonZone([(500, 100), (520, 100), (510, 120)])),
        ]
        runner, _ = self.make_runner(steps)
        runner.start(); runner.join(3)
        status = runner.status()
        self.assertEqual(status.state, SequenceState.COMPLETED)
        self.assertEqual([result.state for result in status.results], ["ARRIVED"] * 3)
        for result, step in zip(status.results, steps):
            self.assertTrue(step.zone.contains(result.measured_position))

    def test_commanded_wait_requires_next(self):
        steps = [
            SequenceStep(RectangleZone(100, 100, 5, 5), WaitMode.COMMANDED),
            SequenceStep(RectangleZone(200, 200, 5, 5)),
        ]
        runner, _ = self.make_runner(steps)
        runner.start()
        wait_until(
            lambda: runner.status().state == SequenceState.WAITING,
            timeout=5,
            description="commanded sequence waiting state",
        )
        self.assertEqual(runner.status().state, SequenceState.WAITING)
        runner.next_target(); runner.join(2)
        self.assertEqual(runner.status().state, SequenceState.COMPLETED)

    def test_advance_before_commanded_wait_and_replay_are_rejected(self):
        steps = [
            SequenceStep(RectangleZone(300, 300, 5, 5), WaitMode.COMMANDED),
            SequenceStep(RectangleZone(400, 300, 5, 5)),
        ]
        runner, _ = self.make_runner(steps, delay=0.002)
        runner.start()
        with self.assertRaisesRegex(RuntimeError, "not awaiting"):
            runner.next_target()
        wait_until(
            lambda: runner.status().state == SequenceState.WAITING,
            timeout=3,
            description="advanced sequence waiting state",
        )
        self.assertEqual(runner.status().state, SequenceState.WAITING)
        runner.next_target(); runner.join(3)
        self.assertEqual(runner.status().state, SequenceState.COMPLETED)
        with self.assertRaisesRegex(RuntimeError, "cannot be replayed"):
            runner.start()

    def test_pause_resume_and_stop_prevent_future_hid(self):
        steps = [SequenceStep(RectangleZone(1000, 800, 5, 5))]
        runner, transport = self.make_runner(steps, delay=0.01)
        runner.start()
        wait_until(
            lambda: len([event for event in transport.events if event[0] == "move"]) >= 2,
            description="trajectory reports before pause",
        )
        runner.pause()
        count = len(transport.events)
        time.sleep(0.08)
        self.assertEqual(len(transport.events), count)
        runner.resume()
        time.sleep(0.03)
        runner.stop()
        runner.join(1)
        stopped_count = len(transport.events)
        time.sleep(0.05)
        self.assertEqual(len(transport.events), stopped_count)
        self.assertEqual(runner.status().state, SequenceState.STOPPED)

    def test_stop_from_commanded_wait_wakes_and_converges(self):
        steps = [
            SequenceStep(RectangleZone(100, 100, 5, 5), WaitMode.COMMANDED),
            SequenceStep(RectangleZone(200, 200, 5, 5)),
        ]
        runner, transport = self.make_runner(steps)
        runner.start()
        wait_until(
            lambda: runner.status().state == SequenceState.WAITING,
            timeout=2,
            description="trajectory waiting state",
        )
        self.assertEqual(runner.status().state, SequenceState.WAITING)
        runner.stop(); runner.join(1)
        stopped_count = len(transport.events)
        time.sleep(0.05)
        self.assertEqual(runner.status().state, SequenceState.STOPPED)
        self.assertEqual(len(transport.events), stopped_count)

    def test_stop_while_paused_wakes_and_converges(self):
        runner, transport = self.make_runner(
            [SequenceStep(RectangleZone(1000, 800, 5, 5))], delay=0.01)
        runner.start()
        wait_until(
            lambda: len([event for event in transport.events if event[0] == "move"]) >= 2,
            description="trajectory movement before pause race",
        )
        runner.pause()
        self.assertEqual(runner.status().state, SequenceState.PAUSED)
        runner.stop(); runner.join(1)
        stopped_count = len(transport.events)
        time.sleep(0.05)
        self.assertEqual(runner.status().state, SequenceState.STOPPED)
        self.assertEqual(len(transport.events), stopped_count)

    def test_topology_change_aborts_sequence(self):
        store = PositionStore()
        transport = FeedbackTransport(store)
        controller = MouseController(transport, store)
        controller.start()
        original_move = transport.move

        def changed(dx, dy):
            original_move(dx, dy)
            transport.sequence += 1
            store.update(PositionSnapshot(
                transport.x, transport.y, transport.sequence, 1, "changed",
                int(time.time() * 1000), time.monotonic(),
            ))

        transport.move = changed
        runner = SequenceRunner(controller, TrajectoryEngine(), TOPOLOGY, [SequenceStep(RectangleZone(500, 500, 5, 5))])
        runner.start(); runner.join(2)
        self.assertEqual(runner.status().state, SequenceState.ERROR)
        self.assertIn("topology changed", runner.status().error)
