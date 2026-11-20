"""Deterministic, non-material doubles used only by the R0 characterization suite."""

from __future__ import annotations

import io
import queue
import threading
from typing import Any

from mousse_controler.transport import SimulatedHidTransport, TransportError


class BlockingLineStream:
    """A stdout double that stays silent until the test explicitly releases it."""

    def __init__(self, line: str = '{"ok":true,"event":"prepared"}\n') -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.line = line

    def readline(self) -> str:
        self.entered.set()
        self.release.wait(2)
        return self.line


class SaturatingStderr:
    """Models an engine writer blocked by a one-slot stderr pipe."""

    def __init__(self) -> None:
        self.buffer: queue.Queue[str] = queue.Queue(maxsize=1)
        self.blocked = threading.Event()
        self.finished = threading.Event()
        self.read_calls = 0
        self._thread = threading.Thread(target=self._write, daemon=True)
        self._thread.start()

    def _write(self) -> None:
        self.buffer.put("first diagnostic")
        self.blocked.set()
        self.buffer.put("second diagnostic")
        self.finished.set()

    def readline(self) -> str:
        self.read_calls += 1
        return self.buffer.get(timeout=1)

    def unblock(self) -> None:
        try:
            self.buffer.get_nowait()
        except queue.Empty:
            pass
        self._thread.join(1)


class ProcessDouble:
    """Minimum subprocess surface needed by NativeHogpTransport."""

    def __init__(self, stdout: Any, *, stderr: Any | None = None,
                 return_code: int | None = None) -> None:
        self.stdin = io.StringIO()
        self.stdout = stdout
        self.stderr = stderr if stderr is not None else io.StringIO()
        self.return_code = return_code

    def poll(self) -> int | None:
        return self.return_code


class FailingAfterEffectTransport(SimulatedHidTransport):
    """Applies one simulated effect, then makes delivery acknowledgement uncertain."""

    def __init__(self, operation: str) -> None:
        super().__init__()
        self.operation = operation
        self.failed = False

    def buttons(self, mask: int) -> None:
        super().buttons(mask)
        if self.operation == "buttons" and mask and not self.failed:
            self.failed = True
            raise TransportError("delivery became uncertain after simulated effect")

    def move(self, dx: int, dy: int) -> None:
        super().move(dx, dy)
        if self.operation == "move" and not self.failed:
            self.failed = True
            raise TransportError("delivery became uncertain after simulated effect")


class SequenceDouble:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1

    def request_stop(self) -> None:
        self.stop_calls += 1


class ActionsDouble:
    def __init__(self) -> None:
        self.request_stop_calls = 0

    def request_stop(self) -> None:
        self.request_stop_calls += 1


class ControllerStopDouble:
    def __init__(self) -> None:
        self.emergency_stop_calls = 0

    def emergency_stop(self) -> None:
        self.emergency_stop_calls += 1


class UpdateOrderModel:
    """Model of the target script's replace-then-start ordering, not an updater."""

    def __init__(self) -> None:
        self.installed = "old"
        self.rollback_artifact = "old"

    def install(self, *, fail_start: bool) -> None:
        self.installed = "new"
        if fail_start:
            raise RuntimeError("simulated task start failure")

    def rollback(self, *, fail_start: bool) -> None:
        self.installed = self.rollback_artifact
        if fail_start:
            raise RuntimeError("simulated rollback start failure")
