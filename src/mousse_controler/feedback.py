"""Atomic position and display-topology feedback shared by application layers."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from .geometry import DesktopTopology


class PositionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PositionSnapshot:
    x: int
    y: int
    sequence: int
    session_id: int
    topology_generation: str
    observed_at_unix_ms: int
    received_monotonic: float

    def age_ms(self, now: float | None = None) -> float:
        current = time.monotonic() if now is None else now
        return max(0.0, (current - self.received_monotonic) * 1000.0)


@dataclass(frozen=True)
class FeedbackSnapshot:
    position: PositionSnapshot
    topology: DesktopTopology


class PositionStore:
    """Publish feedback generations atomically and provide bounded waits."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._latest: PositionSnapshot | None = None
        self._topology: DesktopTopology | None = None

    def update(
        self,
        snapshot: PositionSnapshot,
        topology: DesktopTopology | None = None,
    ) -> None:
        if topology is not None and topology.generation != snapshot.topology_generation:
            raise ValueError("position and topology generations differ")
        with self._condition:
            if self._latest and snapshot.sequence <= self._latest.sequence:
                raise ValueError("position sequence did not advance")
            self._latest = snapshot
            if topology is not None:
                self._topology = topology
            self._condition.notify_all()

    def latest(self, max_age_ms: int = 150) -> PositionSnapshot:
        with self._condition:
            return self._latest_locked(max_age_ms)

    def feedback(self, max_age_ms: int | None = 150) -> FeedbackSnapshot:
        with self._condition:
            if self._latest is None:
                raise PositionError("no position sample")
            if max_age_ms is not None and self._latest.age_ms() > max_age_ms:
                raise PositionError("position sample is stale")
            if self._topology is None:
                raise PositionError("display topology has not been received")
            if self._topology.generation != self._latest.topology_generation:
                raise PositionError("position and topology generations differ")
            return FeedbackSnapshot(self._latest, self._topology)

    def wait_fresh(
        self,
        timeout: float,
        max_age_ms: int = 150,
        interrupt_events: tuple[threading.Event, ...] = (),
    ) -> PositionSnapshot:
        """Return a fresh sample, waiting for the next publication when needed."""
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                if any(event.is_set() for event in interrupt_events):
                    raise PositionError("position feedback wait interrupted")
                if self._latest is not None and self._latest.age_ms() <= max_age_ms:
                    return self._latest
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if self._latest is None:
                        raise PositionError("no position sample")
                    raise PositionError("position sample is stale")
                self._condition.wait(min(remaining, 0.02) if interrupt_events else remaining)

    def wait_newer(
        self,
        sequence: int,
        timeout: float,
        max_age_ms: int = 150,
        interrupt_events: tuple[threading.Event, ...] = (),
    ) -> PositionSnapshot:
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._latest is None or self._latest.sequence <= sequence:
                if any(event.is_set() for event in interrupt_events):
                    raise PositionError("position feedback wait interrupted")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PositionError("timed out waiting for fresh feedback")
                self._condition.wait(min(remaining, 0.02) if interrupt_events else remaining)
            if any(event.is_set() for event in interrupt_events):
                raise PositionError("position feedback wait interrupted")
            if self._latest.age_ms() > max_age_ms:
                raise PositionError("new feedback is stale")
            return self._latest

    def _latest_locked(self, max_age_ms: int) -> PositionSnapshot:
        if self._latest is None:
            raise PositionError("no position sample")
        if self._latest.age_ms() > max_age_ms:
            raise PositionError("position sample is stale")
        return self._latest
