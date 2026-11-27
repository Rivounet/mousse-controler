"""Authenticated loopback command API with TTL and idempotency guards."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
import time
from typing import Any

from .application import ApplicationError, MouseApplicationService
from .api_catalog import build_catalog, command_contract, validate_parameters
from .controller import MouseController


MAX_COMMAND_BYTES = 8192


class CommandError(ValueError):
    pass


class CommandGateway:
    def __init__(self, token: bytes, controller: MouseController, transport: Any,
                 position_receiver: Any, action_executor: Any | None = None,
                 capture_broker: Any | None = None,
                 application: MouseApplicationService | None = None):
        self._token = token
        self._application = application or MouseApplicationService(
            controller, transport, position_receiver, action_executor, capture_broker,
        )
        self._seen: dict[str, int] = {}
        self._envelope_lock = threading.Lock()
        self._window_started = time.monotonic()
        self._window_count = 0

    @property
    def _sequence(self) -> Any | None:
        return self._application.sequence

    @_sequence.setter
    def _sequence(self, value: Any | None) -> None:
        self._application.sequence = value

    def authorized(self, authorization: str) -> bool:
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            return False
        return hmac.compare_digest(authorization[len(prefix):].encode("utf-8"), self._token)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._envelope_lock:
            self._validate_envelope(payload)
        command = str(payload.get("command", ""))
        arguments = payload.get("arguments") or {}
        contract = command_contract(command)
        if contract is None:
            raise CommandError("unknown command")
        validate_parameters(arguments, contract)
        try:
            result = getattr(self, contract["_handler"])(payload, arguments)
        except ApplicationError as exc:
            raise CommandError(str(exc)) from exc
        return result or {"accepted": True, "command": command}

    def _command_api_catalog(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        catalog = build_catalog(
            name=arguments.get("name"), category=arguments.get("category"),
            include=arguments.get("include"),
            availability=self._application.availability,
        )
        return {"accepted": True, "command": "api_catalog", **catalog}

    def _command_advertise_start(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.advertise_start()

    def _command_transport_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "command": "transport_status",
                "status": self._application.transport_status()}

    def _command_position_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "command": "position_status",
                "position": self._application.position_status()}

    def _command_position_metrics(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "command": "position_metrics",
                "metrics": self._application.position_metrics()}

    def _command_move(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        tracked = self._application.move(
            str(payload["command_id"]), int(arguments["dx"]), int(arguments["dy"]),
        )
        return ({"accepted": True, "command": "move", "action": tracked}
                if tracked is not None else None)

    def _command_click(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        tracked = self._application.click(str(payload["command_id"]), int(arguments["button_bit"]))
        return ({"accepted": True, "command": "click", "action": tracked}
                if tracked is not None else None)

    def _command_buttons(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        tracked = self._application.buttons(str(payload["command_id"]), int(arguments["mask"]))
        return ({"accepted": True, "command": "buttons", "action": tracked}
                if tracked is not None else None)

    def _command_scroll(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any] | None:
        tracked = self._application.scroll(str(payload["command_id"]), int(arguments["delta"]))
        return ({"accepted": True, "command": "scroll", "action": tracked}
                if tracked is not None else None)

    def _command_stop(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.stop()

    def _command_capabilities(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "command": "capabilities",
                "capabilities": self._application.capabilities()}

    def _command_action_submit(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._application.submit_action(arguments["action"], arguments.get("action_id"))
        return {"accepted": True, "command": "action_submit", "action": record}

    def _command_action_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._application.action_status(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_status", "action": record}

    def _command_action_list(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        records = self._application.action_list(int(arguments.get("limit", 100)))
        return {"accepted": True, "command": "action_list", "actions": records}

    def _command_action_cancel(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._application.cancel_action(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_cancel", "action": record}

    def _command_action_pause(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._application.pause_action(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_pause", "event": event}

    def _command_action_resume(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._application.resume_action(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_resume", "event": event}

    def _command_action_continue(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        event = self._application.advance_action(str(arguments["action_id"]))
        return {"accepted": True, "command": "action_continue", "event": event}

    def _command_action_events(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        events = self._application.action_events(
            arguments.get("after_event_id"), int(arguments.get("limit", 100)),
        )
        return {"accepted": True, "command": "action_events", "events": events}

    def _command_capture_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        captures = self._application.capture_status(str(arguments["action_id"]))
        return {"accepted": True, "command": "capture_status", "captures": captures}

    def _command_capture_delete(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        capture = self._application.capture_delete(str(arguments["capture_id"]))
        return {"accepted": True, "command": "capture_delete", "capture": capture}

    def _command_sequence_start(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.start_sequence(arguments)

    def _command_sequence_pause(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.pause_sequence()

    def _command_sequence_resume(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.resume_sequence()

    def _command_sequence_next(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.advance_sequence()

    def _command_sequence_skip(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.skip_sequence()

    def _command_sequence_stop(self, payload: dict[str, Any], arguments: dict[str, Any]) -> None:
        self._application.stop_sequence()

    def _command_sequence_status(self, payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
        return self._application.sequence_status()

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
