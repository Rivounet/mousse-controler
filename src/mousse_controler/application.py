"""Application services coordinating commands, actions, sequences and queries."""

from __future__ import annotations

from dataclasses import asdict
import threading
import time
from typing import Any, Callable

from .actions import ActionState
from .controller import MouseController
from .geometry import CircleZone, PolygonZone, RectangleZone
from .orchestration import OperationCoordinator
from .sequence import SequenceRunner, SequenceStep, WaitMode
from .trajectory import TrajectoryConfig, TrajectoryEngine


class ApplicationError(RuntimeError):
    pass


class MouseApplicationService:
    """Single application boundary used by protocol adapters."""

    def __init__(
        self,
        controller: MouseController,
        transport: Any,
        position_receiver: Any,
        action_executor: Any | None = None,
        capture_broker: Any | None = None,
        coordinator: OperationCoordinator | None = None,
    ) -> None:
        action_coordinator = getattr(action_executor, "coordinator", None)
        if coordinator is not None and action_coordinator is not None and coordinator is not action_coordinator:
            raise ValueError("action executor and application must share one coordinator")
        self._controller = controller
        self._transport = transport
        self._receiver = position_receiver
        self._actions = action_executor
        self._captures = capture_broker
        self._coordinator = coordinator or action_coordinator or OperationCoordinator()
        self._sequence: SequenceRunner | Any | None = None
        self._sequence_lock = threading.Lock()

    @property
    def coordinator(self) -> OperationCoordinator:
        return self._coordinator

    @property
    def availability(self) -> dict[str, bool]:
        return {"actions": self._actions is not None, "captures": self._captures is not None}

    @property
    def sequence(self) -> Any | None:
        with self._sequence_lock:
            return self._sequence

    @sequence.setter
    def sequence(self, value: Any | None) -> None:
        """Compatibility seam for characterized legacy stop tests."""
        with self._sequence_lock:
            self._sequence = value

    def advertise_start(self) -> None:
        self._transport.advertise()

    def transport_status(self) -> dict[str, Any]:
        status = getattr(self._transport, "status", None)
        if status is None:
            raise ApplicationError("transport status is unavailable")
        return status()

    def position_status(self) -> dict[str, Any]:
        snapshot = self._controller.position_snapshot(max_age_ms=5_000)
        return {
            "x": snapshot.x,
            "y": snapshot.y,
            "sequence": snapshot.sequence,
            "session_id": snapshot.session_id,
            "topology_generation": snapshot.topology_generation,
            "observed_at_unix_ms": snapshot.observed_at_unix_ms,
            "age_ms": round((time.monotonic() - snapshot.received_monotonic) * 1000, 3),
        }

    def position_metrics(self) -> dict[str, Any]:
        metrics = getattr(self._receiver, "metrics", None)
        if metrics is None:
            raise ApplicationError("position metrics are unavailable")
        return metrics()

    def move(self, action_id: str, dx: int, dy: int) -> dict[str, Any] | None:
        return self._legacy(action_id, "move", lambda: self._controller.move(dx, dy))

    def click(self, action_id: str, button_bit: int) -> dict[str, Any] | None:
        return self._legacy(action_id, "click", lambda: self._controller.click(button_bit))

    def buttons(self, action_id: str, mask: int) -> dict[str, Any] | None:
        return self._legacy(action_id, "buttons", lambda: self._controller.set_buttons(mask))

    def scroll(self, action_id: str, delta: int) -> dict[str, Any] | None:
        return self._legacy(action_id, "scroll", lambda: self._controller.scroll(delta))

    def stop(self) -> None:
        errors: list[str] = []
        if self._actions is not None:
            try:
                self._actions.request_stop()
            except Exception as exc:
                errors.append(f"actions: {exc}")
        sequence = self.sequence
        if sequence is not None:
            try:
                sequence.request_stop()
            except Exception as exc:
                errors.append(f"sequence: {exc}")
        try:
            self._controller.emergency_stop()
        except Exception as exc:
            errors.append(f"controller: {exc}")
        if errors:
            raise ApplicationError("global stop completed with errors: " + "; ".join(errors))

    def capabilities(self) -> dict[str, Any]:
        if self._actions is not None:
            return self._actions.capabilities()
        return {
            "buttons": {"left": 1, "right": 2, "middle": 4, "back": 8, "forward": 16},
            "vertical_wheel": True,
            "horizontal_wheel": False,
        }

    def submit_action(self, spec: dict[str, Any], action_id: str | None) -> dict[str, Any]:
        return self._require_actions().submit(spec, action_id=action_id)

    def action_status(self, action_id: str) -> dict[str, Any]:
        return self._require_actions().registry.get(action_id)

    def action_list(self, limit: int) -> list[dict[str, Any]]:
        return self._require_actions().registry.list(limit)

    def cancel_action(self, action_id: str) -> dict[str, Any]:
        return self._require_actions().cancel(action_id)

    def pause_action(self, action_id: str) -> dict[str, Any]:
        return self._require_actions().pause(action_id)

    def resume_action(self, action_id: str) -> dict[str, Any]:
        return self._require_actions().resume(action_id)

    def advance_action(self, action_id: str) -> dict[str, Any]:
        return self._require_actions().advance(action_id)

    def action_events(self, after_event_id: str | None, limit: int) -> list[dict[str, Any]]:
        return self._require_actions().registry.history(after_event_id, limit)

    def capture_status(self, action_id: str) -> list[dict[str, Any]]:
        return self._require_captures().list_for_action(action_id)

    def capture_delete(self, capture_id: str) -> dict[str, Any]:
        return self._require_captures().delete(capture_id)

    def start_sequence(self, arguments: dict[str, Any]) -> None:
        with self._sequence_lock:
            if self._sequence and self._sequence.status().state.value not in (
                "COMPLETED", "STOPPED", "ERROR",
            ):
                raise ApplicationError("a sequence is already active")
            steps = [SequenceStep(
                self._zone(item["zone"]),
                WaitMode(item.get("wait_mode", "automatic")),
                float(item.get("wait_seconds", 0)),
            ) for item in arguments["steps"]]
            config = TrajectoryConfig(**arguments.get("trajectory", {}))
            feedback = getattr(self._receiver, "feedback", None)
            topology = feedback().topology if feedback is not None else self._receiver.topology()
            candidate = SequenceRunner(
                self._controller,
                TrajectoryEngine(config),
                topology,
                steps,
                seed=arguments.get("seed"),
                coordinator=self._coordinator,
            )
            candidate.start()
            self._sequence = candidate

    def pause_sequence(self) -> None:
        self._require_sequence().pause()

    def resume_sequence(self) -> None:
        self._require_sequence().resume()

    def advance_sequence(self) -> None:
        self._require_sequence().next_target()

    def skip_sequence(self) -> None:
        self._require_sequence().skip_target()

    def stop_sequence(self) -> None:
        self._require_sequence().stop()

    def sequence_status(self) -> dict[str, Any]:
        status = self._require_sequence().status()
        return {
            "sequence_id": status.sequence_id,
            "state": status.state.value,
            "current_index": status.current_index,
            "target": status.target,
            "measured_position": status.measured_position,
            "wait_mode": status.wait_mode.value if status.wait_mode else None,
            "error": status.error,
            "started_at": status.started_at,
            "updated_at": status.updated_at,
            "results": [asdict(result) for result in status.results],
        }

    def _legacy(
        self,
        action_id: str,
        kind: str,
        callback: Callable[[], None],
    ) -> dict[str, Any] | None:
        with self._coordinator.acquire(f"legacy:{action_id}", wait=False):
            if self._actions is None:
                callback()
                return None
            registry = self._actions.registry
            registry.create(action_id, kind)
            registry.transition(action_id, ActionState.RUNNING)
            try:
                callback()
            except Exception as exc:
                registry.transition(
                    action_id,
                    ActionState.UNKNOWN,
                    error_code="LEGACY_ACTION_UNCERTAIN",
                    error=str(exc),
                )
                raise
            registry.transition(
                action_id,
                ActionState.EXECUTED,
                result={"legacy_command": True},
            )
            return registry.get(action_id)

    def _require_actions(self) -> Any:
        if self._actions is None:
            raise ApplicationError("action engine is unavailable")
        return self._actions

    def _require_captures(self) -> Any:
        if self._captures is None:
            raise ApplicationError("capture subsystem is unavailable")
        return self._captures

    def _require_sequence(self) -> Any:
        sequence = self.sequence
        if sequence is None:
            raise ApplicationError("no sequence")
        return sequence

    @staticmethod
    def _zone(data: dict[str, Any]) -> Any:
        kind = data.get("type")
        if kind == "rectangle":
            return RectangleZone(int(data["x"]), int(data["y"]), int(data["width"]), int(data["height"]))
        if kind == "circle":
            return CircleZone(int(data["center_x"]), int(data["center_y"]), int(data["radius"]))
        if kind == "polygon":
            return PolygonZone([(int(point[0]), int(point[1])) for point in data["vertices"]])
        raise ApplicationError("unknown zone type")
