"""Serialized mouse commands and feedback-based absolute positioning."""

from __future__ import annotations

import math
import threading
import time

from .feedback import PositionError, PositionSnapshot, PositionStore
from .transport import HidTransport

class PositioningError(PositionError):
    """A bounded feedback move failed, with explicit HID emission evidence."""

    def __init__(self, message: str, *, code: str, emitted: bool,
                 metrics: dict[str, float | int | str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.emitted = emitted
        self.metrics = dict(metrics or {})

class MouseController:
    def __init__(self, transport: HidTransport, positions: PositionStore):
        self._transport = transport
        self._positions = positions
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._stopped.set()
        self._transport_stopped = True
        self._buttons = 0
        self._last_positioning_metrics: dict[str, float | int | str] = {}

    def _ensure_running_locked(self) -> None:
        if self._stopped.is_set() or self._transport_stopped:
            raise RuntimeError("controller is stopped")

    def positioning_metrics(self) -> dict[str, float | int | str]:
        with self._lock:
            return dict(self._last_positioning_metrics)

    def start(self) -> None:
        with self._lock:
            if not self._stopped.is_set() and not self._transport_stopped:
                return
            try:
                self._transport.start()
            except Exception:
                try:
                    self._transport.stop()
                finally:
                    self._buttons = 0
                    self._transport_stopped = True
                raise
            self._buttons = 0
            self._transport_stopped = False
            self._stopped.clear()

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
            except Exception:
                # Recovery must continue when the failed channel can no longer
                # acknowledge a release.  The local button model is cleared and
                # the old engine is terminated before a new channel is created.
                pass
            self._buttons = 0
            try:
                self._transport.stop()
            finally:
                self._transport_stopped = True
            if self._stopped.is_set():
                return
            try:
                self._transport.start()
                if self._stopped.is_set():
                    self._transport.stop()
                    return
                advertise = getattr(self._transport, "advertise", None)
                if advertise is not None:
                    advertise()
            except BaseException:
                try:
                    self._transport.stop()
                finally:
                    self._transport_stopped = True
                raise
            self._transport_stopped = False

    def position_snapshot(self, max_age_ms: int = 150) -> PositionSnapshot:
        return self._positions.latest(max_age_ms)

    def emergency_stop(self) -> None:
        self._stopped.set()
        with self._lock:
            if self._transport_stopped:
                return
            try:
                self._transport.release_all()
            finally:
                self._buttons = 0
                self._transport.stop()
                self._transport_stopped = True

    def move(self, dx: int, dy: int) -> None:
        if not -32768 <= dx <= 32767 or not -32768 <= dy <= 32767:
            raise ValueError("movement outside int16 bounds")
        with self._lock:
            self._ensure_running_locked()
            self._transport.move(dx, dy)

    def set_buttons(self, mask: int) -> None:
        if not 0 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        with self._lock:
            self._ensure_running_locked()
            self._transport.buttons(mask)
            self._buttons = mask

    def press_buttons(self, mask: int) -> int:
        """Press one or more supported buttons while preserving held buttons."""
        if not 1 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        with self._lock:
            self._ensure_running_locked()
            next_mask = self._buttons | mask
            self._transport.buttons(next_mask)
            self._buttons = next_mask
            return self._buttons

    def release_buttons(self, mask: int) -> int:
        """Release selected buttons while preserving every other held button."""
        if not 1 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        with self._lock:
            self._ensure_running_locked()
            next_mask = self._buttons & ~mask
            self._transport.buttons(next_mask)
            self._buttons = next_mask
            return self._buttons

    def buttons_mask(self) -> int:
        with self._lock:
            return self._buttons

    def click(self, button_bit: int, hold_seconds: float = 0.04) -> None:
        if button_bit not in (1, 2, 4, 8, 16):
            raise ValueError("invalid button")
        with self._lock:
            self._ensure_running_locked()
            self._transport.buttons(self._buttons | button_bit)
            try:
                if self._stopped.wait(hold_seconds):
                    raise RuntimeError("controller stopped during click")
            finally:
                self._transport.buttons(self._buttons & ~button_bit)

    def scroll(self, delta: int) -> None:
        if not -127 <= delta <= 127:
            raise ValueError("wheel outside int8 bounds")
        with self._lock:
            self._ensure_running_locked()
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
        preflight_timeout: float = 2.0,
        feedback_timeout: float = 0.25,
        max_age_ms: int = 150,
        max_iterations: int = 64,
        max_total_movement: float | None = None,
        stagnation_limit: int = 3,
        oscillation_limit: int = 3,
        no_progress_limit: int = 8,
        pause_gate: threading.Event | None = None,
        pause_ack: threading.Event | None = None,
        cancel_event: threading.Event | None = None,
    ) -> PositionSnapshot:
        if (tolerance_px < 0 or timeout <= 0 or max_step <= 0 or
                not 0 < proportional_gain <= 1 or minimum_effective_step <= 0 or
                preflight_timeout <= 0 or feedback_timeout <= 0 or
                max_age_ms <= 0 or max_iterations <= 0 or
                stagnation_limit <= 0 or oscillation_limit <= 0 or
                no_progress_limit <= 0 or
                (max_total_movement is not None and
                 not 0 < max_total_movement <= 262_144)):
            raise ValueError("invalid positioning limits")
        started = time.perf_counter()
        deadline = time.monotonic() + timeout
        try:
            interrupt_events = ((self._stopped,) if cancel_event is None else
                                (self._stopped, cancel_event))
            snapshot = self._positions.wait_fresh(
                min(preflight_timeout, timeout), max_age_ms, interrupt_events,
            )
        except PositionError as exc:
            raise PositioningError(
                str(exc), code="POSITION_FEEDBACK_UNAVAILABLE", emitted=False,
            ) from exc
        initial_x, initial_y = snapshot.x, snapshot.y
        initial_distance = math.hypot(target_x - initial_x, target_y - initial_y)
        movement_limit = (
            float(max_total_movement) if max_total_movement is not None
            else min(262_144.0, max(64.0, initial_distance * 8.0 + max_step * 2.0))
        )
        corrections = 0
        total_movement = 0.0
        transport_seconds = 0.0
        feedback_seconds = 0.0
        previous_error: tuple[int, int] | None = None
        fine_mode = False
        emitted = False
        stagnation_count = 0
        oscillation_count = 0
        no_progress_count = 0
        best_distance = initial_distance
        position_history: list[tuple[int, int]] = [(snapshot.x, snapshot.y)]
        expected_session = snapshot.session_id
        expected_topology = snapshot.topology_generation

        def metrics(final_error: float, outcome: str,
                    failure_code: str | None = None) -> dict[str, float | int | str]:
            result: dict[str, float | int | str] = {
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "corrections": corrections,
                "transport_ms": round(transport_seconds * 1000.0, 3),
                "feedback_wait_ms": round(feedback_seconds * 1000.0, 3),
                "initial_distance_px": round(initial_distance, 3),
                "final_error_px": round(final_error, 3),
                "total_commanded_movement": round(total_movement, 3),
                "max_iterations": max_iterations,
                "max_total_movement": round(movement_limit, 3),
                "outcome": outcome,
            }
            if failure_code is not None:
                result["failure_code"] = failure_code
            with self._lock:
                self._last_positioning_metrics = result
            return result

        def fail(message: str, code: str, final_error: float) -> None:
            raise PositioningError(
                message,
                code=code,
                emitted=emitted,
                metrics=metrics(final_error, "failed", code),
            )

        while True:
            if self._stopped.is_set():
                fail("positioning stopped", "POSITION_INTERRUPTED", math.hypot(
                    target_x - snapshot.x, target_y - snapshot.y))
            if cancel_event is not None and cancel_event.is_set():
                fail("positioning cancelled", "POSITION_INTERRUPTED", math.hypot(
                    target_x - snapshot.x, target_y - snapshot.y))
            if pause_gate is not None and not pause_gate.is_set():
                paused_at = time.monotonic()
                if pause_ack is not None:
                    pause_ack.set()
                while not pause_gate.wait(0.05):
                    if self._stopped.is_set():
                        fail("positioning stopped", "POSITION_INTERRUPTED", math.hypot(
                            target_x - snapshot.x, target_y - snapshot.y))
                    if cancel_event is not None and cancel_event.is_set():
                        fail("positioning cancelled", "POSITION_INTERRUPTED", math.hypot(
                            target_x - snapshot.x, target_y - snapshot.y))
                deadline += time.monotonic() - paused_at
                if pause_ack is not None:
                    pause_ack.clear()
            error_x = target_x - snapshot.x
            error_y = target_y - snapshot.y
            distance = math.hypot(error_x, error_y)
            if distance <= tolerance_px:
                metrics(distance, "confirmed")
                return snapshot
            if time.monotonic() >= deadline:
                fail("positioning deadline exceeded", "POSITION_DEADLINE", distance)
            if corrections >= max_iterations:
                fail("positioning iteration limit exceeded", "POSITION_ITERATION_LIMIT", distance)
            if (adaptive_acceleration and previous_error is not None and
                    error_x * previous_error[0] + error_y * previous_error[1] <= 0):
                fine_mode = True
            if adaptive_acceleration and not fine_mode:
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
            command_movement = math.hypot(dx, dy)
            if total_movement + command_movement > movement_limit:
                fail(
                    "positioning cumulative movement limit exceeded",
                    "POSITION_MOVEMENT_LIMIT",
                    distance,
                )
            previous_error = (error_x, error_y)
            previous_position = (snapshot.x, snapshot.y)
            transport_started = time.perf_counter()
            emitted = True
            try:
                self.move(dx, dy)
            except Exception as exc:
                transport_seconds += time.perf_counter() - transport_started
                fail(
                    f"positioning HID delivery is uncertain: {exc}",
                    "POSITION_EMISSION_UNCERTAIN",
                    distance,
                )
            transport_seconds += time.perf_counter() - transport_started
            corrections += 1
            total_movement += command_movement
            wait = min(feedback_timeout, max(0.001, deadline - time.monotonic()))
            feedback_started = time.perf_counter()
            try:
                interrupt_events = ((self._stopped,) if cancel_event is None else
                                    (self._stopped, cancel_event))
                snapshot = self._positions.wait_newer(
                    snapshot.sequence,
                    wait,
                    max_age_ms,
                    interrupt_events,
                )
            except PositionError as exc:
                feedback_seconds += time.perf_counter() - feedback_started
                interrupted = (self._stopped.is_set() or
                               cancel_event is not None and cancel_event.is_set())
                fail(
                    str(exc),
                    "POSITION_INTERRUPTED" if interrupted else "POSITION_FEEDBACK_FAILURE",
                    distance,
                )
            feedback_seconds += time.perf_counter() - feedback_started
            if snapshot.session_id != expected_session:
                fail("interactive session changed", "POSITION_SESSION_CHANGED", distance)
            if snapshot.topology_generation != expected_topology:
                fail("display topology changed", "POSITION_TOPOLOGY_CHANGED", distance)

            current_position = (snapshot.x, snapshot.y)
            current_distance = math.hypot(target_x - snapshot.x, target_y - snapshot.y)
            improved = current_distance < best_distance
            if current_position == previous_position:
                stagnation_count += 1
            else:
                stagnation_count = 0
            if (len(position_history) >= 2 and
                    current_position == position_history[-2] and not improved):
                oscillation_count += 1
            elif improved:
                oscillation_count = 0
            if improved:
                best_distance = current_distance
                no_progress_count = 0
            else:
                no_progress_count += 1
            position_history.append(current_position)
            if stagnation_count >= stagnation_limit:
                fail("positioning stagnated", "POSITION_STAGNATION", current_distance)
            if oscillation_count >= oscillation_limit:
                fail("positioning oscillation detected", "POSITION_OSCILLATION", current_distance)
            if no_progress_count >= no_progress_limit:
                fail("positioning correction is ineffective", "POSITION_NO_PROGRESS", current_distance)

    def move_relative_confirmed(
        self,
        dx: int,
        dy: int,
        **limits: object,
    ) -> tuple[PositionSnapshot, PositionSnapshot]:
        """Move by screen pixels and confirm the feedback-derived target exactly."""
        if not -32768 <= dx <= 32767 or not -32768 <= dy <= 32767:
            raise ValueError("movement outside int16 bounds")
        max_age_ms = int(limits.get("max_age_ms", 150))
        try:
            preflight_timeout = float(limits.get("preflight_timeout", 2.0))
            cancel_event = limits.get("cancel_event")
            interrupt_events = ((self._stopped,) if cancel_event is None else
                                (self._stopped, cancel_event))
            initial = self._positions.wait_fresh(
                preflight_timeout, max_age_ms, interrupt_events,
            )
        except PositionError as exc:
            raise PositioningError(
                str(exc), code="POSITION_FEEDBACK_UNAVAILABLE", emitted=False,
            ) from exc
        final = self.move_to(initial.x + dx, initial.y + dy, **limits)
        return initial, final
