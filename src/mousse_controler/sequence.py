"""Interruptible A→B→C orchestration over real position confirmations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random
import threading
import time
import uuid

from .controller import MouseController, PositionError, PositionSnapshot
from .geometry import DesktopTopology, Point, Zone
from .trajectory import TrajectoryEngine


class SequenceState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class WaitMode(str, Enum):
    AUTOMATIC = "automatic"
    COMMANDED = "commanded"


@dataclass(frozen=True)
class SequenceStep:
    zone: Zone
    wait_mode: WaitMode = WaitMode.AUTOMATIC
    wait_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.wait_seconds < 0:
            raise ValueError("wait duration must be non-negative")


@dataclass
class StepResult:
    index: int
    target: Point
    state: str
    started_at: float
    finished_at: float | None = None
    measured_position: Point | None = None
    error: str | None = None
    metrics: dict[str, float | int] = field(default_factory=dict)


@dataclass
class SequenceStatus:
    sequence_id: str
    state: SequenceState = SequenceState.IDLE
    current_index: int | None = None
    target: Point | None = None
    measured_position: Point | None = None
    wait_mode: WaitMode | None = None
    error: str | None = None
    started_at: float | None = None
    updated_at: float = field(default_factory=time.time)
    results: list[StepResult] = field(default_factory=list)


class SequenceRunner:
    def __init__(
        self,
        controller: MouseController,
        trajectory: TrajectoryEngine,
        topology: DesktopTopology,
        steps: list[SequenceStep],
        *,
        seed: int | None = None,
    ):
        if not steps:
            raise ValueError("sequence needs at least one zone")
        for step in steps:
            step.zone.validate(topology)
        self._controller = controller
        self._trajectory = trajectory
        self._topology = topology
        self._steps = list(steps)
        self._rng = random.Random(seed)
        self._status = SequenceStatus(sequence_id=str(uuid.uuid4()))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._skip = threading.Event()
        self._advance = threading.Event()
        self._run_gate = threading.Event()
        self._run_gate.set()
        self._paused_ack = threading.Event()
        self._paused_from: SequenceState | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("sequence runner cannot be replayed")
            self._stop.clear()
            self._skip.clear()
            self._advance.clear()
            self._run_gate.set()
            self._status.state = SequenceState.MOVING
            self._status.started_at = time.time()
            self._status.updated_at = time.time()
            self._thread = threading.Thread(target=self._run, name="mousse-sequence", daemon=True)
            self._thread.start()

    def pause(self) -> None:
        with self._lock:
            if self._status.state not in (SequenceState.MOVING, SequenceState.WAITING):
                raise RuntimeError("sequence is not pausable")
            self._paused_from = self._status.state
            self._run_gate.clear()
            self._status.state = SequenceState.PAUSED
            self._status.updated_at = time.time()
        self._paused_ack.wait(1.0)

    def resume(self) -> None:
        with self._lock:
            if self._status.state != SequenceState.PAUSED:
                raise RuntimeError("sequence is not paused")
            self._status.state = self._paused_from or SequenceState.MOVING
            self._paused_from = None
            self._status.updated_at = time.time()
            self._paused_ack.clear()
            self._run_gate.set()

    def next_target(self) -> None:
        with self._lock:
            if self._status.state != SequenceState.WAITING or self._status.wait_mode != WaitMode.COMMANDED:
                raise RuntimeError("sequence is not awaiting a command")
        self._advance.set()

    def skip_target(self) -> None:
        self._skip.set()
        self._advance.set()

    def stop(self) -> None:
        self._stop.set()
        self._skip.set()
        self._advance.set()
        self._run_gate.set()
        self._controller.emergency_stop()
        with self._lock:
            self._status.state = SequenceState.STOPPED
            self._status.updated_at = time.time()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread:
            thread.join(timeout)

    def status(self) -> SequenceStatus:
        with self._lock:
            return SequenceStatus(
                sequence_id=self._status.sequence_id,
                state=self._status.state,
                current_index=self._status.current_index,
                target=self._status.target,
                measured_position=self._status.measured_position,
                wait_mode=self._status.wait_mode,
                error=self._status.error,
                started_at=self._status.started_at,
                updated_at=self._status.updated_at,
                results=list(self._status.results),
            )

    def _set_state(self, state: SequenceState, **changes: object) -> None:
        with self._lock:
            self._status.state = state
            self._status.updated_at = time.time()
            for name, value in changes.items():
                setattr(self._status, name, value)

    def _wait_gate(self) -> None:
        while not self._run_gate.wait(0.05):
            self._paused_ack.set()
            if self._stop.is_set():
                raise PositionError("sequence stopped")
        self._paused_ack.clear()

    def _wait_automatic(self, duration: float) -> None:
        remaining = duration
        while remaining > 0:
            self._wait_gate()
            if self._stop.is_set():
                raise PositionError("sequence stopped")
            started = time.monotonic()
            if self._stop.wait(min(0.05, remaining)):
                raise PositionError("sequence stopped")
            remaining -= time.monotonic() - started

    def _run(self) -> None:
        try:
            for index, step in enumerate(self._steps):
                if self._stop.is_set():
                    return
                self._skip.clear()
                self._advance.clear()
                target = step.zone.random_point(self._rng)
                result = StepResult(index=index, target=target, state="MOVING", started_at=time.time())
                with self._lock:
                    self._status.current_index = index
                    self._status.target = target
                    self._status.wait_mode = step.wait_mode
                    self._status.results.append(result)
                current = self._controller.position_snapshot()
                generation_started = time.perf_counter()
                points = self._trajectory.generate((current.x, current.y), target, self._topology, self._rng)
                result.metrics = {
                    "trajectory_generation_ms": round((time.perf_counter() - generation_started) * 1000.0, 3),
                    "trajectory_point_count": len(points),
                    "positioning_calls": 0,
                    "corrections": 0,
                    "transport_ms": 0.0,
                    "feedback_wait_ms": 0.0,
                    "positioning_ms": 0.0,
                }
                measured: PositionSnapshot = current
                for point in points:
                    self._wait_gate()
                    if self._stop.is_set():
                        return
                    if self._skip.is_set():
                        result.state = "SKIPPED"
                        result.finished_at = time.time()
                        break
                    self._set_state(SequenceState.MOVING)
                    try:
                        measured = self._controller.move_to(
                            point[0], point[1], timeout=2.0,
                            pause_gate=self._run_gate, pause_ack=self._paused_ack,
                            cancel_event=self._skip,
                        )
                        call_metrics = self._controller.positioning_metrics()
                        result.metrics["positioning_calls"] += 1
                        result.metrics["corrections"] += int(call_metrics.get("corrections", 0))
                        result.metrics["transport_ms"] += float(call_metrics.get("transport_ms", 0.0))
                        result.metrics["feedback_wait_ms"] += float(call_metrics.get("feedback_wait_ms", 0.0))
                        result.metrics["positioning_ms"] += float(call_metrics.get("elapsed_ms", 0.0))
                    except PositionError:
                        if not self._skip.is_set():
                            raise
                        result.state = "SKIPPED"
                        result.finished_at = time.time()
                        break
                    self._set_state(SequenceState.MOVING, measured_position=(measured.x, measured.y))
                else:
                    if not step.zone.contains((measured.x, measured.y)):
                        measured = self._controller.move_to(
                            target[0], target[1], tolerance_px=0, timeout=2.0,
                            pause_gate=self._run_gate, pause_ack=self._paused_ack,
                            cancel_event=self._skip,
                        )
                        call_metrics = self._controller.positioning_metrics()
                        result.metrics["positioning_calls"] += 1
                        result.metrics["corrections"] += int(call_metrics.get("corrections", 0))
                        result.metrics["transport_ms"] += float(call_metrics.get("transport_ms", 0.0))
                        result.metrics["feedback_wait_ms"] += float(call_metrics.get("feedback_wait_ms", 0.0))
                        result.metrics["positioning_ms"] += float(call_metrics.get("elapsed_ms", 0.0))
                    if not step.zone.contains((measured.x, measured.y)):
                        raise PositionError("measured arrival is outside target zone")
                    result.state = "ARRIVED"
                    result.finished_at = time.time()
                    result.measured_position = (measured.x, measured.y)
                    self._set_state(SequenceState.ARRIVED, measured_position=result.measured_position)
                    if index < len(self._steps) - 1:
                        self._set_state(SequenceState.WAITING)
                        if step.wait_mode == WaitMode.AUTOMATIC:
                            self._wait_automatic(step.wait_seconds)
                        else:
                            while not self._advance.wait(0.05):
                                self._wait_gate()
                                if self._stop.is_set():
                                    return
                if self._stop.is_set():
                    return
            self._set_state(SequenceState.COMPLETED)
        except Exception as exc:
            if self._stop.is_set():
                return
            with self._lock:
                if self._status.results:
                    self._status.results[-1].state = "ERROR"
                    self._status.results[-1].error = str(exc)
                    self._status.results[-1].finished_at = time.time()
            self._set_state(SequenceState.ERROR, error=str(exc))
            try:
                self._controller.emergency_stop()
            except Exception:
                pass
