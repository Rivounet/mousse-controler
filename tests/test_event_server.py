from __future__ import annotations

import base64
import json
import os
import socket
import struct
import threading
import unittest

from mousse_controler.actions import ActionRegistry, ActionState
from mousse_controler.event_server import EventWebSocketServer


class EventWebSocketTests(unittest.TestCase):
    def setUp(self):
        self.registry = ActionRegistry()
        self.server = EventWebSocketServer(("127.0.0.1", 0), b"secret", self.registry)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(1)

    def connect(self, token="secret"):
        client = socket.create_connection(self.server.server_address, timeout=1)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET /v1/events HTTP/1.1\r\n"
            "Host: 127.0.0.1\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Bearer {token}\r\n\r\n"
        ).encode("ascii")
        client.sendall(request)
        response = b""
        while b"\r\n\r\n" not in response:
            response += client.recv(1024)
        headers, remainder = response.split(b"\r\n\r\n", 1)
        return client, headers, remainder

    @staticmethod
    def frame(client, initial=b""):
        data = bytearray(initial)
        while len(data) < 2:
            data.extend(client.recv(4096))
        length = data[1] & 0x7F
        offset = 2
        if length == 126:
            while len(data) < 4:
                data.extend(client.recv(4096))
            length = struct.unpack("!H", data[2:4])[0]
            offset = 4
        elif length == 127:
            while len(data) < 10:
                data.extend(client.recv(4096))
            length = struct.unpack("!Q", data[2:10])[0]
            offset = 10
        while len(data) < offset + length:
            data.extend(client.recv(4096))
        return json.loads(bytes(data[offset:offset + length]).decode("utf-8"))

    def test_authentication_is_required(self):
        client, headers, _ = self.connect("wrong")
        try:
            self.assertIn(b"401 Unauthorized", headers)
        finally:
            client.close()

    def test_state_changes_are_pushed_with_unique_correlation(self):
        client, headers, remainder = self.connect()
        try:
            self.assertIn(b"101 Switching Protocols", headers)
            hello = self.frame(client, remainder)
            self.assertEqual(hello["protocol"], "mousse.actions.v1")
            self.registry.create("action-1", "click")
            accepted = self.frame(client)
            self.registry.transition("action-1", ActionState.RUNNING)
            running = self.frame(client)
            self.assertEqual(accepted["action"]["action_id"], "action-1")
            self.assertEqual(accepted["action"]["state"], "ACCEPTED")
            self.assertEqual(running["action"]["state"], "RUNNING")
            self.assertNotEqual(accepted["event_id"], running["event_id"])
            self.assertEqual(running["action"]["event_sequence"], 2)
        finally:
            client.close()

    def test_server_refuses_non_loopback_binding(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            EventWebSocketServer(("0.0.0.0", 0), b"secret", self.registry)


if __name__ == "__main__":
    unittest.main()
