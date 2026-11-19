from __future__ import annotations

import time
import unittest

from mousse_controler.command_server import CommandError, CommandGateway
from mousse_controler.controller import MouseController, PositionStore
from mousse_controler.transport import SimulatedHidTransport


class ReceiverStub:
    def topology(self):
        raise AssertionError("not needed")


class CommandGatewayTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedHidTransport()
        self.controller = MouseController(self.transport, PositionStore())
        self.controller.start()
        self.gateway = CommandGateway(b"token", self.controller, self.transport, ReceiverStub())

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

    def test_stop_releases_and_blocks_future_move(self):
        self.gateway.execute(self.envelope("buttons", "press", mask=1))
        self.gateway.execute(self.envelope("stop", "stop"))
        count = len(self.transport.events)
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            self.gateway.execute(self.envelope("move", "after", dx=1, dy=1))
        self.assertEqual(len(self.transport.events), count)
