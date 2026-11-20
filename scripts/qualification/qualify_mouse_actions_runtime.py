"""Run bounded real mouse actions against the dedicated visible witness surface."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
import uuid

from mousse_controler.command_client import invoke
from mousse_controler.dpapi import unprotect


class EventClient:
    def __init__(self, config_path: Path):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        token = unprotect(config["command_token_dpapi"])
        self.socket = socket.create_connection(
            ("127.0.0.1", int(config.get("event_port", 8767))), timeout=5)
        self.socket.settimeout(15)
        self.buffer = bytearray()
        try:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = (
                "GET /v1/events HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{int(config.get('event_port', 8767))}\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                f"Authorization: Bearer {token.decode('ascii')}\r\n\r\n"
            ).encode("ascii")
            self.socket.sendall(request)
            response = bytearray()
            while b"\r\n\r\n" not in response:
                response.extend(self.socket.recv(4096))
            headers, remainder = bytes(response).split(b"\r\n\r\n", 1)
            if b"101 Switching Protocols" not in headers:
                raise RuntimeError("WebSocket upgrade failed")
            self.buffer.extend(remainder)
            opcode, payload = self.receive()
            hello = json.loads(payload.decode("utf-8"))
            if opcode != 1 or hello.get("protocol") != "mousse.actions.v1":
                raise RuntimeError("unexpected WebSocket hello")
        finally:
            token = b"\0" * len(token)

    def receive(self) -> tuple[int, bytes]:
        while len(self.buffer) < 2:
            self.buffer.extend(self.socket.recv(4096))
        opcode = self.buffer[0] & 0x0F
        length = self.buffer[1] & 0x7F
        offset = 2
        if length == 126:
            while len(self.buffer) < 4:
                self.buffer.extend(self.socket.recv(4096))
            length = struct.unpack("!H", self.buffer[2:4])[0]
            offset = 4
        elif length == 127:
            while len(self.buffer) < 10:
                self.buffer.extend(self.socket.recv(4096))
            length = struct.unpack("!Q", self.buffer[2:10])[0]
            offset = 10
        while len(self.buffer) < offset + length:
            self.buffer.extend(self.socket.recv(4096))
        payload = bytes(self.buffer[offset:offset + length])
        del self.buffer[:offset + length]
        return opcode, payload

    def states_until(self, action_id: str, expected: str) -> tuple[list[str], list[str]]:
        states: list[str] = []
        event_ids: list[str] = []
        while expected not in states:
            opcode, payload = self.receive()
            if opcode != 1:
                continue
            event = json.loads(payload.decode("utf-8"))
            action = event.get("action") or {}
            if action.get("action_id") != action_id:
                continue
            state = str(action.get("state"))
            states.append(state)
            event_ids.append(str(event["event_id"]))
            if state in {"FAILED", "UNKNOWN", "CANCELLED"}:
                raise RuntimeError(f"action {action_id} ended in {state}, expected {expected}")
        return states, event_ids

    def close(self) -> None:
        self.socket.close()


def qualify(config_path: Path, bounds: tuple[int, int, int, int], *, capture_only: bool = False,
            evidence_directory: Path | None = None) -> dict:
    x, y, width, height = bounds
    if width < 400 or height < 300:
        raise ValueError("witness surface is too small")
    center = (x + width // 2, y + height // 2)
    near = (center[0] + min(100, width // 5), center[1] + min(70, height // 5))
    client = EventClient(config_path)
    results: list[dict] = []
    all_event_ids: list[str] = []

    def run(label: str, spec: dict, *, confirmed: bool = False) -> dict:
        action_id = f"hardware-{label}-{uuid.uuid4()}"
        accepted = invoke(config_path, "action_submit", {
            "action_id": action_id, "action": spec,
        })
        expected = "CONFIRMED" if confirmed else "EXECUTED"
        states, event_ids = client.states_until(action_id, expected)
        all_event_ids.extend(event_ids)
        status = invoke(config_path, "action_status", {"action_id": action_id})["action"]
        item = {
            "label": label,
            "action_id": action_id,
            "accepted_state": accepted["action"]["state"],
            "websocket_states": states,
            "final_state": status["state"],
        }
        results.append(item)
        return status

    try:
        run("move-center", {"kind": "move_to", "x": center[0], "y": center[1]}, confirmed=True)
        if not capture_only:
            for count in (1, 2, 3):
                run(f"left-{count}", {"kind": "click", "button": "left", "count": count})
            for button in ("right", "middle", "back", "forward"):
                run(f"click-{button}", {"kind": "click", "button": button})
            run("press-combination", {"kind": "press", "buttons": ["left", "right"]})
            run("release-combination", {"kind": "release", "buttons": ["left", "right"]})
            run("hold", {"kind": "hold", "button": "left", "duration_seconds": 0.25})
            run("drag", {"kind": "drag", "button": "left", "x": near[0], "y": near[1]}, confirmed=True)
            run("return-center", {"kind": "move_to", "x": center[0], "y": center[1]}, confirmed=True)
            run("scroll-discrete", {"kind": "scroll", "delta": 120})
            run("scroll-continuous", {
                "kind": "scroll", "duration_seconds": 0.2,
                "interval_seconds": 0.05, "step": -1,
            })
            run("sequence", {"kind": "sequence", "actions": [
                {"kind": "wait", "duration_seconds": 0.1},
                {"kind": "move_relative", "dx": 5, "dy": 5},
                {"kind": "move_to", "x": center[0], "y": center[1]},
            ]})
        capture_status = run("capture", {
            "kind": "click", "button": "left",
            "capture": {"before": True, "after": True, "retention_seconds": 600,
                        "timeout_seconds": 10},
        })
        deadline = time.monotonic() + 15
        while True:
            captures = invoke(config_path, "capture_status", {
                "action_id": capture_status["action_id"],
            })["captures"]
            if len(captures) == 2 and all(
                    capture["state"] in {"STORED", "FAILED", "DELETED"}
                    for capture in captures):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("capture completion deadline exceeded")
            time.sleep(0.1)
        capture_proof = []
        for capture in captures:
            capture_proof.append({
                "capture_id": capture["capture_id"], "moment": capture["moment"],
                "state_before_delete": capture["state"],
                "content_type": capture["content_type"], "size_bytes": capture["size_bytes"],
                "monitor_dimensions": ({"width": capture["monitor"]["width"],
                                        "height": capture["monitor"]["height"]}
                                       if capture.get("monitor") else None),
            })
            try:
                if evidence_directory is not None:
                    repository = Path(__file__).resolve().parents[2]
                    evidence = evidence_directory.resolve()
                    if not evidence.is_relative_to(repository):
                        raise ValueError("capture evidence directory must be inside the repository")
                    monitor = capture.get("monitor") or {}
                    if capture["state"] != "STORED" or not capture.get("storage_path"):
                        raise RuntimeError("cannot export capture evidence that was not stored")
                    destination = evidence / f"capture-{capture['moment']}.png"
                    command = [
                        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(Path(__file__).with_name("Export-CaptureEvidence.ps1")),
                        "-SourcePath", str(capture["storage_path"]),
                        "-DestinationPath", str(destination),
                        "-X", str(x - int(monitor["x"])), "-Y", str(y - int(monitor["y"])),
                        "-Width", str(width), "-Height", str(height),
                    ]
                    exported = ""
                    for attempt in range(3):
                        try:
                            exported = subprocess.run(
                                command, check=True, capture_output=True, text=True).stdout.strip()
                            break
                        except subprocess.CalledProcessError as exc:
                            if attempt == 2:
                                detail = (exc.stderr or exc.stdout or "export failed")[-512:]
                                raise RuntimeError(
                                    f"capture evidence export failed: {detail}") from exc
                            time.sleep(0.25)
                    capture_proof[-1]["repository_evidence"] = json.loads(exported)
            finally:
                deleted = invoke(config_path, "capture_delete", {
                    "capture_id": capture["capture_id"],
                })["capture"]
                capture_proof[-1]["state_after_delete"] = deleted["state"]
        status = invoke(config_path, "transport_status")
        return {
            "phase": "captures" if capture_only else "actions",
            "safe_bounds": {"width": width, "height": height},
            "actions": results, "action_count": len(results),
            "websocket_event_ids_unique": len(all_event_ids) == len(set(all_event_ids)),
            "captures": capture_proof,
            "transport": status.get("status"),
        }
    finally:
        client.close()


def emergency(config_path: Path) -> dict:
    client = EventClient(config_path)
    action_id = f"hardware-emergency-{uuid.uuid4()}"
    try:
        accepted = invoke(config_path, "action_submit", {
            "action_id": action_id,
            "action": {"kind": "sequence", "actions": [
                {"kind": "wait", "duration_seconds": 2.0},
                {"kind": "click", "button": "left"},
            ]},
        })
        time.sleep(0.2)
        stop = invoke(config_path, "stop")
        time.sleep(0.2)
        status = invoke(config_path, "action_status", {"action_id": action_id})["action"]
        return {
            "phase": "emergency", "action_id": action_id,
            "accepted_state": accepted["action"]["state"],
            "stop_accepted": stop["accepted"], "final_state": status["state"],
            "error_code": status.get("error_code"),
        }
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--phase", choices=("actions", "captures", "emergency"),
                        default="actions")
    parser.add_argument("--bounds", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    parser.add_argument("--evidence-directory", type=Path)
    args = parser.parse_args()
    if args.phase in {"actions", "captures"}:
        if not args.bounds:
            parser.error("--bounds is required for actions and captures")
        result = qualify(args.config, tuple(args.bounds), capture_only=args.phase == "captures",
                         evidence_directory=args.evidence_directory)
    else:
        result = emergency(args.config)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
