"""Foreground runtime for HOGP, loopback commands and HTTPS feedback."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import signal
import sys
import threading
import time

from .actions import ActionExecutor, ActionRegistry
from .application import MouseApplicationService
from .capture import CaptureBroker
from .command_server import CommandGateway, make_command_server
from .controller import MouseController, PositionStore
from .dpapi import protect, unprotect
from .event_server import make_event_server
from .position_server import PositionReceiver, make_https_server
from .orchestration import OperationCoordinator
from .security import HmacVerifier
from .transport import NativeHogpTransport


class RuntimeCleanupError(RuntimeError):
    def __init__(self, primary: BaseException | None,
                 cleanup_errors: list[tuple[str, BaseException]]) -> None:
        self.primary = primary
        self.cleanup_errors = tuple(cleanup_errors)
        parts = []
        if primary is not None:
            parts.append(f"primary failure: {primary}")
        parts.extend(f"{label}: {error}" for label, error in cleanup_errors)
        super().__init__("runtime cleanup failed; " + "; ".join(parts))


def _bounded_interval(
    config: dict[str, object], name: str, default: float, maximum: float,
) -> float:
    value = float(config.get(name, default))
    if not math.isfinite(value) or not 0.1 <= value <= maximum:
        raise ValueError(
            f"{name} must be finite and between 0.1 and {maximum} seconds"
        )
    return value


class _RuntimeLifecycle:
    """Small, idempotent resource stack for the foreground runtime."""

    def __init__(self, actions: ActionExecutor, controller: MouseController,
                 command_token: bytes, keys: dict[str, bytes]) -> None:
        self.actions = actions
        self.controller = controller
        self.command_token = command_token
        self.keys = keys
        self.stopped = threading.Event()
        self.servers: list[dict[str, object]] = []
        self.maintenance: threading.Thread | None = None
        self.closed = False

    def add_server(self, name: str, server: object) -> object:
        self.servers.append({"name": name, "server": server, "thread": None})
        return server

    def start_server(self, name: str) -> None:
        entry = next(item for item in self.servers if item["name"] == name)
        server = entry["server"]
        thread = threading.Thread(
            target=server.serve_forever, name=name, daemon=True,
        )
        thread.start()
        entry["thread"] = thread

    def close(self) -> list[tuple[str, BaseException]]:
        if self.closed:
            return []
        self.closed = True
        errors: list[tuple[str, BaseException]] = []

        def attempt(label: str, operation) -> None:
            try:
                operation()
            except BaseException as exc:
                errors.append((label, exc))

        def join_bounded(thread: threading.Thread, label: str) -> None:
            thread.join(timeout=6)
            if thread.is_alive():
                raise RuntimeError(f"{label} did not stop within 6 seconds")

        attempt("stop event", self.stopped.set)
        if self.maintenance is not None:
            attempt(
                "maintenance thread join",
                lambda: join_bounded(self.maintenance, "maintenance thread"),
            )
        for entry in reversed(self.servers):
            name = str(entry["name"])
            server = entry["server"]
            thread = entry["thread"]
            if thread is not None:
                attempt(f"{name} shutdown", lambda current=server: current.shutdown())
                attempt(
                    f"{name} thread join",
                    lambda current=thread, current_name=name: join_bounded(
                        current, current_name,
                    ),
                )
            attempt(f"{name} server_close", lambda current=server: current.server_close())
        attempt("actions close", self.actions.close)
        attempt("controller emergency_stop", self.controller.emergency_stop)
        if isinstance(self.command_token, bytearray):
            self.command_token[:] = b"\0" * len(self.command_token)
        for secret in self.keys.values():
            if isinstance(secret, bytearray):
                secret[:] = b"\0" * len(secret)
        return errors


def serve(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = PositionStore()
    keys = {key_id: unprotect(value) for key_id, value in config["agent_keys_dpapi"].items()}
    capture_broker = CaptureBroker(
        Path(config.get("capture_directory", str(config_path.parent / "captures"))),
        max_pending=int(config.get("capture_max_pending", 64)),
        max_records=int(config.get("capture_max_records", 2048)),
        max_bytes=int(config.get("capture_max_bytes", 16 * 1024 * 1024)),
        max_total_bytes=int(config.get("capture_max_total_bytes", 512 * 1024 * 1024)),
    )
    receiver = PositionReceiver(store, HmacVerifier(keys), capture_broker)
    transport = NativeHogpTransport(
        Path(config["hogp_executable"]),
        startup_timeout=float(config.get("hogp_startup_timeout_seconds", 15.0)),
        command_timeout=float(config.get("hogp_command_timeout_seconds", 3.0)),
        stop_timeout=float(config.get("hogp_stop_timeout_seconds", 3.0)),
        termination_timeout=float(config.get("hogp_termination_timeout_seconds", 2.0)),
    )
    controller = MouseController(transport, store)
    command_token = unprotect(config["command_token_dpapi"])
    registry = ActionRegistry(
        max_records=int(config.get("action_max_records", 2048)),
        max_subscribers=int(config.get("event_max_subscribers", 16)),
        journal_path=Path(config.get(
            "action_journal", str(config_path.parent / "action-journal.jsonl"))),
        action_id_retention_seconds=int(config.get(
            "action_id_retention_seconds", 2_592_000)),
    )
    coordinator = OperationCoordinator()
    actions = ActionExecutor(
        controller,
        registry,
        capture_broker,
        max_queue=int(config.get("action_queue_size", 256)),
        coordinator=coordinator,
    )
    lifecycle = _RuntimeLifecycle(actions, controller, command_token, keys)
    primary_error: BaseException | None = None
    try:
        refresh_seconds = _bounded_interval(
            config, "hogp_reconnect_refresh_seconds", 30.0, 3600.0,
        )
        fault_recovery_seconds = _bounded_interval(
            config, "hogp_fault_recovery_seconds", 5.0, 3600.0,
        )
        health_poll_seconds = _bounded_interval(
            config, "hogp_health_poll_seconds", 30.0, 300.0,
        )
        controller.start()
        transport.advertise()
        application = MouseApplicationService(
            controller,
            transport,
            receiver,
            actions,
            capture_broker,
            coordinator,
        )
        gateway = CommandGateway(
            command_token,
            controller,
            transport,
            receiver,
            actions,
            capture_broker,
            application,
        )
        position_server = lifecycle.add_server("position-https", make_https_server(
            config["position_bind"], int(config["position_port"]), receiver,
            config["tls_certificate"], config["tls_private_key"],
            max_connections=int(config.get("position_max_connections", 8)),
            request_queue_size=int(config.get("position_request_queue_size", 8)),
            tls_handshake_timeout=float(config.get(
                "position_tls_handshake_timeout_seconds", 3.0)),
            header_timeout=float(config.get("position_header_timeout_seconds", 2.0)),
            header_total_timeout=float(config.get(
                "position_header_total_timeout_seconds", 5.0)),
            body_timeout=float(config.get("position_body_timeout_seconds", 5.0)),
            body_total_timeout=float(config.get(
                "position_body_total_timeout_seconds", 10.0)),
            capture_body_total_timeout=float(config.get(
                "position_capture_body_total_timeout_seconds", 120.0)),
            write_timeout=float(config.get("position_write_timeout_seconds", 2.0)),
        ))
        command_server = lifecycle.add_server(
            "command-loopback",
            make_command_server(int(config.get("command_port", 8766)), gateway),
        )
        event_server = lifecycle.add_server(
            "events-websocket",
            make_event_server(int(config.get("event_port", 8767)), command_token, registry),
        )

        for name in ("position-https", "command-loopback", "events-websocket"):
            lifecycle.start_server(name)

        def maintain_hogp() -> None:
            disconnected_since: float | None = None
            last_fault_recovery: float | None = None
            while not lifecycle.stopped.wait(health_poll_seconds):
                if controller.is_stopped():
                    return
                try:
                    status = transport.status()
                    if status.get("subscribed", "").lower() == "true":
                        disconnected_since = None
                        last_fault_recovery = None
                        continue
                    now = time.monotonic()
                    if disconnected_since is None:
                        disconnected_since = now
                    elif now - disconnected_since >= refresh_seconds:
                        controller.restart_transport()
                        disconnected_since = time.monotonic()
                except Exception as exc:
                    print(f"HOGP reconnect maintenance pending: {exc}", file=sys.stderr, flush=True)
                    now = time.monotonic()
                    if (last_fault_recovery is None or
                            now - last_fault_recovery >= fault_recovery_seconds):
                        last_fault_recovery = now
                        try:
                            controller.restart_transport()
                            disconnected_since = None
                        except Exception as recovery_exc:
                            print(
                                f"HOGP fault recovery failed: {recovery_exc}",
                                file=sys.stderr,
                                flush=True,
                            )

        lifecycle.maintenance = threading.Thread(
            target=maintain_hogp, name="hogp-maintenance", daemon=True,
        )
        lifecycle.maintenance.start()

        def stop_handler(signum, frame):
            lifecycle.stopped.set()

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)
        print("Mousse controller ready; GATT advertising active.", flush=True)
        print(f"Position HTTPS: {config['position_bind']}:{config['position_port']}", flush=True)
        print(f"Command API: 127.0.0.1:{config.get('command_port', 8766)}", flush=True)
        print(f"Action events: ws://127.0.0.1:{config.get('event_port', 8767)}/v1/events", flush=True)
        lifecycle.stopped.wait()
    except BaseException as exc:
        primary_error = exc
    cleanup_errors = lifecycle.close()
    if primary_error is not None:
        if cleanup_errors:
            raise RuntimeCleanupError(primary_error, cleanup_errors) from primary_error
        raise primary_error
    if cleanup_errors:
        raise RuntimeCleanupError(None, cleanup_errors)
    return 0


def serve_position_only(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = PositionStore()
    keys = {key_id: unprotect(value) for key_id, value in config["agent_keys_dpapi"].items()}
    receiver = PositionReceiver(store, HmacVerifier(keys))
    server = make_https_server(
        config["position_bind"], int(config["position_port"]), receiver,
        config["tls_certificate"], config["tls_private_key"],
        max_connections=int(config.get("position_max_connections", 8)),
        request_queue_size=int(config.get("position_request_queue_size", 8)),
        tls_handshake_timeout=float(config.get(
            "position_tls_handshake_timeout_seconds", 3.0)),
        header_timeout=float(config.get("position_header_timeout_seconds", 2.0)),
        header_total_timeout=float(config.get(
            "position_header_total_timeout_seconds", 5.0)),
        body_timeout=float(config.get("position_body_timeout_seconds", 5.0)),
        body_total_timeout=float(config.get(
            "position_body_total_timeout_seconds", 10.0)),
        capture_body_total_timeout=float(config.get(
            "position_capture_body_total_timeout_seconds", 120.0)),
        write_timeout=float(config.get("position_write_timeout_seconds", 2.0)),
    )
    proof_emitted = threading.Event()

    def report_first_sample() -> None:
        while not proof_emitted.wait(0.1):
            try:
                sample = store.latest(max_age_ms=5_000)
                topology = receiver.topology()
            except (ValueError, RuntimeError):
                continue
            print(
                "Position sample accepted: "
                f"sequence={sample.sequence}, session={sample.session_id}, "
                f"display_count={len(topology.displays)}, fresh=true",
                flush=True,
            )
            proof_emitted.set()

    threading.Thread(target=report_first_sample, name="position-proof", daemon=True).start()
    print(f"Position HTTPS ready: {config['position_bind']}:{config['position_port']}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        proof_emitted.set()
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    run = subparsers.add_parser("serve")
    run.add_argument("--config", type=Path, required=True)
    position = subparsers.add_parser("position-only")
    position.add_argument("--config", type=Path, required=True)
    subparsers.add_parser("protect-secret")
    args = parser.parse_args(argv)
    if args.action == "protect-secret":
        secret = sys.stdin.buffer.readline().rstrip(b"\r\n")
        if not secret:
            raise SystemExit("secret is empty")
        print(protect(secret))
        return 0
    if args.action == "position-only":
        return serve_position_only(args.config)
    return serve(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
