"""Foreground runtime for HOGP, loopback commands and HTTPS feedback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import threading
import time

from .command_server import CommandGateway, make_command_server
from .controller import MouseController, PositionStore
from .dpapi import protect, unprotect
from .position_server import PositionReceiver, make_https_server
from .security import HmacVerifier
from .transport import NativeHogpTransport


def serve(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = PositionStore()
    keys = {key_id: unprotect(value) for key_id, value in config["agent_keys_dpapi"].items()}
    receiver = PositionReceiver(store, HmacVerifier(keys))
    transport = NativeHogpTransport(Path(config["hogp_executable"]))
    controller = MouseController(transport, store)
    controller.start()
    transport.advertise()
    gateway = CommandGateway(unprotect(config["command_token_dpapi"]), controller, transport, receiver)
    position_server = make_https_server(
        config["position_bind"], int(config["position_port"]), receiver,
        config["tls_certificate"], config["tls_private_key"],
    )
    command_server = make_command_server(int(config.get("command_port", 8766)), gateway)
    threads = [
        threading.Thread(target=position_server.serve_forever, name="position-https", daemon=True),
        threading.Thread(target=command_server.serve_forever, name="command-loopback", daemon=True),
    ]
    for thread in threads:
        thread.start()
    stopped = threading.Event()

    def maintain_hogp() -> None:
        disconnected_since: float | None = None
        refresh_seconds = float(config.get("hogp_reconnect_refresh_seconds", 30.0))
        while not stopped.wait(5.0):
            if controller.is_stopped():
                return
            try:
                status = transport.status()
                if status.get("subscribed", "").lower() == "true":
                    disconnected_since = None
                    continue
                now = time.monotonic()
                if disconnected_since is None:
                    disconnected_since = now
                elif now - disconnected_since >= refresh_seconds:
                    controller.restart_transport()
                    disconnected_since = time.monotonic()
            except Exception as exc:
                print(f"HOGP reconnect maintenance pending: {exc}", file=sys.stderr, flush=True)

    maintenance = threading.Thread(target=maintain_hogp, name="hogp-maintenance", daemon=True)
    maintenance.start()

    def stop_handler(signum, frame):
        stopped.set()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)
    print("Mousse controller ready; GATT advertising active.", flush=True)
    print(f"Position HTTPS: {config['position_bind']}:{config['position_port']}", flush=True)
    print(f"Command API: 127.0.0.1:{config.get('command_port', 8766)}", flush=True)
    try:
        stopped.wait()
    finally:
        stopped.set()
        maintenance.join(timeout=6)
        position_server.shutdown()
        command_server.shutdown()
        controller.emergency_stop()
        for secret in keys.values():
            if isinstance(secret, bytearray):
                secret[:] = b"\0" * len(secret)
    return 0


def serve_position_only(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = PositionStore()
    keys = {key_id: unprotect(value) for key_id, value in config["agent_keys_dpapi"].items()}
    receiver = PositionReceiver(store, HmacVerifier(keys))
    server = make_https_server(
        config["position_bind"], int(config["position_port"]), receiver,
        config["tls_certificate"], config["tls_private_key"],
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
