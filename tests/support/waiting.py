"""Deterministic bounded waits shared by asynchronous tests."""

from __future__ import annotations

import threading
import time
from typing import Callable, TypeVar


T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T],
    *,
    timeout: float = 1.0,
    interval: float = 0.005,
    description: str = "condition",
) -> T:
    """Return the first truthy predicate result or fail at a bounded deadline."""

    if timeout <= 0 or interval <= 0:
        raise ValueError("wait limits must be positive")
    deadline = time.monotonic() + timeout
    waiter = threading.Event()
    while True:
        result = predicate()
        if result:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"timed out waiting for {description}")
        waiter.wait(min(interval, remaining))
