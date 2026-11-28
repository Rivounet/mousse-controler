"""Health supervision for the long-lived HOGP provider.

Subscriber absence is an external connectivity state, not an engine failure.
Recreating the dynamic Windows GATT provider on that signal invalidates the
very server lifetime that a bonded HID host needs in order to reconnect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import threading
import time
from typing import Any, Callable


@dataclass(frozen=True)
class HogpHealthSnapshot:
    state: str
    authorized_subscriber: bool | None
    restart_attempts: int
    last_error: str | None


class HogpHealthMonitor:
    """Observe HOGP health and recover only a failed engine channel."""

    def __init__(
        self,
        controller: Any,
        transport: Any,
        stopped: threading.Event,
        *,
        poll_seconds: float,
        fault_recovery_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        logger: Callable[[str], None] | None = None,
        on_provider_restart: Callable[[], None] | None = None,
    ) -> None:
        for name, value, maximum in (
            ("poll_seconds", poll_seconds, 300.0),
            ("fault_recovery_seconds", fault_recovery_seconds, 3600.0),
        ):
            if not math.isfinite(value) or not 0.1 <= value <= maximum:
                raise ValueError(
                    f"{name} must be finite and between 0.1 and {maximum} seconds"
                )
        self._controller = controller
        self._transport = transport
        self._stopped = stopped
        self._poll_seconds = poll_seconds
        self._fault_recovery_seconds = fault_recovery_seconds
        self._clock = clock
        self._logger = logger or (lambda message: None)
        self._on_provider_restart = on_provider_restart or (lambda: None)
        self._lock = threading.Lock()
        self._last_fault_recovery: float | None = None
        self._snapshot = HogpHealthSnapshot(
            state="starting",
            authorized_subscriber=None,
            restart_attempts=0,
            last_error=None,
        )

    @staticmethod
    def _subscriber_is_authorized(status: dict[str, Any]) -> bool:
        value = status.get("authorized_subscriber", status.get("subscribed", ""))
        return str(value).strip().lower() == "true"

    def _replace(self, **changes: Any) -> HogpHealthSnapshot:
        with self._lock:
            values = asdict(self._snapshot)
            values.update(changes)
            self._snapshot = HogpHealthSnapshot(**values)
            return self._snapshot

    def snapshot(self) -> dict[str, str | bool | int | None]:
        with self._lock:
            return asdict(self._snapshot)

    @staticmethod
    def _is_true(value: object) -> bool:
        return str(value).strip().lower() == "true"

    def _recover(self, state: str, detail: str) -> HogpHealthSnapshot:
        current = self._replace(
            state=state,
            authorized_subscriber=None,
            last_error=detail,
        )
        now = self._clock()
        if (self._last_fault_recovery is not None and
                now - self._last_fault_recovery < self._fault_recovery_seconds):
            return current
        self._last_fault_recovery = now
        self._logger(f"HOGP engine recovery pending: {detail}")
        try:
            self._controller.restart_transport()
            if self._controller.is_stopped() or self._stopped.is_set():
                return self._replace(state="stopped", last_error=None)
            self._on_provider_restart()
        except Exception as recovery_exc:
            recovery_detail = f"{type(recovery_exc).__name__}: {recovery_exc}"
            self._logger(f"HOGP engine recovery failed: {recovery_detail}")
            return self._replace(
                state="recovery_failed",
                last_error=recovery_detail,
            )
        return self._replace(
            state="engine_restarted",
            restart_attempts=current.restart_attempts + 1,
        )

    def poll_once(self) -> HogpHealthSnapshot:
        if self._controller.is_stopped() or self._stopped.is_set():
            return self._replace(state="stopped")
        try:
            status = self._transport.status()
            if not isinstance(status, dict) or "advertising" not in status:
                raise ValueError("HOGP engine status is missing advertising state")
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            return self._recover("engine_fault", detail)

        if not self._is_true(status["advertising"]):
            return self._recover(
                "provider_not_advertising",
                f"advertising={status['advertising']}",
            )

        authorized = self._subscriber_is_authorized(status)
        return self._replace(
            state="connected" if authorized else "awaiting_subscriber",
            authorized_subscriber=authorized,
            last_error=None,
        )

    def run(self) -> None:
        while not self._stopped.wait(self._poll_seconds):
            if self._controller.is_stopped():
                self._replace(state="stopped")
                return
            self.poll_once()
