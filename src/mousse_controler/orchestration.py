"""Application-level ownership of the single mouse command lane."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time


class OperationBusyError(RuntimeError):
    """The mouse command lane is already owned by another operation."""


class OperationCancelled(RuntimeError):
    """A queued operation was cancelled before it acquired the command lane."""


@dataclass(frozen=True)
class OperationSnapshot:
    owner: str | None
    generation: int


class OperationLease:
    """Idempotent capability granting exclusive access to the command lane."""

    def __init__(self, coordinator: "OperationCoordinator", owner: str, generation: int) -> None:
        self._coordinator = coordinator
        self.owner = owner
        self.generation = generation
        self._closed = False
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._coordinator._release(self.owner, self.generation)

    def __enter__(self) -> "OperationLease":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()


class OperationCoordinator:
    """Serialize complete logical operations, not only individual HID reports."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._owner: str | None = None
        self._generation = 0

    def snapshot(self) -> OperationSnapshot:
        with self._condition:
            return OperationSnapshot(self._owner, self._generation)

    def acquire(
        self,
        owner: str,
        *,
        wait: bool,
        cancel_event: threading.Event | None = None,
        timeout: float | None = None,
    ) -> OperationLease:
        if not owner:
            raise ValueError("operation owner is required")
        if timeout is not None and timeout < 0:
            raise ValueError("operation timeout must be non-negative")
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while self._owner is not None:
                if cancel_event is not None and cancel_event.is_set():
                    raise OperationCancelled("operation cancelled before execution")
                if not wait:
                    raise OperationBusyError(f"mouse operation busy: {self._owner}")
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise OperationBusyError(f"mouse operation busy: {self._owner}")
                interval = 0.05 if remaining is None else min(0.05, remaining)
                self._condition.wait(interval)
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled("operation cancelled before execution")
            self._generation += 1
            self._owner = owner
            return OperationLease(self, owner, self._generation)

    def _release(self, owner: str, generation: int) -> None:
        with self._condition:
            if self._owner != owner or self._generation != generation:
                raise RuntimeError("operation lease is no longer current")
            self._owner = None
            self._condition.notify_all()
