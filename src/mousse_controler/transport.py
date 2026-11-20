"""HOGP transport boundary and deterministic simulation double."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import threading
from typing import Any


class TransportError(RuntimeError):
    """A transport command was rejected or could not be delivered."""


class HidTransport(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def move(self, dx: int, dy: int) -> None: ...

    @abstractmethod
    def buttons(self, mask: int) -> None: ...

    @abstractmethod
    def scroll(self, delta: int) -> None: ...

    @abstractmethod
    def release_all(self) -> None: ...


@dataclass
class SimulatedHidTransport(HidTransport):
    """Records commands; never touches an input device."""

    events: list[tuple[Any, ...]] = field(default_factory=list)
    started: bool = False
    buttons_mask: int = 0

    def start(self) -> None:
        self.started = True
        self.events.append(("start",))

    def stop(self) -> None:
        self.release_all()
        self.started = False
        self.events.append(("stop",))

    def _ready(self) -> None:
        if not self.started:
            raise TransportError("transport is stopped")

    def move(self, dx: int, dy: int) -> None:
        self._ready()
        if not -32768 <= dx <= 32767 or not -32768 <= dy <= 32767:
            raise ValueError("movement outside int16 bounds")
        self.events.append(("move", dx, dy, self.buttons_mask))

    def buttons(self, mask: int) -> None:
        self._ready()
        if not 0 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        self.buttons_mask = mask
        self.events.append(("buttons", mask))

    def scroll(self, delta: int) -> None:
        self._ready()
        if not -127 <= delta <= 127:
            raise ValueError("wheel outside int8 bounds")
        self.events.append(("scroll", delta, self.buttons_mask))

    def release_all(self) -> None:
        self.buttons_mask = 0
        self.events.append(("release",))

    def status(self) -> dict[str, str]:
        return {
            "prepared": str(self.started),
            "advertising": str(self.started),
            "subscribed": str(self.started),
            "buttons": str(self.buttons_mask),
        }


class NativeHogpTransport(HidTransport):
    """Serialized line protocol for the foreground packaged WinRT engine."""

    def __init__(self, executable: Path, startup_timeout: float = 15.0):
        self._executable = Path(executable)
        self._startup_timeout = startup_timeout
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def _engine_command(self) -> list[str]:
        if self._executable.name.lower() != "mousse-hogp-packaged.exe":
            return [str(self._executable), "--stdio"]
        package_script = (
            "$utf8=[System.Text.UTF8Encoding]::new($false);"
            "[Console]::InputEncoding=$utf8;[Console]::OutputEncoding=$utf8;"
            "$OutputEncoding=$utf8;"
            "$p=[Windows.ApplicationModel.Package,Windows,ContentType=WindowsRuntime]::"
            "Current.InstalledLocation.Path; & (Join-Path $p 'hogp.ps1') -Stdio"
        )
        return [
            str(self._executable),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            package_script,
        ]

    def _read_result(self) -> dict[str, Any]:
        assert self._process and self._process.stdout
        line = self._process.stdout.readline()
        if not line:
            code = self._process.poll()
            raise TransportError(f"HOGP engine closed output (exit={code})")
        try:
            result = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TransportError("invalid HOGP engine response") from exc
        if not result.get("ok"):
            raise TransportError(str(result.get("detail", "HOGP command failed")))
        return result

    def _command(self, command: str, expected: set[str] | None = None) -> dict[str, Any]:
        with self._lock:
            if not self._process or self._process.poll() is not None:
                raise TransportError("HOGP engine is not running")
            assert self._process.stdin
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()
            while True:
                result = self._read_result()
                if expected is None or result.get("event") in expected:
                    return result

    def start(self) -> None:
        if self._process and self._process.poll() is None:
            return
        self._process = subprocess.Popen(
            self._engine_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        self._read_result()  # prepared; does not advertise

    def advertise(self) -> None:
        self._command("advertise start", {"advertise-start", "advertisement"})

    def status(self) -> dict[str, str]:
        result = self._command("status", {"status"})
        fields: dict[str, str] = {}
        for item in str(result.get("detail", "")).split(","):
            name, separator, value = item.partition("=")
            if separator:
                fields[name.strip()] = value.strip()
        return fields

    def stop(self) -> None:
        process = self._process
        if not process:
            return
        try:
            self.release_all()
            self._command("stop", {"stopped"})
            process.wait(timeout=5)
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        finally:
            self._process = None

    def move(self, dx: int, dy: int) -> None:
        self._command(f"move {dx} {dy}", {"report"})

    def buttons(self, mask: int) -> None:
        self._command(f"buttons {mask}", {"report"})

    def scroll(self, delta: int) -> None:
        self._command(f"scroll {delta}", {"report"})

    def release_all(self) -> None:
        if self._process and self._process.poll() is None:
            self._command("release", {"release"})
