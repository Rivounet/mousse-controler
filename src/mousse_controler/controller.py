"""Serialized mouse commands and feedback-based absolute positioning."""

from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time

from .transport import HidTransport


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


class PositionStore:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._latest: PositionSnapshot | None = None

    def update(self, snapshot: PositionSnapshot) -> None:
        with self._condition:
            if self._latest and snapshot.sequence <= self._latest.sequence:
                raise ValueError("position sequence did not advance")
            self._latest = snapshot
            self._condition.notify_all()

    def latest(self, max_age_ms: int = 150) -> PositionSnapshot:
        with self._condition:
            if self._latest is None:
                raise PositionError("no position sample")
            if self._latest.age_ms() > max_age_ms:
                raise PositionError("position sample is stale")
            return self._latest

    def wait_newer(self, sequence: int, timeout: float, max_age_ms: int = 150) -> PositionSnapshot:
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._latest is None or self._latest.sequence <= sequence:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PositionError("timed out waiting for fresh feedback")
                self._condition.wait(remaining)
            if self._latest.age_ms() > max_age_ms:
                raise PositionError("new feedback is stale")
            return self._latest


class MouseController:
    def __init__(self, transport: HidTransport, positions: PositionStore):
        self._transport = transport
        self._positions = positions
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._buttons = 0
        self._last_positioning_metrics: dict[str, float | int] = {}

    def positioning_metrics(self) -> dict[str, float | int]:
        with self._lock:
            return dict(self._last_positioning_metrics)

    def start(self) -> None:
        with self._lock:
            self._stopped.clear()
            self._transport.start()

    def is_stopped(self) -> bool:
        return self._stopped.is_set()

    def restart_transport(self) -> None:
        if self._stopped.is_set():
            return
        with self._lock:
            if self._stopped.is_set():
                return
            try:
                self._transport.release_all()
            finally:
                self._buttons = 0
                self._transport.stop()
            self._transport.start()
            advertise = getattr(self._transport, "advertise", None)
            if advertise is not None:
                advertise()

    def position_snapshot(self, max_age_ms: int = 150) -> PositionSnapshot:
        return self._positions.latest(max_age_ms)

    def emergency_stop(self) -> None:
        self._stopped.set()
        with self._lock:
            try:
                self._transport.release_all()
            finally:
                self._buttons = 0
                self._transport.stop()

    def move(self, dx: int, dy: int) -> None:
        if self._stopped.is_set():
            raise RuntimeError("controller is stopped")
        if not -32768 <= dx <= 32767 or not -32768 <= dy <= 32767:
            raise ValueError("movement outside int16 bounds")
        with self._lock:
            self._transport.move(dx, dy)

    def set_buttons(self, mask: int) -> None:
        if not 0 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        with self._lock:
            self._transport.buttons(mask)
            self._buttons = mask

    def click(self, button_bit: int, hold_seconds: float = 0.04) -> None:
        if button_bit not in (1, 2, 4, 8, 16):
            raise ValueError("invalid button")
        with self._lock:
            self._transport.buttons(self._buttons | button_bit)
            try:
                if self._stopped.wait(hold_seconds):
                    raise RuntimeError("controller stopped during click")
            finally:
                self._transport.buttons(self._buttons & ~button_bit)

    def scroll(self, delta: int) -> None:
        with self._lock:
            self._transport.scroll(delta)

    def move_to(
        self,
        target_x: int,
        target_y: int,
        *,
        tolerance_px: int = 2,
        timeout: float = 2.0,
        max_step: int = 48,
        proportional_gain: float = 0.35,
        adaptive_acceleration: bool = True,
        minimum_effective_step: int = 4,
        feedback_timeout: float = 0.25,
        pause_gate: threading.Event | None = None,
        pause_ack: threading.Event | None = None,
        cancel_event: threading.Event | None = None,
    ) -> PositionSnapshot:
        if (tolerance_px < 0 or timeout <= 0 or max_step <= 0 or
                not 0 < proportional_gain <= 1 or minimum_effective_step <= 0):
            raise ValueError("invalid positioning limits")
        started = time.perf_counter()
        deadline = time.monotonic() + timeout
        snapshot = self._positions.latest()
        initial_x, initial_y = snapshot.x, snapshot.y
        corrections = 0
        transport_seconds = 0.0
        feedback_seconds = 0.0
        previous_error: tuple[int, int] | None = None
        fine_mode = False
        expected_session = snapshot.session_id
        expected_topology = snapshot.topology_generation
        while True:
            if self._stopped.is_set():
                raise PositionError("positioning stopped")
            if cancel_event is not None and cancel_event.is_set():
                raise PositionError("positioning cancelled")
            if pause_gate is not None and not pause_gate.is_set():
                paused_at = time.monotonic()
                if pause_ack is not None:
                    pause_ack.set()
                while not pause_gate.wait(0.05):
                    if self._stopped.is_set():
                        raise PositionError("positioning stopped")
                    if cancel_event is not None and cancel_event.is_set():
                        raise PositionError("positioning cancelled")
                deadline += time.monotonic() - paused_at
                if pause_ack is not None:
                    pause_ack.clear()
            error_x = target_x - snapshot.x
            error_y = target_y - snapshot.y
            if math.hypot(error_x, error_y) <= tolerance_px:
                metrics: dict[str, float | int] = {
                    "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "corrections": corrections,
                    "transport_ms": round(transport_seconds * 1000.0, 3),
                    "feedback_wait_ms": round(feedback_seconds * 1000.0, 3),
                    "initial_distance_px": round(math.hypot(target_x - initial_x, target_y - initial_y), 3),
                    "final_error_px": round(math.hypot(error_x, error_y), 3),
                }
                with self._lock:
                    self._last_positioning_metrics = metrics
                return snapshot
            if time.monotonic() >= deadline:
                raise PositionError("positioning deadline exceeded")
            if (adaptive_acceleration and previous_error is not None and
                    error_x * previous_error[0] + error_y * previous_error[1] <= 0):
                fine_mode = True
            if adaptive_acceleration and not fine_mode:
                distance = math.hypot(error_x, error_y)
                if distance <= minimum_effective_step * 2:
                    command_length = max(minimum_effective_step, round(distance))
                else:
                    command_length = round(
                        distance * proportional_gain + minimum_effective_step * 2 + 1
                    )
                command_length = min(max_step, command_length)
                dx = round(command_length * error_x / distance)
                dy = round(command_length * error_y / distance)
                if dx == 0 and error_x:
                    dx = 1 if error_x > 0 else -1
                if dy == 0 and error_y:
                    dy = 1 if error_y > 0 else -1
            else:
                def correction(error: int) -> int:
                    if error == 0:
                        return 0
                    gain = 0.75 if fine_mode else proportional_gain
                    limit = min(max_step, 8) if fine_mode else max_step
                    scaled = max(1, round(abs(error) * gain))
                    return max(-limit, min(limit, scaled if error > 0 else -scaled))

                dx = correction(error_x)
                dy = correction(error_y)
            previous_error = (error_x, error_y)
            transport_started = time.perf_counter()
            self.move(dx, dy)
            transport_seconds += time.perf_counter() - transport_started
            corrections += 1
            wait = min(feedback_timeout, max(0.001, deadline - time.monotonic()))
            feedback_started = time.perf_counter()
            snapshot = self._positions.wait_newer(snapshot.sequence, wait)
            feedback_seconds += time.perf_counter() - feedback_started
            if snapshot.session_id != expected_session:
                raise PositionError("interactive session changed")
            if snapshot.topology_generation != expected_topology:
                raise PositionError("display topology changed")
