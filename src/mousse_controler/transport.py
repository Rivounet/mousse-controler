"""HOGP transport boundary and deterministic simulation double."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any


class TransportError(RuntimeError):
    """A transport command was rejected or could not be delivered."""


class TransportTimeoutError(TransportError):
    """A bounded engine operation exceeded its deadline."""


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


@dataclass
class _WriteRequest:
    command: str
    completed: queue.Queue[BaseException | None] = field(default_factory=queue.Queue)


@dataclass
class _EngineChannel:
    process: subprocess.Popen[str]
    stdout: queue.Queue[str | BaseException | None] = field(default_factory=queue.Queue)
    writes: queue.Queue[_WriteRequest | None] = field(default_factory=queue.Queue)
    stderr_count: int = 0
    stderr_lock: threading.Lock = field(default_factory=threading.Lock)
    shutdown_lock: threading.Lock = field(default_factory=threading.Lock)
    shutdown_complete: threading.Event = field(default_factory=threading.Event)
    threads: list[threading.Thread] = field(default_factory=list)


class NativeHogpTransport(HidTransport):
    """Deadline-bounded line protocol for the foreground packaged WinRT engine."""

    _PACKAGED_ENGINES = {
        "mousse-hogp-packaged.exe",
        "mousse-hogp-qualification.exe",
    }

    def __init__(self, executable: Path, startup_timeout: float = 15.0,
                 command_timeout: float = 3.0, stop_timeout: float = 3.0,
                 termination_timeout: float = 2.0,
                 authorized_client_sha256: str | None = None):
        for name, value, maximum in (
            ("startup_timeout", startup_timeout, 60.0),
            ("command_timeout", command_timeout, 10.0),
            ("stop_timeout", stop_timeout, 10.0),
            ("termination_timeout", termination_timeout, 10.0),
        ):
            if not math.isfinite(value) or not 0 < value <= maximum:
                raise ValueError(f"{name} must be finite and in (0, {maximum}]")
        self._executable = Path(executable)
        self._startup_timeout = startup_timeout
        self._command_timeout = command_timeout
        self._stop_timeout = stop_timeout
        self._termination_timeout = termination_timeout
        if authorized_client_sha256 is not None:
            normalized_client = authorized_client_sha256.strip().upper()
            if (len(normalized_client) != 64 or
                    any(character not in "0123456789ABCDEF"
                        for character in normalized_client)):
                raise ValueError(
                    "authorized_client_sha256 must contain exactly 64 hex characters"
                )
            if self._executable.name.lower() not in self._PACKAGED_ENGINES:
                raise ValueError(
                    "authorized HOGP clients require the packaged WinRT engine"
                )
            self._authorized_client_sha256: str | None = normalized_client
        else:
            self._authorized_client_sha256 = None
        self._process: subprocess.Popen[str] | None = None
        self._channel: _EngineChannel | None = None
        self._failed_channel: _EngineChannel | None = None
        self._command_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._channel_state = "stopped"
        self._last_error: str | None = None
        self._last_exit_code: int | None = None
        self._last_stderr_lines = 0
        self._lingering_workers = 0
        self._termination_failed = False
        self._last_stop_outcome: str | None = None

    def _engine_command(self) -> list[str]:
        if self._executable.name.lower() not in self._PACKAGED_ENGINES:
            return [str(self._executable), "--stdio"]
        authorization = (
            " -AuthorizedClientSha256 '"
            + self._authorized_client_sha256
            + "'"
            if self._authorized_client_sha256 is not None else ""
        )
        package_script = (
            "$utf8=[System.Text.UTF8Encoding]::new($false);"
            "[Console]::InputEncoding=$utf8;[Console]::OutputEncoding=$utf8;"
            "$OutputEncoding=$utf8;"
            "$p=[Windows.ApplicationModel.Package,Windows,ContentType=WindowsRuntime]::"
            "Current.InstalledLocation.Path; & (Join-Path $p 'hogp.ps1') -Stdio"
            + authorization
        )
        return [
            str(self._executable),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            package_script,
        ]

    @staticmethod
    def _stdout_worker(channel: _EngineChannel) -> None:
        stream = channel.process.stdout
        assert stream is not None
        try:
            while True:
                line = stream.readline()
                if line == "":
                    break
                channel.stdout.put(line)
        except BaseException as exc:
            channel.stdout.put(exc)
        finally:
            channel.stdout.put(None)

    @staticmethod
    def _stderr_worker(channel: _EngineChannel) -> None:
        stream = channel.process.stderr
        assert stream is not None
        try:
            while True:
                line = stream.readline()
                if line == "":
                    return
                with channel.stderr_lock:
                    channel.stderr_count += 1
        except BaseException:
            return

    @staticmethod
    def _stdin_worker(channel: _EngineChannel) -> None:
        stream = channel.process.stdin
        assert stream is not None
        while True:
            request = channel.writes.get()
            if request is None:
                return
            try:
                stream.write(request.command + "\n")
                stream.flush()
            except BaseException as exc:
                request.completed.put(exc)
                return
            request.completed.put(None)

    def _start_workers(self, channel: _EngineChannel) -> None:
        workers = (
            ("stdout", self._stdout_worker),
            ("stderr", self._stderr_worker),
            ("stdin", self._stdin_worker),
        )
        for role, target in workers:
            thread = threading.Thread(
                target=target, args=(channel,), name=f"hogp-{role}", daemon=True,
            )
            channel.threads.append(thread)
            thread.start()

    @staticmethod
    def _remaining(deadline: float, operation: str) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TransportTimeoutError(f"HOGP {operation} timed out")
        return remaining

    def _read_result(self, channel: _EngineChannel | None = None,
                     deadline: float | None = None,
                     operation: str = "response") -> dict[str, Any]:
        if channel is None:
            channel = self._channel
        if channel is None:
            raise TransportError("HOGP engine is not running")
        if deadline is None:
            deadline = time.monotonic() + self._command_timeout
        try:
            item = channel.stdout.get(timeout=self._remaining(deadline, operation))
        except queue.Empty as exc:
            raise TransportTimeoutError(f"HOGP {operation} timed out") from exc
        if isinstance(item, BaseException):
            raise TransportError(f"HOGP output reader failed: {type(item).__name__}") from item
        if item is None:
            code = channel.process.poll()
            raise TransportError(f"HOGP engine closed output (exit={code})")
        try:
            result = json.loads(item)
        except json.JSONDecodeError as exc:
            raise TransportError("invalid HOGP engine response") from exc
        if not isinstance(result, dict):
            raise TransportError("invalid HOGP engine response")
        if not result.get("ok"):
            raise TransportError(str(result.get("detail", "HOGP command failed")))
        return result

    def _write_command(self, channel: _EngineChannel, command: str,
                       deadline: float) -> None:
        request = _WriteRequest(command)
        channel.writes.put_nowait(request)
        try:
            error = request.completed.get(
                timeout=self._remaining(deadline, f"write for {command.split()[0]}")
            )
        except queue.Empty as exc:
            raise TransportTimeoutError(
                f"HOGP write for {command.split()[0]} timed out"
            ) from exc
        if error is not None:
            raise TransportError(f"HOGP input writer failed: {type(error).__name__}") from error

    def _command(self, command: str, expected: set[str] | None = None,
                 timeout: float | None = None) -> dict[str, Any]:
        operation = command.split()[0]
        deadline = time.monotonic() + (self._command_timeout if timeout is None else timeout)
        if not self._command_lock.acquire(timeout=self._remaining(deadline, operation)):
            error = TransportTimeoutError(f"HOGP {operation} command lock timed out")
            channel = self._channel
            if channel is not None:
                self._invalidate(channel, str(error))
            raise error
        try:
            channel = self._channel
            if channel is None or channel.process.poll() is not None:
                raise TransportError("HOGP engine is not running")
            try:
                self._write_command(channel, command, deadline)
                while True:
                    result = self._read_result(channel, deadline, operation)
                    if expected is None or result.get("event") in expected:
                        return result
            except TransportError as exc:
                self._invalidate(channel, str(exc))
                raise
        finally:
            self._command_lock.release()

    def _shutdown_channel(self, channel: _EngineChannel) -> bool:
        if not channel.shutdown_lock.acquire(blocking=False):
            channel.shutdown_complete.wait(self._termination_timeout)
            return channel.process.poll() is None
        termination_failed = False
        try:
            channel.writes.put_nowait(None)
            process = channel.process
            deadline = time.monotonic() + self._termination_timeout
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=max(
                        0.001,
                        min(self._termination_timeout / 2, deadline - time.monotonic()),
                    ))
                except BaseException:
                    try:
                        process.kill()
                        remaining = deadline - time.monotonic()
                        if remaining > 0:
                            process.wait(timeout=remaining)
                    except BaseException:
                        termination_failed = True
                if process.poll() is None:
                    termination_failed = True
            if not termination_failed:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except BaseException:
                            pass
            for thread in channel.threads:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                thread.join(remaining)
            with channel.stderr_lock:
                stderr_count = channel.stderr_count
            lingering = sum(thread.is_alive() for thread in channel.threads)
            with self._lifecycle_lock:
                self._last_exit_code = process.poll()
                self._last_stderr_lines = stderr_count
                self._lingering_workers = lingering
                self._termination_failed = termination_failed
        finally:
            channel.shutdown_complete.set()
            channel.shutdown_lock.release()
        return termination_failed

    def _invalidate(self, channel: _EngineChannel, reason: str) -> None:
        with self._lifecycle_lock:
            if self._channel is channel:
                self._channel = None
                self._process = None
                self._channel_state = "invalid"
                self._last_error = reason
        termination_failed = self._shutdown_channel(channel)
        with self._lifecycle_lock:
            if termination_failed:
                self._failed_channel = channel
            elif self._failed_channel is channel:
                self._failed_channel = None

    def recovery_status(self) -> dict[str, Any]:
        with self._lifecycle_lock:
            channel = self._channel
            stderr_lines = self._last_stderr_lines
            if channel is not None:
                with channel.stderr_lock:
                    stderr_lines = channel.stderr_count
            return {
                "channel_state": self._channel_state,
                "last_error": self._last_error,
                "process_exit_code": self._last_exit_code,
                "stderr_lines_drained": stderr_lines,
                "lingering_workers": self._lingering_workers,
                "termination_failed": self._termination_failed,
                "last_stop_outcome": self._last_stop_outcome,
                "recovery_required": (
                    self._failed_channel is not None and
                    self._failed_channel.process.poll() is None
                ),
            }

    def start(self) -> None:
        with self._start_lock:
            self._start_once()

    def _start_once(self) -> None:
        failed_channel = self._failed_channel
        if failed_channel is not None:
            termination_failed = self._shutdown_channel(failed_channel)
            with self._lifecycle_lock:
                if not termination_failed and self._failed_channel is failed_channel:
                    self._failed_channel = None
            if termination_failed:
                raise TransportError(
                    "previous HOGP engine termination failed; recovery required"
                )
        with self._lifecycle_lock:
            if self._channel is not None and self._channel.process.poll() is None:
                return
            self._channel_state = "starting"
            self._last_error = None
            self._last_exit_code = None
            self._last_stderr_lines = 0
            self._lingering_workers = 0
            self._termination_failed = False
            self._last_stop_outcome = None
        try:
            process = subprocess.Popen(
                self._engine_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        except BaseException as exc:
            with self._lifecycle_lock:
                self._channel_state = "invalid"
                self._last_error = f"HOGP engine launch failed: {type(exc).__name__}"
            raise TransportError(self._last_error) from exc
        channel = _EngineChannel(process)
        with self._lifecycle_lock:
            self._channel = channel
            self._process = process
        self._start_workers(channel)
        try:
            self._read_result(
                channel, time.monotonic() + self._startup_timeout, "startup",
            )
        except TransportError as exc:
            self._invalidate(channel, str(exc))
            raise
        with self._lifecycle_lock:
            if self._channel is not channel:
                raise TransportError("HOGP engine was stopped during startup")
            self._channel_state = "ready"

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
        with self._stop_lock:
            channel = self._channel
            if channel is None:
                failed_channel = self._failed_channel
                if failed_channel is None:
                    return
                termination_failed = self._shutdown_channel(failed_channel)
                with self._lifecycle_lock:
                    if not termination_failed and self._failed_channel is failed_channel:
                        self._failed_channel = None
                        self._channel_state = "stopped"
                        self._last_stop_outcome = "forced"
                if termination_failed:
                    with self._lifecycle_lock:
                        self._channel_state = "invalid"
                        self._last_stop_outcome = "failed"
                    raise TransportError(
                        "HOGP stop failed: process termination requires recovery"
                    )
                return
            deadline = time.monotonic() + self._stop_timeout
            error: BaseException | None = None
            try:
                self._command(
                    "release", {"release"},
                    timeout=self._remaining(deadline, "stop release"),
                )
                self._command(
                    "stop", {"stopped"},
                    timeout=self._remaining(deadline, "stop command"),
                )
                channel.process.wait(timeout=self._remaining(deadline, "process exit"))
            except BaseException as exc:
                error = exc
            with self._lifecycle_lock:
                if self._channel is channel:
                    self._channel = None
                    self._process = None
            termination_failed = self._shutdown_channel(channel)
            with self._lifecycle_lock:
                if termination_failed:
                    self._failed_channel = channel
                    self._channel_state = "invalid"
                    self._last_stop_outcome = "failed"
                    self._last_error = (
                        str(error) if error is not None
                        else "HOGP process termination failed"
                    )
                elif self._failed_channel is channel:
                    self._failed_channel = None
                if not termination_failed:
                    self._channel_state = "stopped"
                    self._last_stop_outcome = "clean" if error is None else "forced"
                    self._last_error = None if error is None else str(error)
            if termination_failed:
                detail = f": {error}" if error is not None else ""
                raise TransportError(
                    f"HOGP stop failed: process termination requires recovery{detail}"
                ) from error
            if error is not None and not isinstance(error, Exception):
                raise error

    def move(self, dx: int, dy: int) -> None:
        self._command(f"move {dx} {dy}", {"report"})

    def buttons(self, mask: int) -> None:
        self._command(f"buttons {mask}", {"report"})

    def scroll(self, delta: int) -> None:
        self._command(f"scroll {delta}", {"report"})

    def release_all(self) -> None:
        if self._channel is not None and self._channel.process.poll() is None:
            self._command("release", {"release"})
