"""Open a bounded Windows Bluetooth pairing window and restore prior state."""

from __future__ import annotations

import argparse
import ctypes
import json
import time
from dataclasses import asdict, dataclass
from typing import Protocol


class BluetoothApi(Protocol):
    def is_connectable(self) -> bool: ...
    def is_discoverable(self) -> bool: ...
    def set_connectable(self, enabled: bool) -> None: ...
    def set_discoverable(self, enabled: bool) -> None: ...


class WindowsBluetoothApi:
    def __init__(self) -> None:
        dll = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
        self._is_connectable = dll.BluetoothIsConnectable
        self._is_discoverable = dll.BluetoothIsDiscoverable
        self._set_connectable = dll.BluetoothEnableIncomingConnections
        self._set_discoverable = dll.BluetoothEnableDiscovery
        for function in (self._is_connectable, self._is_discoverable):
            function.argtypes = [ctypes.c_void_p]
            function.restype = ctypes.c_bool
        for function in (self._set_connectable, self._set_discoverable):
            function.argtypes = [ctypes.c_void_p, ctypes.c_bool]
            function.restype = ctypes.c_bool

    def is_connectable(self) -> bool:
        return bool(self._is_connectable(None))

    def is_discoverable(self) -> bool:
        return bool(self._is_discoverable(None))

    @staticmethod
    def _raise_last_error(action: str) -> None:
        code = ctypes.get_last_error()
        raise OSError(code, f"{action} failed")

    def set_connectable(self, enabled: bool) -> None:
        if not self._set_connectable(None, enabled):
            self._raise_last_error("BluetoothEnableIncomingConnections")

    def set_discoverable(self, enabled: bool) -> None:
        if not self._set_discoverable(None, enabled):
            self._raise_last_error("BluetoothEnableDiscovery")


@dataclass(frozen=True)
class PairabilityState:
    connectable: bool
    discoverable: bool


def read_state(api: BluetoothApi) -> PairabilityState:
    return PairabilityState(api.is_connectable(), api.is_discoverable())


def restore_state(api: BluetoothApi, initial: PairabilityState) -> PairabilityState:
    current = read_state(api)
    if current.discoverable != initial.discoverable:
        api.set_discoverable(initial.discoverable)
    current = read_state(api)
    if current.connectable != initial.connectable:
        api.set_connectable(initial.connectable)
    return read_state(api)


def pairing_window(api: BluetoothApi, seconds: float) -> tuple[PairabilityState, PairabilityState]:
    initial = read_state(api)
    try:
        if not initial.connectable:
            api.set_connectable(True)
        if not initial.discoverable:
            api.set_discoverable(True)
        active = read_state(api)
        print(json.dumps({"event": "pairability-active", **asdict(active)}), flush=True)
        time.sleep(seconds)
    finally:
        final = restore_state(api, initial)
        print(json.dumps({"event": "pairability-restored", **asdict(final)}), flush=True)
    return initial, final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--confirm-pairing-window", action="store_true")
    args = parser.parse_args()
    if not args.confirm_pairing_window:
        parser.error("--confirm-pairing-window is required")
    if not 1 <= args.duration_seconds <= 900:
        parser.error("--duration-seconds must be between 1 and 900")
    pairing_window(WindowsBluetoothApi(), args.duration_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
