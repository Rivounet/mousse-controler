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
from .api_catalog import build_catalog, command_contract, validate_parameters
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
            contract = command_contract(command)
            if contract is None:
                raise CommandError("unknown command")
            validate_parameters(arguments, contract)
            result = getattr(self, contract["_handler"])(payload, arguments)
            return result or {"accepted": True, "command": command}

    def _command_api_catalog(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        catalog = build_catalog(
            name=arguments.get("name"), category=arguments.get("category"),
            include=arguments.get("include"),
            availability={"actions": self._actions is not None, "captures": self._captures is not None},
        )
        return {"accepted": True, "command": "api_catalog", **catalog}

    def _command_advertise_start(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._transport.advertise()

    def _command_transport_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        status = getattr(self._transport, "status", None)
        if status is None:
            raise CommandError("transport status is unavailable")
        return {"accepted": True, "command": "transport_status", "status": status()}

    def _command_position_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._controller.position_snapshot(max_age_ms=5_000)
        return {
            "accepted": True, "command": "position_status",
            "position": {
                "x": snapshot.x, "y": snapshot.y, "sequence": snapshot.sequence,
                "session_id": snapshot.session_id,
                "topology_generation": snapshot.topology_generation,
                "observed_at_unix_ms": snapshot.observed_at_unix_ms,
                "age_ms": round((time.monotonic() - snapshot.received_monotonic) * 1000, 3),
            },
        }

    def _command_position_metrics(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        metrics = getattr(self._receiver, "metrics", None)
        if metrics is None:
            raise CommandError("position metrics are unavailable")
        return {"accepted": True, "command": "position_metrics", "metrics": metrics()}

    def _legacy(self, payload: dict[str, Any], command: str, callback) -> dict[str, Any] | None:
        tracked = self._tracked_legacy(str(payload["command_id"]), command, callback)
        if tracked is not None:
            return {"accepted": True, "command": command, "action": tracked}
        return None

    def _command_move(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        return self._legacy(payload, "move", lambda: self._controller.move(
            int(arguments["dx"]), int(arguments["dy"])))

    def _command_click(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        return self._legacy(payload, "click", lambda: self._controller.click(
            int(arguments["button_bit"])))

    def _command_buttons(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        return self._legacy(payload, "buttons", lambda: self._controller.set_buttons(
            int(arguments["mask"])))

    def _command_scroll(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        return self._legacy(payload, "scroll", lambda: self._controller.scroll(
            int(arguments["delta"])))

    def _command_stop(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        errors: list[str] = []
        if self._actions is not None:
            try:
                self._actions.request_stop()
            except Exception as exc:
                errors.append(f"actions: {exc}")
        if self._sequence is not None:
            try:
                self._sequence.request_stop()
            except Exception as exc:
                errors.append(f"sequence: {exc}")
        try:
            self._controller.emergency_stop()
        except Exception as exc:
            errors.append(f"controller: {exc}")
        if errors:
            raise CommandError("global stop completed with errors: " + "; ".join(errors))

    def _command_capabilities(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        if self._actions is None:
            capabilities = {
                "buttons": {"left": 1, "right": 2, "middle": 4, "back": 8, "forward": 16},
                "vertical_wheel": True, "horizontal_wheel": False,
            }
        else:
            capabilities = self._actions.capabilities()
        return {"accepted": True, "command": "capabilities", "capabilities": capabilities}

    def _command_action_submit(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._require_actions().submit(
            arguments["action"], action_id=arguments.get("action_id"))
        return {"accepted": True, "command": "action_submit", "action": record}

    def _command_action_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._require_actions().registry.get(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_status", "action": record}

    def _command_action_list(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        records = self._require_actions().registry.list(int(arguments.get("limit", 100)))
        return {"accepted": True, "command": "action_list", "actions": records}

    def _command_action_cancel(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._require_actions().cancel(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_cancel", "action": record}

    def _command_action_pause(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._require_actions().pause(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_pause", "event": event}

    def _command_action_resume(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._require_actions().resume(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_resume", "event": event}

    def _command_action_continue(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._require_actions().advance(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_continue", "event": event}

    def _command_action_events(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        events = self._require_actions().registry.history(
            arguments.get("after_event_id"), int(arguments.get("limit", 100)))
        return {"accepted": True, "command": "action_events", "events": events}

    def _command_capture_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        captures = self._require_captures().list_for_action(str(arguments["action_id"]))
        return {"accepted": True, "command": "capture_status", "captures": captures}

    def _command_capture_delete(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        capture = self._require_captures().delete(str(arguments["capture_id"]))
        return {"accepted": True, "command": "capture_delete", "capture": capture}

    def _command_sequence_start(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._start_sequence(arguments)

    def _command_sequence_pause(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._require_sequence().pause()

    def _command_sequence_resume(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._require_sequence().resume()

    def _command_sequence_next(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._require_sequence().next_target()

    def _command_sequence_skip(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._require_sequence().skip_target()

    def _command_sequence_stop(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._require_sequence().stop()

    def _command_sequence_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return self._sequence_status()

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
