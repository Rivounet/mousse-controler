import threading
import unittest

from mousse_controler.hogp_health import HogpHealthMonitor


class _Controller:
    def __init__(self) -> None:
        self.stopped = False
        self.restarts = 0
        self.restart_error: Exception | None = None

    def is_stopped(self) -> bool:
        return self.stopped

    def restart_transport(self) -> None:
        self.restarts += 1
        if self.restart_error is not None:
            raise self.restart_error


class _StoppingController(_Controller):
    def restart_transport(self) -> None:
        super().restart_transport()
        self.stopped = True


class _Transport:
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def status(self):
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class HogpHealthMonitorTests(unittest.TestCase):
    def monitor(self, outcomes, *, controller=None, clock=lambda: 10.0,
                on_provider_restart=None):
        selected_controller = controller or _Controller()
        monitor = HogpHealthMonitor(
            selected_controller,
            _Transport(outcomes),
            threading.Event(),
            poll_seconds=1.0,
            fault_recovery_seconds=5.0,
            clock=clock,
            on_provider_restart=on_provider_restart,
        )
        return monitor, selected_controller

    def test_missing_subscriber_never_recreates_provider(self) -> None:
        monitor, controller = self.monitor([
            {"advertising": "True", "authorized_subscriber": "False"},
            {"advertising": "True", "authorized_subscriber": "False"},
        ])

        monitor.poll_once()
        status = monitor.poll_once()

        self.assertEqual(status.state, "awaiting_subscriber")
        self.assertFalse(status.authorized_subscriber)
        self.assertEqual(controller.restarts, 0)

    def test_authorized_subscriber_is_connected(self) -> None:
        monitor, controller = self.monitor([{
            "advertising": "True", "authorized_subscriber": "True",
        }])

        status = monitor.poll_once()

        self.assertEqual(status.state, "connected")
        self.assertTrue(status.authorized_subscriber)
        self.assertEqual(controller.restarts, 0)

    def test_engine_fault_is_restarted_once_within_cooldown(self) -> None:
        now = [10.0]
        monitor, controller = self.monitor(
            [RuntimeError("channel lost"), RuntimeError("still lost")],
            clock=lambda: now[0],
        )

        first = monitor.poll_once()
        now[0] = 12.0
        second = monitor.poll_once()

        self.assertEqual(first.state, "engine_restarted")
        self.assertEqual(second.state, "engine_fault")
        self.assertEqual(controller.restarts, 1)

    def test_successful_poll_does_not_bypass_fault_cooldown(self) -> None:
        now = [10.0]
        monitor, controller = self.monitor(
            [
                RuntimeError("first"),
                {"advertising": "True", "subscribed": "false"},
                RuntimeError("second"),
            ],
            clock=lambda: now[0],
        )

        monitor.poll_once()
        now[0] = 11.0
        monitor.poll_once()
        now[0] = 12.0
        status = monitor.poll_once()

        self.assertEqual(status.state, "engine_fault")
        self.assertEqual(controller.restarts, 1)

        now[0] = 16.0
        retried = monitor.poll_once()

        self.assertEqual(retried.state, "engine_restarted")
        self.assertEqual(controller.restarts, 2)

    def test_failed_recovery_is_observable(self) -> None:
        controller = _Controller()
        controller.restart_error = RuntimeError("restart denied")
        monitor, _ = self.monitor([RuntimeError("channel lost")], controller=controller)

        status = monitor.poll_once()

        self.assertEqual(status.state, "recovery_failed")
        self.assertIn("restart denied", status.last_error)
        self.assertEqual(controller.restarts, 1)

    def test_stopped_advertising_restarts_and_rotates_provider_generation(self) -> None:
        rotations = []
        monitor, controller = self.monitor(
            [{"advertising": "False", "authorized_subscriber": "False"}],
            on_provider_restart=lambda: rotations.append("rotated"),
        )

        status = monitor.poll_once()

        self.assertEqual(status.state, "engine_restarted")
        self.assertEqual(controller.restarts, 1)
        self.assertEqual(rotations, ["rotated"])

    def test_missing_advertising_state_is_an_engine_fault(self) -> None:
        monitor, controller = self.monitor([{"authorized_subscriber": "False"}])

        status = monitor.poll_once()

        self.assertEqual(status.state, "engine_restarted")
        self.assertIn("missing advertising state", status.last_error)
        self.assertEqual(controller.restarts, 1)

    def test_shutdown_race_does_not_rotate_provider_generation(self) -> None:
        rotations = []
        monitor, controller = self.monitor(
            [RuntimeError("channel lost")],
            controller=_StoppingController(),
            on_provider_restart=lambda: rotations.append("rotated"),
        )

        status = monitor.poll_once()

        self.assertEqual(status.state, "stopped")
        self.assertEqual(controller.restarts, 1)
        self.assertEqual(rotations, [])


if __name__ == "__main__":
    unittest.main()
