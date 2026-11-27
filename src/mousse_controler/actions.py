"""Bounded, non-replaying mouse action execution and lifecycle tracking."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import copy
import json
import os
from pathlib import Path
import queue
import threading
import time
import uuid
from typing import Any, Callable

from .api_catalog import validate_action_contract
from .controller import MouseController, PositionError, PositioningError
from .orchestration import OperationCancelled, OperationCoordinator


class ActionState(str, Enum):
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    EXECUTED = "EXECUTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class ErrorPolicy(str, Enum):
    STOP = "stop"
    RETRY = "retry"
    CONTINUE = "continue"


TERMINAL_STATES = {
    ActionState.EXECUTED,
    ActionState.CONFIRMED,
    ActionState.FAILED,
    ActionState.UNKNOWN,
    ActionState.CANCELLED,
}

BUTTONS = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
    "back": 0x08,
    "forward": 0x10,
}

NON_IDEMPOTENT_KINDS = {
    "move_relative", "move_relative_confirmed", "click", "press", "release", "hold", "drag",
    "move_with_buttons", "scroll",
}
RETRY_SAFE_KINDS = {"move_relative_confirmed", "move_to", "wait", "wait_command"}
MOUSE_ACTION_KINDS = {
    "move_relative", "move_relative_confirmed", "move_to", "click", "press", "release", "hold", "drag",
    "move_with_buttons", "scroll",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class ActionRecord:
    action_id: str
    kind: str
    state: ActionState
    accepted_at_ms: int
    updated_at_ms: int
    parent_id: str | None = None
    started_at_ms: int | None = None
    finished_at_ms: int | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error: str | None = None
    event_sequence: int = 0

    def snapshot(self) -> dict[str, Any]:
        duration = None
        if self.started_at_ms is not None:
            duration = (self.finished_at_ms or self.updated_at_ms) - self.started_at_ms
        return {
            "action_id": self.action_id,
            "parent_id": self.parent_id,
            "kind": self.kind,
            "state": self.state.value,
            "accepted_at_ms": self.accepted_at_ms,
            "started_at_ms": self.started_at_ms,
            "updated_at_ms": self.updated_at_ms,
            "finished_at_ms": self.finished_at_ms,
            "duration_ms": duration,
            "result": copy.deepcopy(self.result),
            "error_code": self.error_code,
            "error": self.error,
            "event_sequence": self.event_sequence,
        }


class ActionRegistry:
    """Thread-safe bounded registry and fan-out event source."""

    def __init__(self, max_records: int = 2048, max_subscribers: int = 16,
                 event_history: int = 4096, subscriber_queue: int = 256,
                 journal_path: Path | None = None,
                 action_id_retention_seconds: int = 2_592_000):
        if min(max_records, max_subscribers, event_history, subscriber_queue) < 1:
            raise ValueError("registry limits must be positive")
        if action_id_retention_seconds < 1:
            raise ValueError("action id retention must be positive")
        self._max_records = max_records
        self._max_subscribers = max_subscribers
        self._subscriber_queue = subscriber_queue
        self._journal_path = Path(journal_path) if journal_path else None
        self._used_ids_path = (self._journal_path.with_suffix(
            self._journal_path.suffix + ".ids") if self._journal_path else None)
        self._action_id_retention_ms = int(action_id_retention_seconds) * 1000
        self._records: dict[str, ActionRecord] = {}
        self._order: deque[str] = deque()
        self._used_ids: dict[str, int] = {}
        self._history: deque[dict[str, Any]] = deque(maxlen=event_history)
        self._subscribers: set[queue.Queue[dict[str, Any]]] = set()
        self._lock = threading.Lock()
        self._load_used_ids()
        self._load_journal()

    @property
    def action_id_retention_seconds(self) -> int:
        return self._action_id_retention_ms // 1000

    def create(self, action_id: str, kind: str, parent_id: str | None = None) -> dict[str, Any]:
        if not action_id or len(action_id) > 128:
            raise ValueError("invalid action id")
        now = _now_ms()
        with self._lock:
            self._expire_used_ids_locked(now)
            if action_id in self._records or action_id in self._used_ids:
                raise ValueError("duplicate action id")
            while len(self._records) >= self._max_records:
                oldest = self._order[0]
                record = self._records[oldest]
                if record.state not in TERMINAL_STATES:
                    raise RuntimeError("action registry capacity exceeded")
                self._order.popleft()
                del self._records[oldest]
            self._reserve_action_id_locked(action_id, now)
            record = ActionRecord(action_id, kind, ActionState.ACCEPTED, now, now, parent_id)
            self._records[action_id] = record
            self._order.append(action_id)
            return self._emit_locked(record, "state")

    def transition(self, action_id: str, state: ActionState, *,
                   result: dict[str, Any] | None = None,
                   error_code: str | None = None, error: str | None = None) -> dict[str, Any]:
        now = _now_ms()
        with self._lock:
            record = self._records[action_id]
            if record.state in TERMINAL_STATES and record.state != ActionState.EXECUTED:
                raise RuntimeError("action is already terminal")
            if record.state == ActionState.EXECUTED and state != ActionState.CONFIRMED:
                raise RuntimeError("executed action can only become confirmed")
            record.state = state
            record.updated_at_ms = now
            if state == ActionState.RUNNING and record.started_at_ms is None:
                record.started_at_ms = now
            if result:
                record.result.update(copy.deepcopy(result))
            record.error_code = error_code
            record.error = error
            if state in TERMINAL_STATES:
                record.finished_at_ms = now
            return self._emit_locked(record, "state")

    def annotate(self, action_id: str, result: dict[str, Any], event_type: str = "result") -> dict[str, Any]:
        with self._lock:
            record = self._records[action_id]
            record.result.update(copy.deepcopy(result))
            record.updated_at_ms = _now_ms()
            return self._emit_locked(record, event_type)

    def get(self, action_id: str) -> dict[str, Any]:
        with self._lock:
            if action_id not in self._records:
                raise KeyError("unknown action id")
            return self._records[action_id].snapshot()

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("invalid action list limit")
        with self._lock:
            return [self._records[item].snapshot() for item in list(self._order)[-limit:]]

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        with self._lock:
            if len(self._subscribers) >= self._max_subscribers:
                raise RuntimeError("event subscriber capacity exceeded")
            target: queue.Queue[dict[str, Any]] = queue.Queue(self._subscriber_queue)
            self._subscribers.add(target)
            return target

    def unsubscribe(self, target: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(target)

    def history(self, after_event_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("invalid history limit")
        with self._lock:
            events = list(self._history)
        if after_event_id:
            for index, event in enumerate(events):
                if event["event_id"] == after_event_id:
                    events = events[index + 1:]
                    break
            else:
                events = []
        return copy.deepcopy(events[-limit:])

    def _emit_locked(self, record: ActionRecord, event_type: str) -> dict[str, Any]:
        record.event_sequence += 1
        self._append_journal_locked(record)
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "emitted_at_ms": _now_ms(),
            "action": record.snapshot(),
        }
        self._history.append(event)
        dead: list[queue.Queue[dict[str, Any]]] = []
        for subscriber in self._subscribers:
            try:
                subscriber.put_nowait(copy.deepcopy(event))
            except queue.Full:
                dead.append(subscriber)
        for subscriber in dead:
            self._subscribers.discard(subscriber)
        return copy.deepcopy(event)

    def _load_journal(self) -> None:
        path = self._journal_path
        if path is None or not path.exists():
            return
        latest: dict[str, dict[str, Any]] = {}
        used_ids_changed = False
        try:
            if path.stat().st_size > 32 * 1024 * 1024:
                raise RuntimeError("action journal exceeds safe size")
            with path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if len(line) > 65_536:
                        raise RuntimeError("action journal record exceeds safe size")
                    data = json.loads(line)
                    identifier = str(data["action_id"])
                    if identifier in latest:
                        del latest[identifier]
                    latest[identifier] = data
                    accepted_at = int(data["accepted_at_ms"])
                    if identifier not in self._used_ids:
                        self._used_ids[identifier] = accepted_at
                        used_ids_changed = True
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError("action journal is invalid") from exc
        for data in list(latest.values())[-self._max_records:]:
            try:
                state = ActionState(str(data["state"]))
                if state in (ActionState.ACCEPTED, ActionState.RUNNING):
                    state = ActionState.UNKNOWN
                    data["error_code"] = "PROCESS_RESTART"
                    data["error"] = "execution outcome is unknown after process restart"
                    data["finished_at_ms"] = _now_ms()
                record = ActionRecord(
                    action_id=str(data["action_id"]), kind=str(data["kind"]), state=state,
                    accepted_at_ms=int(data["accepted_at_ms"]),
                    updated_at_ms=int(data.get("updated_at_ms") or _now_ms()),
                    parent_id=data.get("parent_id"),
                    started_at_ms=data.get("started_at_ms"),
                    finished_at_ms=data.get("finished_at_ms"),
                    result=dict(data.get("result") or {}),
                    error_code=data.get("error_code"), error=data.get("error"),
                    event_sequence=int(data.get("event_sequence") or 0),
                )
            except (TypeError, ValueError, KeyError) as exc:
                raise RuntimeError("action journal is invalid") from exc
            self._records[record.action_id] = record
            self._order.append(record.action_id)
        for record in self._records.values():
            if record.error_code == "PROCESS_RESTART":
                record.updated_at_ms = _now_ms()
                record.event_sequence += 1
                self._append_journal_unlocked(record)
        self._expire_used_ids_locked(_now_ms())
        if used_ids_changed and self._used_ids_path is not None:
            self._compact_used_ids_locked()

    def _append_journal_locked(self, record: ActionRecord) -> None:
        if self._journal_path is None:
            return
        self._append_journal_unlocked(record)
        if self._journal_path.stat().st_size > 16 * 1024 * 1024:
            self._compact_journal_locked()

    def _append_journal_unlocked(self, record: ActionRecord) -> None:
        assert self._journal_path is not None
        self._journal_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(record.snapshot(), separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 65_535:
            raise RuntimeError("action journal record exceeds safe size")
        with self._journal_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _compact_journal_locked(self) -> None:
        assert self._journal_path is not None
        temporary = self._journal_path.with_suffix(self._journal_path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for identifier in self._order:
                stream.write(json.dumps(
                    self._records[identifier].snapshot(), separators=(",", ":"),
                    ensure_ascii=False,
                ) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self._journal_path)

    def _load_used_ids(self) -> None:
        path = self._used_ids_path
        if path is None or not path.exists():
            return
        try:
            if path.stat().st_size > 32 * 1024 * 1024:
                raise RuntimeError("action id ledger exceeds safe size")
            with path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if len(line) > 1024:
                        raise RuntimeError("action id ledger record exceeds safe size")
                    data = json.loads(line)
                    identifier = str(data["action_id"])
                    accepted_at = int(data["accepted_at_ms"])
                    if not identifier or len(identifier) > 128:
                        raise ValueError("invalid action id ledger entry")
                    self._used_ids[identifier] = accepted_at
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError("action id ledger is invalid") from exc
        self._expire_used_ids_locked(_now_ms())

    def _reserve_action_id_locked(self, action_id: str, accepted_at_ms: int) -> None:
        self._used_ids[action_id] = accepted_at_ms
        if self._used_ids_path is None:
            return
        encoded = json.dumps({
            "action_id": action_id, "accepted_at_ms": accepted_at_ms,
        }, separators=(",", ":"), ensure_ascii=False)
        try:
            self._used_ids_path.parent.mkdir(parents=True, exist_ok=True)
            with self._used_ids_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            if self._used_ids_path.stat().st_size > 16 * 1024 * 1024:
                self._compact_used_ids_locked()
        except Exception:
            # Fail closed: an identifier whose durable reservation may have
            # partially succeeded must remain blocked in this process.
            raise

    def _expire_used_ids_locked(self, now_ms: int) -> None:
        expired = [identifier for identifier, accepted_at in self._used_ids.items()
                   if identifier not in self._records and
                   now_ms >= accepted_at + self._action_id_retention_ms]
        if not expired:
            return
        for identifier in expired:
            del self._used_ids[identifier]
        if self._used_ids_path is not None:
            self._compact_used_ids_locked()

    def _compact_used_ids_locked(self) -> None:
        assert self._used_ids_path is not None
        self._used_ids_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._used_ids_path.with_suffix(self._used_ids_path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for identifier, accepted_at in self._used_ids.items():
                stream.write(json.dumps({
                    "action_id": identifier, "accepted_at_ms": accepted_at,
                }, separators=(",", ":"), ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self._used_ids_path)


class ActionCancelled(RuntimeError):
    pass


class ActionExecutionError(RuntimeError):
    def __init__(self, message: str, *, code: str = "ACTION_FAILED", emitted: bool = False,
                 button_state_uncertain: bool = False):
        super().__init__(message)
        self.code = code
        self.emitted = emitted
        self.button_state_uncertain = button_state_uncertain


@dataclass
class _Control:
    cancel: threading.Event = field(default_factory=threading.Event)
    run_gate: threading.Event = field(default_factory=threading.Event)
    advance: threading.Event = field(default_factory=threading.Event)
    button_state_uncertain: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self) -> None:
        self.run_gate.set()


class ActionExecutor:
    """Single-lane executor; accepted work is never replayed after restart."""

    def __init__(self, controller: MouseController, registry: ActionRegistry,
                 capture_broker: Any | None = None, max_queue: int = 256,
                 coordinator: OperationCoordinator | None = None):
        self._controller = controller
        self.registry = registry
        self._captures = capture_broker
        self._coordinator = coordinator or OperationCoordinator()
        self._queue: queue.Queue[tuple[str, dict[str, Any], _Control] | None] = queue.Queue(max_queue)
        self._controls: dict[str, _Control] = {}
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._stopped = threading.Event()
        self._worker = threading.Thread(target=self._run, name="mousse-actions", daemon=True)
        self._worker.start()

    @property
    def coordinator(self) -> OperationCoordinator:
        return self._coordinator

    def capabilities(self) -> dict[str, Any]:
        return {
            "buttons": dict(BUTTONS),
            "button_combinations": True,
            "vertical_wheel": True,
            "horizontal_wheel": False,
            "horizontal_wheel_reason": "current paired HID descriptor has no AC Pan field",
            "max_click_count": 20,
            "max_hold_seconds": 30.0,
            "max_scroll_reports": 500,
            "capture_moments": ["before", "after"],
            "action_id_retention_seconds": self.registry.action_id_retention_seconds,
        }

    def submit(self, spec: dict[str, Any], action_id: str | None = None,
               parent_id: str | None = None) -> dict[str, Any]:
        validated = self._validate_spec(spec)
        identifier = action_id or str(uuid.uuid4())
        control = _Control()
        with self._lock:
            if self._closed.is_set():
                raise RuntimeError("action executor is closed")
            if self._stopped.is_set():
                raise RuntimeError("action executor is safety-stopped")
            self.registry.create(identifier, validated["kind"], parent_id)
            self._controls[identifier] = control
            try:
                self._queue.put_nowait((identifier, validated, control))
            except queue.Full:
                self._controls.pop(identifier, None)
                self.registry.transition(identifier, ActionState.FAILED, error_code="QUEUE_FULL",
                                         error="action queue capacity exceeded")
                raise RuntimeError("action queue capacity exceeded")
        return self.registry.get(identifier)

    def cancel(self, action_id: str) -> dict[str, Any]:
        with self._lock:
            control = self._controls.get(action_id)
        if control is None:
            record = self.registry.get(action_id)
            if record["state"] in {item.value for item in TERMINAL_STATES}:
                return record
            raise KeyError("unknown action id")
        control.cancel.set()
        control.advance.set()
        control.run_gate.set()
        return self.registry.get(action_id)

    def pause(self, action_id: str) -> dict[str, Any]:
        with self._lock:
            control = self._controls.get(action_id)
        if control is None:
            raise KeyError("unknown or completed action id")
        control.run_gate.clear()
        return self.registry.annotate(action_id, {"paused": True}, "control")

    def resume(self, action_id: str) -> dict[str, Any]:
        with self._lock:
            control = self._controls.get(action_id)
        if control is None:
            raise KeyError("unknown or completed action id")
        control.run_gate.set()
        return self.registry.annotate(action_id, {"paused": False}, "control")

    def advance(self, action_id: str) -> dict[str, Any]:
        with self._lock:
            control = self._controls.get(action_id)
        if control is None:
            raise KeyError("unknown or completed action id")
        control.advance.set()
        return self.registry.annotate(action_id, {"advance_requested": True}, "control")

    def request_stop(self) -> None:
        """Publish the stop intent and wake every operation without taking a HID lock."""
        self._stopped.set()
        with self._lock:
            controls = list(self._controls.values())
        for control in controls:
            control.cancel.set()
            control.advance.set()
            control.run_gate.set()

    def emergency_stop(self) -> None:
        self.request_stop()
        self._controller.emergency_stop()

    def close(self, timeout: float = 2.0) -> None:
        if timeout < 0:
            raise ValueError("close timeout must be non-negative")
        with self._lock:
            if self._closed.is_set():
                return
            self._closed.set()
        deadline = time.monotonic() + timeout
        self.request_stop()
        self._cancel_queued()
        stop_error: Exception | None = None
        try:
            self._controller.emergency_stop()
        except Exception as exc:
            stop_error = exc
        self._queue.put_nowait(None)
        self._worker.join(max(0.0, deadline - time.monotonic()))
        if self._worker.is_alive():
            raise RuntimeError("action executor did not close within the deadline") from stop_error
        if stop_error is not None:
            raise RuntimeError("controller stop failed while closing action executor") from stop_error

    def _cancel_queued(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                if item is None:
                    continue
                action_id, _spec, control = item
                control.cancel.set()
                control.advance.set()
                control.run_gate.set()
                if self.registry.get(action_id)["state"] == ActionState.ACCEPTED.value:
                    self.registry.transition(
                        action_id, ActionState.CANCELLED,
                        error_code="EXECUTOR_CLOSED", error="cancelled before execution by close",
                    )
                with self._lock:
                    self._controls.pop(action_id, None)
            finally:
                self._queue.task_done()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            action_id, spec, control = item
            try:
                self._execute(action_id, spec, control)
            finally:
                with self._lock:
                    self._controls.pop(action_id, None)
                self._queue.task_done()

    def _execute(self, action_id: str, spec: dict[str, Any], control: _Control) -> None:
        if control.cancel.is_set():
            self.registry.transition(action_id, ActionState.CANCELLED,
                                     error_code="CANCELLED", error="cancelled before execution")
            return
        try:
            lease = self._coordinator.acquire(
                f"action:{action_id}", wait=True, cancel_event=control.cancel,
            )
        except OperationCancelled as exc:
            self.registry.transition(action_id, ActionState.CANCELLED,
                                     error_code="CANCELLED", error=str(exc))
            return
        with lease:
            self._execute_owned(action_id, spec, control)

    def _execute_owned(self, action_id: str, spec: dict[str, Any], control: _Control) -> None:
        self.registry.transition(action_id, ActionState.RUNNING)
        captures: dict[str, Any] = {}
        capture_config = (spec.get("capture") or {}) if spec["kind"] in MOUSE_ACTION_KINDS else {}
        if capture_config.get("before"):
            try:
                captures["before"] = self._capture(action_id, "before", capture_config)
                self.registry.annotate(action_id, {"captures": copy.deepcopy(captures)}, "capture")
            except Exception as exc:
                if ErrorPolicy(spec["error_policy"]) == ErrorPolicy.CONTINUE:
                    captures["before"] = {"state": "FAILED", "error": str(exc)}
                else:
                    self._fail(action_id, spec, exc, emitted=False, code="CAPTURE_BEFORE_FAILED")
                    return

        emitted = False
        try:
            result, confirmed, emitted = self._attempt(action_id, spec, control)
        except ActionCancelled as exc:
            self.registry.transition(action_id, ActionState.CANCELLED,
                                     result={"captures": captures}, error_code="CANCELLED", error=str(exc))
            return
        except Exception as exc:
            code = exc.code if isinstance(exc, ActionExecutionError) else "ACTION_FAILED"
            was_emitted = emitted or (isinstance(exc, ActionExecutionError) and exc.emitted)
            self._fail(action_id, spec, exc, emitted=was_emitted, code=code)
            return

        result["captures"] = captures
        self.registry.transition(action_id, ActionState.EXECUTED, result=result)
        if confirmed:
            self.registry.transition(action_id, ActionState.CONFIRMED,
                                     result={"confirmation_scope": "cursor_position"})
        if capture_config.get("after"):
            try:
                captures["after"] = self._capture(action_id, "after", capture_config)
            except Exception as exc:
                captures["after"] = {"state": "FAILED", "error": str(exc)}
            self.registry.annotate(action_id, {"captures": captures}, "capture")

    def _attempt(self, action_id: str, spec: dict[str, Any], control: _Control
                 ) -> tuple[dict[str, Any], bool, bool]:
        policy = ErrorPolicy(spec["error_policy"])
        max_attempts = int(spec.get("max_attempts", 1))
        if policy != ErrorPolicy.RETRY:
            max_attempts = 1
        emitted = False
        for attempt in range(1, max_attempts + 1):
            try:
                result, confirmed, attempt_emitted = self._perform(action_id, spec, control)
                emitted = emitted or attempt_emitted
                result["attempts"] = attempt
                return result, confirmed, emitted
            except ActionCancelled as exc:
                if control.button_state_uncertain.is_set():
                    raise ActionExecutionError(
                        str(exc), code="BUTTON_UNCERTAIN", emitted=True,
                        button_state_uncertain=True,
                    ) from exc
                raise
            except Exception as exc:
                exc_emitted = isinstance(exc, ActionExecutionError) and exc.emitted
                emitted = emitted or exc_emitted
                can_retry = (spec["kind"] in RETRY_SAFE_KINDS and not emitted and attempt < max_attempts)
                if not can_retry:
                    if isinstance(exc, ActionExecutionError):
                        raise
                    raise ActionExecutionError(str(exc), emitted=emitted) from exc
                self.registry.annotate(action_id, {
                    "retry": {"attempt": attempt, "reason": str(exc)}
                }, "retry")
        raise AssertionError("unreachable")

    def _perform(self, action_id: str, spec: dict[str, Any], control: _Control
                 ) -> tuple[dict[str, Any], bool, bool]:
        self._checkpoint(control)
        kind = spec["kind"]
        if kind == "move_relative":
            try:
                self._controller.move(int(spec["dx"]), int(spec["dy"]))
            except Exception as exc:
                raise ActionExecutionError(str(exc), code="MOVE_UNCERTAIN", emitted=True) from exc
            return {"reports": 1}, False, True
        if kind in {"move_relative_confirmed", "move_to"}:
            options = self._positioning_options(
                spec, control,
                tolerance_default=0 if kind == "move_relative_confirmed" else 2,
            )
            try:
                if kind == "move_relative_confirmed":
                    initial, position = self._controller.move_relative_confirmed(
                        int(spec["dx"]), int(spec["dy"]), **options,
                    )
                else:
                    initial = None
                    position = self._controller.move_to(
                        int(spec["x"]), int(spec["y"]), **options,
                    )
            except PositioningError as exc:
                raise ActionExecutionError(
                    str(exc), code=exc.code, emitted=exc.emitted,
                ) from exc
            result = {
                "position": {"x": position.x, "y": position.y, "sequence": position.sequence},
                "positioning": self._controller.positioning_metrics(),
            }
            if initial is not None:
                result["initial_position"] = {
                    "x": initial.x, "y": initial.y, "sequence": initial.sequence,
                }
                result["target_position"] = {
                    "x": initial.x + int(spec["dx"]),
                    "y": initial.y + int(spec["dy"]),
                }
            return {
                **result,
            }, True, bool(self._controller.positioning_metrics().get("corrections", 0))
        if kind == "click":
            button = self._button(spec)
            count = int(spec.get("count", 1))
            hold = float(spec.get("hold_seconds", 0.04))
            interval = float(spec.get("interval_seconds", 0.08))
            completed = 0
            for index in range(count):
                self._checkpoint(control)
                try:
                    self._controller.click(button, hold)
                except Exception as exc:
                    raise ActionExecutionError(
                        str(exc), code="CLICK_UNCERTAIN", emitted=True,
                        button_state_uncertain=True,
                    ) from exc
                completed += 1
                if index + 1 < count:
                    self._wait(interval, control)
            return {"clicks": completed, "button_mask": button, "reports": completed * 2}, False, True
        if kind in ("press", "release"):
            mask = self._button_mask(spec)
            try:
                buttons = (self._controller.press_buttons(mask) if kind == "press"
                           else self._controller.release_buttons(mask))
            except Exception as exc:
                raise ActionExecutionError(
                    str(exc), code="BUTTON_UNCERTAIN", emitted=True,
                    button_state_uncertain=True,
                ) from exc
            return {"buttons_mask": buttons, "reports": 1}, False, True
        if kind == "hold":
            mask = self._button_mask(spec)
            try:
                self._controller.press_buttons(mask)
            except Exception as exc:
                raise ActionExecutionError(
                    str(exc), code="BUTTON_UNCERTAIN", emitted=True,
                    button_state_uncertain=True,
                ) from exc
            try:
                self._wait(float(spec["duration_seconds"]), control)
            finally:
                try:
                    self._controller.release_buttons(mask)
                except RuntimeError as exc:
                    if not self._controller.is_stopped():
                        raise ActionExecutionError(
                            str(exc), code="BUTTON_UNCERTAIN", emitted=True,
                            button_state_uncertain=True,
                        ) from exc
                    control.button_state_uncertain.set()
            if control.button_state_uncertain.is_set():
                raise ActionExecutionError(
                    "button release was attempted during stop but is not physically confirmed",
                    code="BUTTON_UNCERTAIN", emitted=True, button_state_uncertain=True,
                )
            return {"held_mask": mask, "duration_seconds": float(spec["duration_seconds"]), "reports": 2}, False, True
        if kind in ("drag", "move_with_buttons"):
            mask = self._button_mask(spec)
            try:
                self._controller.press_buttons(mask)
            except Exception as exc:
                raise ActionExecutionError(
                    str(exc), code="DRAG_UNCERTAIN", emitted=True,
                    button_state_uncertain=True,
                ) from exc
            operation_error: Exception | None = None
            try:
                if kind == "drag" or "x" in spec:
                    position = self._controller.move_to(
                        int(spec["x"]), int(spec["y"]),
                        tolerance_px=int(spec.get("tolerance_px", 2)),
                        timeout=float(spec.get("timeout_seconds", 5.0)),
                        pause_gate=control.run_gate,
                        cancel_event=control.cancel,
                    )
                    result = {"position": {"x": position.x, "y": position.y,
                                            "sequence": position.sequence}, "button_mask": mask}
                    confirmed = True
                else:
                    self._controller.move(int(spec["dx"]), int(spec["dy"]))
                    result = {"button_mask": mask, "reports": 3}
                    confirmed = False
            except Exception as exc:
                operation_error = exc
            finally:
                try:
                    self._controller.release_buttons(mask)
                except RuntimeError as exc:
                    if not self._controller.is_stopped():
                        raise ActionExecutionError(
                            str(exc), code="DRAG_UNCERTAIN", emitted=True,
                            button_state_uncertain=True,
                        ) from exc
                    control.button_state_uncertain.set()
            if control.button_state_uncertain.is_set():
                raise ActionExecutionError(
                    "button release was attempted during stop but is not physically confirmed",
                    code="DRAG_UNCERTAIN", emitted=True, button_state_uncertain=True,
                )
            if operation_error is not None:
                raise ActionExecutionError(
                    str(operation_error), code="DRAG_UNCERTAIN", emitted=True,
                ) from operation_error
            return result, confirmed, True
        if kind == "scroll":
            if str(spec.get("axis", "vertical")) != "vertical":
                raise ActionExecutionError("horizontal wheel is unsupported by the paired HID descriptor",
                                           code="CAPABILITY_UNAVAILABLE", emitted=False)
            reports = self._scroll(spec, control)
            return {"reports": reports, "axis": "vertical"}, False, reports > 0
        if kind == "wait":
            duration = float(spec["duration_seconds"])
            self._wait(duration, control)
            return {"waited_seconds": duration}, False, False
        if kind == "wait_command":
            timeout = float(spec.get("timeout_seconds", 300.0))
            deadline = time.monotonic() + timeout
            while not control.advance.wait(0.05):
                self._checkpoint(control)
                if time.monotonic() >= deadline:
                    raise ActionExecutionError("wait command deadline exceeded", code="WAIT_TIMEOUT")
            control.advance.clear()
            return {"command_received": True}, False, False
        if kind == "sequence":
            children: list[str] = []
            any_emitted = False
            for index, child_spec in enumerate(spec["actions"]):
                self._checkpoint(control)
                child_id = str(child_spec.get("action_id") or uuid.uuid4())
                children.append(child_id)
                child = self._validate_spec(child_spec, inherited_policy=spec["error_policy"],
                                            inherited_capture=spec.get("capture"))
                self.registry.create(child_id, child["kind"], action_id)
                self.registry.transition(child_id, ActionState.RUNNING)
                child_captures: dict[str, Any] = {}
                try:
                    child_capture_config = ((child.get("capture") or {})
                                            if child["kind"] in MOUSE_ACTION_KINDS else {})
                    if child_capture_config.get("before"):
                        try:
                            child_captures["before"] = self._capture(
                                child_id, "before", child_capture_config)
                            self.registry.annotate(
                                child_id, {"captures": copy.deepcopy(child_captures)}, "capture")
                        except Exception as capture_error:
                            if ErrorPolicy(child["error_policy"]) != ErrorPolicy.CONTINUE:
                                raise ActionExecutionError(
                                    str(capture_error), code="CAPTURE_BEFORE_FAILED", emitted=False
                                ) from capture_error
                            child_captures["before"] = {
                                "state": "FAILED", "error": str(capture_error)
                            }
                    child_result, child_confirmed, child_emitted = self._attempt(child_id, child, control)
                    any_emitted = any_emitted or child_emitted
                    child_result["captures"] = child_captures
                    self.registry.transition(child_id, ActionState.EXECUTED, result=child_result)
                    if child_confirmed:
                        self.registry.transition(child_id, ActionState.CONFIRMED,
                                                 result={"confirmation_scope": "cursor_position"})
                    if child_capture_config.get("after"):
                        try:
                            child_captures["after"] = self._capture(
                                child_id, "after", child_capture_config)
                        except Exception as capture_error:
                            child_captures["after"] = {
                                "state": "FAILED", "error": str(capture_error)
                            }
                        self.registry.annotate(
                            child_id, {"captures": child_captures}, "capture")
                except ActionCancelled as exc:
                    self.registry.transition(child_id, ActionState.CANCELLED,
                                             error_code="CANCELLED", error=str(exc))
                    raise
                except Exception as exc:
                    emitted = isinstance(exc, ActionExecutionError) and exc.emitted
                    state = ActionState.UNKNOWN if emitted else ActionState.FAILED
                    code = exc.code if isinstance(exc, ActionExecutionError) else "ACTION_FAILED"
                    self.registry.transition(child_id, state, error_code=code, error=str(exc))
                    button_state_uncertain = (
                        isinstance(exc, ActionExecutionError) and exc.button_state_uncertain
                    )
                    if button_state_uncertain:
                        self._enter_safety_stop(child_id, exc)
                        raise ActionExecutionError(
                            f"sequence child {index} left button state uncertain: {exc}",
                            code="SEQUENCE_BUTTON_UNCERTAIN", emitted=True,
                            button_state_uncertain=True,
                        ) from exc
                    if ErrorPolicy(child["error_policy"]) == ErrorPolicy.CONTINUE:
                        continue
                    if ErrorPolicy(child["error_policy"]) == ErrorPolicy.STOP:
                        self._enter_safety_stop(child_id, exc)
                    raise ActionExecutionError(
                        f"sequence child {index} failed: {exc}", code="SEQUENCE_CHILD_FAILED",
                        emitted=any_emitted or emitted,
                    ) from exc
            return {"children": children}, False, any_emitted
        raise ActionExecutionError("unsupported action kind", code="INVALID_ACTION")

    @staticmethod
    def _positioning_options(
        spec: dict[str, Any], control: _Control, *, tolerance_default: int,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "tolerance_px": int(spec.get("tolerance_px", tolerance_default)),
            "timeout": float(spec.get("timeout_seconds", 5.0)),
            "max_step": int(spec.get("max_step", 48)),
            "preflight_timeout": float(spec.get("preflight_timeout_seconds", 2.0)),
            "feedback_timeout": float(spec.get("feedback_timeout_seconds", 0.25)),
            "max_age_ms": int(spec.get("max_age_ms", 150)),
            "max_iterations": int(spec.get("max_iterations", 64)),
            "stagnation_limit": int(spec.get("stagnation_limit", 3)),
            "oscillation_limit": int(spec.get("oscillation_limit", 3)),
            "no_progress_limit": int(spec.get("no_progress_limit", 8)),
            "pause_gate": control.run_gate,
            "cancel_event": control.cancel,
        }
        if "max_total_movement" in spec:
            options["max_total_movement"] = float(spec["max_total_movement"])
        return options

    def _scroll(self, spec: dict[str, Any], control: _Control) -> int:
        reports = 0
        if "duration_seconds" in spec:
            duration = float(spec["duration_seconds"])
            interval = float(spec.get("interval_seconds", 0.05))
            step = int(spec.get("step", 1))
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                self._checkpoint(control)
                try:
                    self._controller.scroll(step)
                except Exception as exc:
                    raise ActionExecutionError(str(exc), code="SCROLL_UNCERTAIN", emitted=True) from exc
                reports += 1
                if reports >= 500:
                    break
                self._wait(min(interval, max(0.0, deadline - time.monotonic())), control)
            return reports
        remaining = int(spec["delta"])
        while remaining:
            self._checkpoint(control)
            chunk = max(-127, min(127, remaining))
            try:
                self._controller.scroll(chunk)
            except Exception as exc:
                raise ActionExecutionError(str(exc), code="SCROLL_UNCERTAIN", emitted=True) from exc
            remaining -= chunk
            reports += 1
            if reports > 500:
                raise ActionExecutionError("scroll report limit exceeded", code="ACTION_LIMIT", emitted=True)
        return reports

    def _capture(self, action_id: str, moment: str, config: dict[str, Any]) -> dict[str, Any]:
        if self._captures is None:
            raise RuntimeError("capture subsystem is unavailable")
        return self._captures.request_capture(
            action_id, moment,
            retention_seconds=int(config.get("retention_seconds", 86_400)),
            timeout=float(config.get("timeout_seconds", 8.0)),
        )

    def _fail(self, action_id: str, spec: dict[str, Any], exc: Exception,
              *, emitted: bool, code: str) -> None:
        button_state_uncertain = (
            isinstance(exc, ActionExecutionError) and exc.button_state_uncertain
        )
        state = ActionState.UNKNOWN if (
            button_state_uncertain or emitted and spec["kind"] in NON_IDEMPOTENT_KINDS
        ) else ActionState.FAILED
        # Complete safety evidence before publishing the terminal state. Readers
        # are allowed to return as soon as a state is terminal, so annotating
        # afterwards exposes a transient, incomplete terminal record.
        if button_state_uncertain:
            self._enter_safety_stop(action_id, exc)
        elif ErrorPolicy(spec["error_policy"]) == ErrorPolicy.STOP:
            self._enter_safety_stop(action_id, exc)
        self.registry.transition(action_id, state, error_code=code, error=str(exc))

    def _enter_safety_stop(self, action_id: str, exc: Exception) -> None:
        """Quarantine the executor; release is attempted but never treated as confirmation."""
        self.request_stop()
        try:
            self._controller.emergency_stop()
        except Exception as stop_error:
            self.registry.annotate(action_id, {
                "safety_stop": {
                    "release_confirmed": False,
                    "error": str(stop_error),
                    "trigger": str(exc),
                }
            }, "safety")
        else:
            self.registry.annotate(action_id, {
                "safety_stop": {
                    "release_attempted": True,
                    "release_confirmed": False,
                }
            }, "safety")

    @staticmethod
    def _checkpoint(control: _Control) -> None:
        if control.cancel.is_set():
            raise ActionCancelled("action cancelled")
        while not control.run_gate.wait(0.05):
            if control.cancel.is_set():
                raise ActionCancelled("action cancelled while paused")

    def _wait(self, duration: float, control: _Control) -> None:
        if duration < 0:
            raise ValueError("duration must be non-negative")
        deadline = time.monotonic() + duration
        while True:
            self._checkpoint(control)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            control.cancel.wait(min(0.05, remaining))

    @staticmethod
    def _button(spec: dict[str, Any]) -> int:
        value = spec.get("button", "left")
        if isinstance(value, str):
            if value not in BUTTONS:
                raise ValueError("unknown mouse button")
            return BUTTONS[value]
        value = int(value)
        if value not in BUTTONS.values():
            raise ValueError("invalid mouse button")
        return value

    @classmethod
    def _button_mask(cls, spec: dict[str, Any]) -> int:
        if "mask" in spec:
            mask = int(spec["mask"])
        elif "buttons" in spec:
            values = spec["buttons"]
            if not isinstance(values, list) or not values:
                raise ValueError("buttons must be a non-empty list")
            mask = 0
            for value in values:
                mask |= cls._button({"button": value})
        else:
            mask = cls._button(spec)
        if not 1 <= mask <= 0x1F:
            raise ValueError("button mask outside five-button range")
        return mask

    @classmethod
    def _validate_spec(cls, spec: dict[str, Any], inherited_policy: str | None = None,
                       inherited_capture: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(spec, dict):
            raise ValueError("action must be an object")
        value = copy.deepcopy(spec)
        kind = str(value.get("kind", ""))
        validate_action_contract(value)
        value["kind"] = kind
        policy = str(value.get("error_policy", inherited_policy or ErrorPolicy.STOP.value))
        ErrorPolicy(policy)
        value["error_policy"] = policy
        attempts = int(value.get("max_attempts", 2 if policy == "retry" else 1))
        if not 1 <= attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        value["max_attempts"] = attempts
        if inherited_capture and "capture" not in value and kind in MOUSE_ACTION_KINDS:
            value["capture"] = copy.deepcopy(inherited_capture)
        capture = value.get("capture")
        if capture is not None:
            if kind not in MOUSE_ACTION_KINDS and kind != "sequence":
                raise ValueError("captures are allowed only before or after mouse actions")
            if not isinstance(capture, dict):
                raise ValueError("capture policy must be an object")
            retention = int(capture.get("retention_seconds", 86_400))
            if not 0 <= retention <= 2_592_000:
                raise ValueError("capture retention is outside allowed bounds")
        if kind == "click":
            cls._button(value)
            if not 1 <= int(value.get("count", 1)) <= 20:
                raise ValueError("click count must be between 1 and 20")
            if not 0 <= float(value.get("hold_seconds", 0.04)) <= 30:
                raise ValueError("click hold is outside allowed bounds")
            if not 0 <= float(value.get("interval_seconds", 0.08)) <= 5:
                raise ValueError("click interval is outside allowed bounds")
        elif kind in {"press", "release", "hold", "drag", "move_with_buttons"}:
            cls._button_mask(value)
        if kind == "hold" and not 0 <= float(value.get("duration_seconds", -1)) <= 30:
            raise ValueError("hold duration is outside allowed bounds")
        if kind in {"wait"} and not 0 <= float(value.get("duration_seconds", -1)) <= 300:
            raise ValueError("wait duration is outside allowed bounds")
        if kind == "wait_command" and not 0.1 <= float(value.get("timeout_seconds", 300)) <= 3600:
            raise ValueError("command wait timeout is outside allowed bounds")
        if kind == "scroll":
            if "duration_seconds" in value:
                if not 0 < float(value["duration_seconds"]) <= 30:
                    raise ValueError("continuous scroll duration is outside allowed bounds")
                if not 0.01 <= float(value.get("interval_seconds", 0.05)) <= 5:
                    raise ValueError("scroll interval is outside allowed bounds")
                if not -127 <= int(value.get("step", 1)) <= 127 or int(value.get("step", 1)) == 0:
                    raise ValueError("scroll step is outside int8 bounds")
            elif not -63_500 <= int(value.get("delta", 0)) <= 63_500:
                raise ValueError("scroll delta is outside bounded range")
        if kind == "sequence":
            actions = value.get("actions")
            if not isinstance(actions, list) or not 1 <= len(actions) <= 256:
                raise ValueError("sequence must contain 1..256 actions")
        return value
