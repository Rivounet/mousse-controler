"""Authenticated loopback command API with TTL and idempotency guards."""

from __future__ import annotations

from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
import time
from typing import Any

from .actions import ActionState
from .controller import MouseController
from .geometry import CircleZone, PolygonZone, RectangleZone
from .sequence import SequenceRunner, SequenceStep, WaitMode
from .trajectory import TrajectoryConfig, TrajectoryEngine


MAX_COMMAND_BYTES = 8192


class CommandError(ValueError):
    pass


class CommandGateway:
    def __init__(self, token: bytes, controller: MouseController, transport: Any,
                 position_receiver: Any, action_executor: Any | None = None,
                 capture_broker: Any | None = None):
        self._token = token
        self._controller = controller
        self._transport = transport
        self._receiver = position_receiver
        self._actions = action_executor
        self._captures = capture_broker
        self._seen: dict[str, int] = {}
        self._lock = threading.Lock()
        self._sequence: SequenceRunner | None = None
        self._window_started = time.monotonic()
        self._window_count = 0

    def authorized(self, authorization: str) -> bool:
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            return False
        return hmac.compare_digest(authorization[len(prefix):].encode("utf-8"), self._token)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._validate_envelope(payload)
            command = str(payload.get("command", ""))
            arguments = payload.get("arguments") or {}
            if command == "advertise_start":
                self._transport.advertise()
            elif command == "transport_status":
                status = getattr(self._transport, "status", None)
                if status is None:
                    raise CommandError("transport status is unavailable")
                return {"accepted": True, "command": command, "status": status()}
            elif command == "position_status":
                snapshot = self._controller.position_snapshot(max_age_ms=5_000)
                return {
                    "accepted": True,
                    "command": command,
                    "position": {
                        "x": snapshot.x,
                        "y": snapshot.y,
                        "sequence": snapshot.sequence,
                        "session_id": snapshot.session_id,
                        "topology_generation": snapshot.topology_generation,
                        "observed_at_unix_ms": snapshot.observed_at_unix_ms,
                        "age_ms": round((time.monotonic() - snapshot.received_monotonic) * 1000, 3),
                    },
                }
            elif command == "position_metrics":
                metrics = getattr(self._receiver, "metrics", None)
                if metrics is None:
                    raise CommandError("position metrics are unavailable")
                return {"accepted": True, "command": command, "metrics": metrics()}
            elif command == "move":
                tracked = self._tracked_legacy(
                    str(payload["command_id"]), command,
                    lambda: self._controller.move(int(arguments["dx"]), int(arguments["dy"])))
                if tracked is not None:
                    return {"accepted": True, "command": command, "action": tracked}
            elif command == "click":
                tracked = self._tracked_legacy(
                    str(payload["command_id"]), command,
                    lambda: self._controller.click(int(arguments["button_bit"])))
                if tracked is not None:
                    return {"accepted": True, "command": command, "action": tracked}
            elif command == "buttons":
                tracked = self._tracked_legacy(
                    str(payload["command_id"]), command,
                    lambda: self._controller.set_buttons(int(arguments["mask"])))
                if tracked is not None:
                    return {"accepted": True, "command": command, "action": tracked}
            elif command == "scroll":
                tracked = self._tracked_legacy(
                    str(payload["command_id"]), command,
                    lambda: self._controller.scroll(int(arguments["delta"])))
                if tracked is not None:
                    return {"accepted": True, "command": command, "action": tracked}
            elif command == "stop":
                if self._actions is not None:
                    self._actions.emergency_stop()
                else:
                    self._controller.emergency_stop()
            elif command == "capabilities":
                if self._actions is None:
                    return {
                        "accepted": True, "command": command,
                        "capabilities": {
                            "buttons": {"left": 1, "right": 2, "middle": 4, "back": 8, "forward": 16},
                            "vertical_wheel": True, "horizontal_wheel": False,
                        },
                    }
                return {"accepted": True, "command": command,
                        "capabilities": self._actions.capabilities()}
            elif command == "action_submit":
                actions = self._require_actions()
                record = actions.submit(arguments["action"], action_id=arguments.get("action_id"))
                return {"accepted": True, "command": command, "action": record}
            elif command == "action_status":
                record = self._require_actions().registry.get(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "action": record}
            elif command == "action_list":
                records = self._require_actions().registry.list(int(arguments.get("limit", 100)))
                return {"accepted": True, "command": command, "actions": records}
            elif command == "action_cancel":
                record = self._require_actions().cancel(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "action": record}
            elif command == "action_pause":
                event = self._require_actions().pause(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "event": event}
            elif command == "action_resume":
                event = self._require_actions().resume(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "event": event}
            elif command == "action_continue":
                event = self._require_actions().advance(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "event": event}
            elif command == "action_events":
                events = self._require_actions().registry.history(
                    arguments.get("after_event_id"), int(arguments.get("limit", 100)))
                return {"accepted": True, "command": command, "events": events}
            elif command == "capture_status":
                captures = self._require_captures().list_for_action(str(arguments["action_id"]))
                return {"accepted": True, "command": command, "captures": captures}
            elif command == "capture_delete":
                capture = self._require_captures().delete(str(arguments["capture_id"]))
                return {"accepted": True, "command": command, "capture": capture}
            elif command == "sequence_start":
                self._start_sequence(arguments)
            elif command == "sequence_pause":
                self._require_sequence().pause()
            elif command == "sequence_resume":
                self._require_sequence().resume()
            elif command == "sequence_next":
                self._require_sequence().next_target()
            elif command == "sequence_skip":
                self._require_sequence().skip_target()
            elif command == "sequence_stop":
                self._require_sequence().stop()
            elif command == "sequence_status":
                return self._sequence_status()
            else:
                raise CommandError("unknown command")
            return {"accepted": True, "command": command}

    def _require_actions(self):
        if self._actions is None:
            raise CommandError("action engine is unavailable")
        return self._actions

    def _require_captures(self):
        if self._captures is None:
            raise CommandError("capture subsystem is unavailable")
        return self._captures

    def _tracked_legacy(self, action_id: str, kind: str, callback):
        if self._actions is None:
            callback()
            return None
        registry = self._actions.registry
        registry.create(action_id, kind)
        registry.transition(action_id, ActionState.RUNNING)
        try:
            callback()
        except Exception as exc:
            registry.transition(action_id, ActionState.UNKNOWN,
                                error_code="LEGACY_ACTION_UNCERTAIN", error=str(exc))
            raise
        registry.transition(action_id, ActionState.EXECUTED,
                            result={"legacy_command": True})
        return registry.get(action_id)

    def _validate_envelope(self, payload: dict[str, Any]) -> None:
        now = int(time.time() * 1000)
        command_id = str(payload.get("command_id", ""))
        issued = int(payload.get("issued_at_ms", -1))
        ttl = int(payload.get("ttl_ms", -1))
        if not command_id or len(command_id) > 128:
            raise CommandError("invalid command id")
        if ttl < 1 or ttl > 5000 or issued > now + 1000 or now > issued + ttl:
            raise CommandError("command expired or invalid")
        if command_id in self._seen:
            raise CommandError("duplicate command id")
        current = time.monotonic()
        if current - self._window_started >= 1.0:
            self._window_started, self._window_count = current, 0
        self._window_count += 1
        if self._window_count > 200:
            raise CommandError("command rate exceeded")
        self._seen[command_id] = now + ttl
        self._seen = {key: expiry for key, expiry in self._seen.items() if expiry >= now}
        if len(self._seen) > 2048:
            raise CommandError("idempotency cache capacity exceeded")

    @staticmethod
    def _zone(data: dict[str, Any]):
        kind = data.get("type")
        if kind == "rectangle":
            return RectangleZone(int(data["x"]), int(data["y"]), int(data["width"]), int(data["height"]))
        if kind == "circle":
            return CircleZone(int(data["center_x"]), int(data["center_y"]), int(data["radius"]))
        if kind == "polygon":
            return PolygonZone([(int(p[0]), int(p[1])) for p in data["vertices"]])
        raise CommandError("unknown zone type")

    def _start_sequence(self, arguments: dict[str, Any]) -> None:
        if self._sequence and self._sequence.status().state.value not in ("COMPLETED", "STOPPED", "ERROR"):
            raise CommandError("a sequence is already active")
        steps = [SequenceStep(
            self._zone(item["zone"]),
            WaitMode(item.get("wait_mode", "automatic")),
            float(item.get("wait_seconds", 0)),
        ) for item in arguments["steps"]]
        config = TrajectoryConfig(**arguments.get("trajectory", {}))
        self._sequence = SequenceRunner(
            self._controller, TrajectoryEngine(config), self._receiver.topology(), steps,
            seed=arguments.get("seed"),
        )
        self._sequence.start()

    def _require_sequence(self) -> SequenceRunner:
        if self._sequence is None:
            raise CommandError("no sequence")
        return self._sequence

    def _sequence_status(self) -> dict[str, Any]:
        status = self._require_sequence().status()
        return {
            "sequence_id": status.sequence_id,
            "state": status.state.value,
            "current_index": status.current_index,
            "target": status.target,
            "measured_position": status.measured_position,
            "wait_mode": status.wait_mode.value if status.wait_mode else None,
            "error": status.error,
            "started_at": status.started_at,
            "updated_at": status.updated_at,
            "results": [asdict(result) for result in status.results],
        }


def handler_factory(gateway: CommandGateway):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MousseCommand/1"

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/command":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not gateway.authorized(self.headers.get("Authorization", "")):
                self.send_error(HTTPStatus.UNAUTHORIZED)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_COMMAND_BYTES:
                    raise CommandError("invalid body length")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = gateway.execute(payload)
                body = json.dumps(result, separators=(",", ":")).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (CommandError, RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                body = json.dumps({"error": str(exc)}, separators=(",", ":")).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def make_command_server(port: int, gateway: CommandGateway) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_factory(gateway))
    server.daemon_threads = True
    server.request_queue_size = 8
    return server
