from __future__ import annotations

import time
import unittest

from mousse_controler.actions import ActionExecutor, ActionRegistry
from mousse_controler.command_server import CommandError, CommandGateway
from mousse_controler.controller import MouseController, PositionStore
from mousse_controler.controller import PositionSnapshot
from mousse_controler.transport import SimulatedHidTransport
from tests.support.waiting import wait_until


class ReceiverStub:
    def topology(self):
        raise AssertionError("not needed")


class CommandGatewayTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedHidTransport()
        self.controller = MouseController(self.transport, PositionStore())
        self.controller.start()
        self.registry = ActionRegistry()
        self.actions = ActionExecutor(self.controller, self.registry)
        self.gateway = CommandGateway(
            b"token", self.controller, self.transport, ReceiverStub(), self.actions)

    def tearDown(self):
        self.actions.close()

    def envelope(self, command="move", command_id="one", **arguments):
        return {
            "command_id": command_id,
            "issued_at_ms": int(time.time() * 1000),
            "ttl_ms": 1000,
            "command": command,
            "arguments": arguments,
        }

    def test_authorization_constant_contract(self):
        self.assertTrue(self.gateway.authorized("Bearer token"))
        self.assertFalse(self.gateway.authorized("Bearer wrong"))

    def test_duplicate_and_expired_commands_rejected(self):
        payload = self.envelope(dx=1, dy=2)
        self.gateway.execute(payload)
        with self.assertRaisesRegex(CommandError, "duplicate"):
            self.gateway.execute(payload)
        expired = self.envelope(command_id="old", dx=1, dy=2)
        expired["issued_at_ms"] -= 2000
        with self.assertRaisesRegex(CommandError, "expired"):
            self.gateway.execute(expired)

    def test_legacy_mouse_command_has_correlated_lifecycle(self):
        result = self.gateway.execute(self.envelope("click", "legacy-click", button_bit=1))
        self.assertEqual(result["action"]["action_id"], "legacy-click")
        self.assertEqual(result["action"]["state"], "EXECUTED")

    def test_action_submission_is_asynchronous_and_queryable(self):
        submitted = self.gateway.execute(self.envelope(
            "action_submit", "submit", action_id="new-action",
            action={"kind": "click", "button": "middle", "hold_seconds": 0},
        ))
        self.assertEqual(submitted["action"]["action_id"], "new-action")
        wait_until(
            lambda: self.registry.get("new-action")["state"]
            in {"EXECUTED", "FAILED", "UNKNOWN"},
            description="new action terminal state",
        )
        status = self.gateway.execute(self.envelope(
            "action_status", "status-new", action_id="new-action"))
        self.assertEqual(status["action"]["state"], "EXECUTED")

    def test_stop_releases_and_blocks_future_move(self):
        self.gateway.execute(self.envelope("buttons", "press", mask=1))
        self.gateway.execute(self.envelope("stop", "stop"))
        count = len(self.transport.events)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            self.gateway.execute(self.envelope("move", "after", dx=1, dy=1))
        self.assertEqual(len(self.transport.events), count)

    def test_transport_status_is_observable_without_hid_action(self):
        result = self.gateway.execute(self.envelope("transport_status", "status"))

        self.assertTrue(result["accepted"])
        self.assertEqual(result["status"]["buttons"], "0")

    def test_position_status_reports_fresh_sample_without_hid_action(self):
        self.controller._positions.update(PositionSnapshot(
            12, 34, 5, 1, "topology", int(time.time() * 1000), time.monotonic()
        ))

        result = self.gateway.execute(self.envelope("position_status", "position"))

        self.assertEqual((result["position"]["x"], result["position"]["y"]), (12, 34))
        self.assertLess(result["position"]["age_ms"], 100)
