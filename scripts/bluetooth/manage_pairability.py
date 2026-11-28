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


@dataclass(frozen=True)
class ConsentAssessment:
    policy: str
    supported: bool
    requires_human_consent: bool
    reason: str


def assess_consent_policy(
    policy: str,
    *,
    windows_iot_core: bool,
    inbound_handler_registered: bool,
) -> ConsentAssessment:
    if policy == "windows-interactive":
        return ConsentAssessment(
            policy=policy,
            supported=True,
            requires_human_consent=True,
            reason="WINDOWS_DESKTOP_SYSTEM_CONSENT_REQUIRED",
        )
    if policy != "unattended":
        raise ValueError("unsupported consent policy")
    if not windows_iot_core:
        return ConsentAssessment(
            policy=policy,
            supported=False,
            requires_human_consent=False,
            reason="UNATTENDED_INBOUND_PAIRING_REQUIRES_WINDOWS_IOT_CORE",
        )
    if not inbound_handler_registered:
        return ConsentAssessment(
            policy=policy,
            supported=False,
            requires_human_consent=False,
            reason="UNATTENDED_INBOUND_PAIRING_HANDLER_NOT_IMPLEMENTED",
        )
    return ConsentAssessment(
        policy=policy,
        supported=True,
        requires_human_consent=False,
        reason="SUPPORTED",
    )


def windows_is_iot_core() -> bool:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        ) as key:
            edition = str(winreg.QueryValueEx(key, "EditionID")[0])
            product = str(winreg.QueryValueEx(key, "ProductName")[0])
    except (ImportError, OSError):
        return False
    normalized = f"{edition} {product}".casefold()
    return "iotcore" in normalized or "iot core" in normalized or "iotuap" in normalized


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


def pairing_window(
    api: BluetoothApi,
    seconds: float,
    consent_policy: str = "windows-interactive",
) -> tuple[PairabilityState, PairabilityState]:
    initial = read_state(api)
    try:
        if not initial.connectable:
            api.set_connectable(True)
        if not initial.discoverable:
            api.set_discoverable(True)
        active = read_state(api)
        print(json.dumps({
            "event": "pairability-active",
            "consent_policy": consent_policy,
            **asdict(active),
        }), flush=True)
        time.sleep(seconds)
    finally:
        final = restore_state(api, initial)
        print(json.dumps({
            "event": "pairability-restored",
            "consent_policy": consent_policy,
            **asdict(final),
        }), flush=True)
    return initial, final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--confirm-pairing-window", action="store_true")
    parser.add_argument(
        "--consent-policy",
        choices=("windows-interactive", "unattended"),
        required=True,
    )
    args = parser.parse_args()
    if not args.confirm_pairing_window:
        parser.error("--confirm-pairing-window is required")
    if not 1 <= args.duration_seconds <= 900:
        parser.error("--duration-seconds must be between 1 and 900")
    assessment = assess_consent_policy(
        args.consent_policy,
        windows_iot_core=windows_is_iot_core(),
        inbound_handler_registered=False,
    )
    if not assessment.supported:
        print(json.dumps({
            "event": "pairability-refused",
            **asdict(assessment),
        }), flush=True)
        return 3
    pairing_window(
        WindowsBluetoothApi(),
        args.duration_seconds,
        consent_policy=args.consent_policy,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
