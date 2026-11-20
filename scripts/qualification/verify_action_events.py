"""Verify the live authenticated WebSocket with a wait-only, non-HID action."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import os
import socket
import struct
import uuid

from mousse_controler.command_client import invoke
from mousse_controler.dpapi import unprotect


def receive_frame(connection: socket.socket, buffered: bytearray) -> tuple[int, bytes]:
    while len(buffered) < 2:
        buffered.extend(connection.recv(4096))
    opcode = buffered[0] & 0x0F
    length = buffered[1] & 0x7F
    offset = 2
    if length == 126:
        while len(buffered) < 4:
            buffered.extend(connection.recv(4096))
        length = struct.unpack("!H", buffered[2:4])[0]
        offset = 4
    elif length == 127:
        while len(buffered) < 10:
            buffered.extend(connection.recv(4096))
        length = struct.unpack("!Q", buffered[2:10])[0]
        offset = 10
    while len(buffered) < offset + length:
        buffered.extend(connection.recv(4096))
    payload = bytes(buffered[offset:offset + length])
    del buffered[:offset + length]
    return opcode, payload


def verify(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    token = unprotect(config["command_token_dpapi"])
    port = int(config.get("event_port", 8767))
    connection = socket.create_connection(("127.0.0.1", port), timeout=3)
    buffered = bytearray()
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET /v1/events HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Bearer {token.decode('ascii')}\r\n\r\n"
        ).encode("ascii")
        connection.sendall(request)
        response = bytearray()
        while b"\r\n\r\n" not in response:
            response.extend(connection.recv(4096))
            if len(response) > 16_384:
                raise RuntimeError("WebSocket handshake exceeded limit")
        headers, remainder = bytes(response).split(b"\r\n\r\n", 1)
        if b"101 Switching Protocols" not in headers:
            raise RuntimeError("WebSocket authentication or upgrade failed")
        buffered.extend(remainder)
        opcode, payload = receive_frame(connection, buffered)
        hello = json.loads(payload.decode("utf-8"))
        if opcode != 1 or hello.get("protocol") != "mousse.actions.v1":
            raise RuntimeError("unexpected WebSocket hello")

        action_id = "runtime-wait-" + str(uuid.uuid4())
        accepted = invoke(config_path, "action_submit", {
            "action_id": action_id,
            "action": {"kind": "wait", "duration_seconds": 0.2},
        })
        states = []
        event_ids = []
        while not states or states[-1] != "EXECUTED":
            opcode, payload = receive_frame(connection, buffered)
            if opcode == 9:
                continue
            event = json.loads(payload.decode("utf-8"))
            action = event.get("action") or {}
            if action.get("action_id") != action_id:
                continue
            states.append(action["state"])
            event_ids.append(event["event_id"])
            if len(states) > 10:
                raise RuntimeError("unexpected action event count")
        status = invoke(config_path, "action_status", {"action_id": action_id})
        return {
            "action_id": action_id,
            "accepted_state": accepted["action"]["state"],
            "websocket_states": states,
            "event_ids_unique": len(event_ids) == len(set(event_ids)),
            "final_state": status["action"]["state"],
            "hid_reports_requested": 0,
        }
    finally:
        token = b"\0" * len(token)
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.config), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
