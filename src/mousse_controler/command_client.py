"""Small local client for the protected loopback command API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

from .dpapi import unprotect


def invoke(config_path: Path, command: str, arguments: dict | None = None) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    token = unprotect(config["command_token_dpapi"])
    payload = json.dumps({
        "command_id": str(uuid.uuid4()),
        "issued_at_ms": int(time.time() * 1000),
        "ttl_ms": 5_000,
        "command": command,
        "arguments": arguments or {},
    }, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{int(config.get('command_port', 8766))}/v1/command",
        data=payload,
        headers={
            "Authorization": "Bearer " + token.decode("utf-8"),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"command rejected ({exc.code}): {detail}") from exc
    finally:
        token = b"\0" * len(token)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("command")
    parser.add_argument("--arguments", type=Path)
    args = parser.parse_args()
    arguments = json.loads(args.arguments.read_text(encoding="utf-8")) if args.arguments else None
    print(json.dumps(invoke(args.config, args.command, arguments), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
