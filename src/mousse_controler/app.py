"""Foreground runtime for HOGP, loopback commands and HTTPS feedback."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import signal
import sys
import threading
from typing import Any, Callable

from .actions import ActionExecutor, ActionRegistry
from .application import MouseApplicationService
from .capture import CaptureBroker
from .command_server import CommandGateway, make_command_server
from .controller import MouseController, PositionStore
from .dpapi import protect, unprotect
from .event_server import make_event_server
from .hogp_control import (
    HogpControlCoordinator,
    HogpControlPolicy,
    HogpControlReceiver,
)
from .hogp_health import HogpHealthMonitor
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
                 command_token: bytes | bytearray,
                 keys: dict[str, bytes | bytearray]) -> None:
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


@dataclass(frozen=True)
class RuntimeFactories:
    """Explicit process boundaries used to assemble a runtime."""

    unprotect_secret: Callable[[str], bytes]
    transport: Callable[..., Any]
    position_server: Callable[..., Any]
    command_server: Callable[..., Any]
    event_server: Callable[..., Any]


@dataclass(frozen=True)
class RuntimeAssembly:
    """Fully wired runtime, before any process or server is started."""

    config: dict[str, Any]
    store: PositionStore
    receiver: PositionReceiver
    transport: Any
    controller: MouseController
    capture_broker: CaptureBroker
    registry: ActionRegistry
    actions: ActionExecutor
    application: MouseApplicationService
    gateway: CommandGateway
    hogp_control: HogpControlCoordinator | None
    lifecycle: _RuntimeLifecycle
    factories: RuntimeFactories


def _default_runtime_factories() -> RuntimeFactories:
    # Resolve globals at call time so boundary replacements remain explicit and
    # existing characterization tests can still patch process integrations.
    return RuntimeFactories(
        unprotect_secret=unprotect,
        transport=NativeHogpTransport,
        position_server=make_https_server,
        command_server=make_command_server,
        event_server=make_event_server,
    )


def _hogp_control_policy(config: dict[str, Any]) -> HogpControlPolicy | None:
    selected = config.get("hogp_control")
    if selected is None:
        return None
    if not isinstance(selected, dict):
        raise ValueError("hogp_control must be an object")
    enabled = selected.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("hogp_control.enabled must be boolean")
    if not enabled:
        return None
    for name in ("allow_adapter_restart", "allow_endpoint_restart"):
        if not isinstance(selected.get(name, False), bool):
            raise ValueError(f"hogp_control.{name} must be boolean")
    string_values: dict[str, str] = {}
    for name in (
        "target_key_id", "target_aep_sha256", "adapter_instance_sha256",
        "paired_pnp_instance_sha256", "hid_pnp_instance_sha256",
    ):
        value = selected.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"hogp_control.{name} must be a string")
        string_values[name] = value
    integer_values: dict[str, int] = {}
    for name, default in (
        ("command_ttl_seconds", 60),
        ("command_cooldown_seconds", 300),
        ("endpoint_recovery_grace_seconds", 30),
    ):
        value = selected.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"hogp_control.{name} must be an integer")
        integer_values[name] = value
    policy = HogpControlPolicy(
        target_key_id=string_values["target_key_id"],
        target_aep_sha256=string_values["target_aep_sha256"],
        adapter_instance_sha256=string_values["adapter_instance_sha256"],
        paired_pnp_instance_sha256=string_values["paired_pnp_instance_sha256"],
        hid_pnp_instance_sha256=string_values["hid_pnp_instance_sha256"],
        allow_adapter_restart=selected.get("allow_adapter_restart", False),
        allow_endpoint_restart=selected.get("allow_endpoint_restart", False),
        command_ttl_seconds=integer_values["command_ttl_seconds"],
        command_cooldown_seconds=integer_values["command_cooldown_seconds"],
        endpoint_recovery_grace_seconds=integer_values[
            "endpoint_recovery_grace_seconds"
        ],
    )
    agent_keys = config.get("agent_keys_dpapi")
    if not isinstance(agent_keys, dict) or policy.target_key_id not in agent_keys:
        raise ValueError("hogp_control target key is not configured")
    return policy


def _hogp_control_key_id(config: dict[str, Any]) -> str | None:
    selected = config.get("hogp_control")
    if selected is None:
        return None
    if not isinstance(selected, dict):
        raise ValueError("hogp_control must be an object")
    value = selected.get("target_key_id")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("hogp_control.target_key_id must be a non-empty string")
    agent_keys = config.get("agent_keys_dpapi")
    if not isinstance(agent_keys, dict) or value not in agent_keys:
        raise ValueError("hogp_control target key is not configured")
    return value


def _route_keysets(
    keys: dict[str, bytearray], control_key_id: str | None,
) -> tuple[dict[str, bytearray], dict[str, bytearray] | None]:
    if control_key_id is None:
        return keys, None
    control_secret = keys[control_key_id]
    if any(
        key_id != control_key_id and secret == control_secret
        for key_id, secret in keys.items()
    ):
        raise ValueError("hogp_control secret must be distinct from telemetry secrets")
    return (
        {
            key_id: secret for key_id, secret in keys.items()
            if key_id != control_key_id
        },
        {control_key_id: control_secret},
    )


def _wipe_runtime_secrets(
    keys: dict[str, bytearray], command_token: bytearray | None = None,
) -> None:
    if command_token is not None:
        command_token[:] = b"\0" * len(command_token)
    for secret in keys.values():
        secret[:] = b"\0" * len(secret)


def build_runtime(
    config_path: Path, *, factories: RuntimeFactories | None = None,
) -> RuntimeAssembly:
    """Compose the application without starting its transport or servers."""

    selected = factories or _default_runtime_factories()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    control_policy = _hogp_control_policy(config)
    control_key_id = _hogp_control_key_id(config)
    store = PositionStore()
    keys: dict[str, bytearray] = {}
    try:
        for key_id, value in config["agent_keys_dpapi"].items():
            keys[key_id] = bytearray(selected.unprotect_secret(value))
    except BaseException:
        _wipe_runtime_secrets(keys)
        raise
    try:
        position_keys, control_keys = _route_keysets(keys, control_key_id)
    except BaseException:
        _wipe_runtime_secrets(keys)
        raise
    try:
        capture_broker = CaptureBroker(
            Path(config.get("capture_directory", str(config_path.parent / "captures"))),
            max_pending=int(config.get("capture_max_pending", 64)),
            max_records=int(config.get("capture_max_records", 2048)),
            max_bytes=int(config.get("capture_max_bytes", 16 * 1024 * 1024)),
            max_total_bytes=int(config.get(
                "capture_max_total_bytes", 512 * 1024 * 1024,
            )),
        )
        position_verifier = HmacVerifier(position_keys)
        transport = selected.transport(
            Path(config["hogp_executable"]),
            startup_timeout=float(config.get("hogp_startup_timeout_seconds", 15.0)),
            command_timeout=float(config.get("hogp_command_timeout_seconds", 3.0)),
            stop_timeout=float(config.get("hogp_stop_timeout_seconds", 3.0)),
            termination_timeout=float(config.get(
                "hogp_termination_timeout_seconds", 2.0,
            )),
            authorized_client_sha256=config.get("hogp_authorized_client_sha256"),
        )
        hogp_control = None
        hogp_control_receiver = None
        if control_policy is not None:
            assert control_keys is not None
            hogp_control = HogpControlCoordinator(control_policy, transport.status)
            hogp_control_receiver = HogpControlReceiver(
                HmacVerifier(control_keys),
                hogp_control,
            )
        receiver = PositionReceiver(
            store, position_verifier, capture_broker, hogp_control_receiver,
        )
        controller = MouseController(transport, store)
        command_token = bytearray(
            selected.unprotect_secret(config["command_token_dpapi"])
        )
    except BaseException:
        _wipe_runtime_secrets(keys)
        raise

    actions: ActionExecutor | None = None
    try:
        registry = ActionRegistry(
            max_records=int(config.get("action_max_records", 2048)),
            max_subscribers=int(config.get("event_max_subscribers", 16)),
            journal_path=Path(config.get(
                "action_journal", str(config_path.parent / "action-journal.jsonl"),
            )),
            action_id_retention_seconds=int(config.get(
                "action_id_retention_seconds", 2_592_000,
            )),
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
    except BaseException as exc:
        cleanup_errors: list[tuple[str, BaseException]] = []
        if actions is not None:
            try:
                actions.close()
            except BaseException as cleanup_exc:
                cleanup_errors.append(("actions close", cleanup_exc))
        _wipe_runtime_secrets(keys, command_token)
        if cleanup_errors:
            raise RuntimeCleanupError(exc, cleanup_errors) from exc
        raise
    try:
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
    except BaseException as exc:
        cleanup_errors = lifecycle.close()
        if cleanup_errors:
            raise RuntimeCleanupError(exc, cleanup_errors) from exc
        raise
    return RuntimeAssembly(
        config=config,
        store=store,
        receiver=receiver,
        transport=transport,
        controller=controller,
        capture_broker=capture_broker,
        registry=registry,
        actions=actions,
        application=application,
        gateway=gateway,
        hogp_control=hogp_control,
        lifecycle=lifecycle,
        factories=selected,
    )


def register_runtime_servers(runtime: RuntimeAssembly) -> None:
    """Create and register all protocol servers on an assembled runtime."""

    config = runtime.config
    lifecycle = runtime.lifecycle
    lifecycle.add_server("position-https", runtime.factories.position_server(
        config["position_bind"], int(config["position_port"]), runtime.receiver,
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
    lifecycle.add_server(
        "command-loopback",
        runtime.factories.command_server(
            int(config.get("command_port", 8766)), runtime.gateway,
        ),
    )
    lifecycle.add_server(
        "events-websocket",
        runtime.factories.event_server(
            int(config.get("event_port", 8767)),
            lifecycle.command_token,
            runtime.registry,
        ),
    )


def serve(config_path: Path) -> int:
    runtime = build_runtime(config_path)
    config = runtime.config
    transport = runtime.transport
    controller = runtime.controller
    lifecycle = runtime.lifecycle
    primary_error: BaseException | None = None
    try:
        fault_recovery_seconds = _bounded_interval(
            config, "hogp_fault_recovery_seconds", 5.0, 3600.0,
        )
        health_poll_seconds = _bounded_interval(
            config, "hogp_health_poll_seconds", 30.0, 300.0,
        )
        controller.start()
        transport.advertise()
        register_runtime_servers(runtime)

        for name in ("position-https", "command-loopback", "events-websocket"):
            lifecycle.start_server(name)

        health_monitor = HogpHealthMonitor(
            controller,
            transport,
            lifecycle.stopped,
            poll_seconds=health_poll_seconds,
            fault_recovery_seconds=fault_recovery_seconds,
            logger=lambda message: print(message, file=sys.stderr, flush=True),
            on_provider_restart=(
                runtime.hogp_control.rotate_provider_generation
                if runtime.hogp_control is not None else None
            ),
        )

        lifecycle.maintenance = threading.Thread(
            target=health_monitor.run, name="hogp-maintenance", daemon=True,
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
    control_policy = _hogp_control_policy(config)
    control_key_id = _hogp_control_key_id(config)
    store = PositionStore()
    keys: dict[str, bytearray] = {}
    server = None
    try:
        for key_id, value in config["agent_keys_dpapi"].items():
            keys[key_id] = bytearray(unprotect(value))
        position_keys, _ = _route_keysets(keys, control_key_id)
        receiver = PositionReceiver(store, HmacVerifier(position_keys))
        server = make_https_server(
            config["position_bind"], int(config["position_port"]), receiver,
            config["tls_certificate"], config["tls_private_key"],
            max_connections=int(config.get("position_max_connections", 8)),
            request_queue_size=int(config.get("position_request_queue_size", 8)),
            tls_handshake_timeout=float(config.get(
                "position_tls_handshake_timeout_seconds", 3.0)),
            header_timeout=float(config.get(
                "position_header_timeout_seconds", 2.0,
            )),
            header_total_timeout=float(config.get(
                "position_header_total_timeout_seconds", 5.0,
            )),
            body_timeout=float(config.get("position_body_timeout_seconds", 5.0)),
            body_total_timeout=float(config.get(
                "position_body_total_timeout_seconds", 10.0,
            )),
            capture_body_total_timeout=float(config.get(
                "position_capture_body_total_timeout_seconds", 120.0,
            )),
            write_timeout=float(config.get(
                "position_write_timeout_seconds", 2.0,
            )),
        )
    except BaseException:
        _wipe_runtime_secrets(keys)
        raise
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
        assert server is not None
        try:
            server.server_close()
        finally:
            _wipe_runtime_secrets(keys)
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
