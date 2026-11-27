from __future__ import annotations

import threading
import time
import unittest

from mousse_controler.actions import ActionExecutor, ActionRegistry
from mousse_controler.application import MouseApplicationService
from mousse_controler.controller import MouseController
from mousse_controler.feedback import PositionSnapshot, PositionStore
from mousse_controler.geometry import DesktopTopology, Display
from mousse_controler.orchestration import (
    OperationBusyError,
    OperationCancelled,
    OperationCoordinator,
)
from mousse_controler.transport import SimulatedHidTransport
from tests.support.waiting import wait_until


class ReceiverStub:
    def metrics(self):
        return {}


class ArchitectureConvergenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = SimulatedHidTransport()
        self.controller = MouseController(self.transport, PositionStore())
        self.controller.start()
        self.actions = ActionExecutor(self.controller, ActionRegistry())
        self.application = MouseApplicationService(
            self.controller,
            self.transport,
            ReceiverStub(),
            self.actions,
        )

    def tearDown(self) -> None:
        self.actions.close()

    def test_legacy_move_cannot_interleave_with_modern_hold(self) -> None:
        self.actions.submit(
            {"kind": "hold", "button": "left", "duration_seconds": 0.15},
            action_id="modern-hold",
        )
        wait_until(
            lambda: self.controller.buttons_mask() == 1,
            description="modern hold acquisition",
        )

        with self.assertRaisesRegex(OperationBusyError, "mouse operation busy"):
            self.application.move("legacy-move", 7, 0)

        self.assertFalse(any(event[0] == "move" for event in self.transport.events))
        wait_until(
            lambda: self.controller.buttons_mask() == 0,
            description="modern hold release",
        )
        result = self.application.move("legacy-after", 7, 0)
        self.assertEqual(result["state"], "EXECUTED")
        self.assertEqual(self.transport.events[-1], ("move", 7, 0, 0))

    def test_cancelled_action_waiter_never_acquires_lane(self) -> None:
        coordinator = OperationCoordinator()
        lease = coordinator.acquire("owner", wait=False)
        cancelled = threading.Event()
        outcome: list[type[BaseException]] = []

        def wait() -> None:
            try:
                coordinator.acquire("waiter", wait=True, cancel_event=cancelled)
            except BaseException as exc:
                outcome.append(type(exc))

        thread = threading.Thread(target=wait)
        thread.start()
        cancelled.set()
        thread.join(1)
        lease.close()

        self.assertEqual(outcome, [OperationCancelled])
        self.assertIsNone(coordinator.snapshot().owner)


class AtomicFeedbackTests(unittest.TestCase):
    @staticmethod
    def position(sequence: int, generation: str) -> PositionSnapshot:
        return PositionSnapshot(
            10,
            20,
            sequence,
            1,
            generation,
            int(time.time() * 1000),
            time.monotonic(),
        )

    def test_position_and_topology_publish_as_one_generation(self) -> None:
        store = PositionStore()
        topology = DesktopTopology((Display(0, 0, 100, 100),), "one")
        store.update(self.position(1, "one"), topology)

        feedback = store.feedback()

        self.assertEqual(feedback.position.sequence, 1)
        self.assertIs(feedback.topology, topology)
        self.assertEqual(feedback.position.topology_generation, feedback.topology.generation)

    def test_mismatched_feedback_generation_is_rejected_before_publication(self) -> None:
        store = PositionStore()
        topology = DesktopTopology((Display(0, 0, 100, 100),), "one")
        store.update(self.position(1, "one"), topology)

        with self.assertRaisesRegex(ValueError, "generations differ"):
            store.update(self.position(2, "two"), topology)

        self.assertEqual(store.feedback().position.sequence, 1)


if __name__ == "__main__":
    unittest.main()
