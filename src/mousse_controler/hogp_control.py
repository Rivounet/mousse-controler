"""Authenticated control-plane state for the deployed target HOGP agent.

Mouse reports never cross this contract.  It only coordinates narrowly
allow-listed Windows Bluetooth/PnP recovery after verifying the enrolled
target identities and the current HOGP provider generation.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable
from uuid import UUID, uuid4


def _sha256(value: object, name: str) -> str:
    normalized = str(value or "").strip().upper()
    if (len(normalized) != 64 or
            any(character not in "0123456789ABCDEF" for character in normalized)):
        raise ValueError(f"{name} must contain exactly 64 hexadecimal characters")
    return normalized


def _canonical_uuid(value: object, name: str) -> str:
    selected = str(value)
    try:
        canonical = str(UUID(selected))
    except ValueError as exc:
        raise ValueError(f"{name} must be a canonical UUID") from exc
    if canonical != selected.lower():
        raise ValueError(f"{name} must be a canonical UUID")
    return canonical


@dataclass(frozen=True)
class HogpControlPolicy:
    target_key_id: str
    target_aep_sha256: str
    adapter_instance_sha256: str
    paired_pnp_instance_sha256: str
    hid_pnp_instance_sha256: str
    allow_adapter_restart: bool = False
    allow_endpoint_restart: bool = False
    command_ttl_seconds: int = 60
    command_cooldown_seconds: int = 300
    endpoint_recovery_grace_seconds: int = 30

    def __post_init__(self) -> None:
        if not self.target_key_id.strip() or len(self.target_key_id) > 128:
            raise ValueError("target_key_id is required and must be at most 128 characters")
        for name in (
            "target_aep_sha256",
            "adapter_instance_sha256",
            "paired_pnp_instance_sha256",
            "hid_pnp_instance_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in ("allow_adapter_restart", "allow_endpoint_restart"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")
        for name in (
            "command_ttl_seconds", "command_cooldown_seconds",
            "endpoint_recovery_grace_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if not 10 <= self.command_ttl_seconds <= 300:
            raise ValueError("command_ttl_seconds must be in [10, 300]")
        if not 30 <= self.command_cooldown_seconds <= 3600:
            raise ValueError("command_cooldown_seconds must be in [30, 3600]")
        if not 10 <= self.endpoint_recovery_grace_seconds <= 300:
            raise ValueError("endpoint_recovery_grace_seconds must be in [10, 300]")


class HogpControlCoordinator:
    """Serialize one recovery command for one enrolled target and provider."""

    _ACK_STATES = {
        "executed", "failed", "expired", "not_required", "outcome_unknown",
    }

    def __init__(
        self,
        policy: HogpControlPolicy,
        transport_status: Callable[[], dict[str, Any]],
        *,
        provider_generation: str | None = None,
        clock_ms: Callable[[], int] | None = None,
        monotonic_ms: Callable[[], int] | None = None,
    ) -> None:
        self._policy = policy
        self._transport_status = transport_status
        self._provider_generation = _canonical_uuid(
            uuid4() if provider_generation is None else provider_generation,
            "provider_generation",
        )
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self._monotonic_ms = monotonic_ms or (lambda: int(time.monotonic() * 1000))
        self._lock = threading.Lock()
        self._outstanding: dict[str, Any] | None = None
        self._attempted: set[tuple[str, str]] = set()
        self._last_command_monotonic_ms: int | None = None
        self._last_ack: dict[str, str] | None = None
        self._endpoint_missing_since_monotonic_ms: int | None = None

    @property
    def provider_generation(self) -> str:
        with self._lock:
            return self._provider_generation

    def rotate_provider_generation(self, generation: str | None = None) -> str:
        """Bind subsequent recovery commands to a newly created provider."""

        selected = _canonical_uuid(
            uuid4() if generation is None else generation,
            "provider_generation",
        )
        with self._lock:
            if selected == self._provider_generation:
                raise ValueError("provider_generation must change after provider restart")
            self._provider_generation = selected
            self._outstanding = None
            self._attempted.clear()
            self._endpoint_missing_since_monotonic_ms = None
            return selected

    @staticmethod
    def _boolean_status(
        status: dict[str, Any], names: tuple[str, ...], label: str,
    ) -> bool:
        for name in names:
            if name not in status:
                continue
            value = str(status[name]).strip().lower()
            if value == "true":
                return True
            if value == "false":
                return False
            raise ValueError(f"HOGP transport {label} must be boolean")
        raise ValueError(f"HOGP transport status is missing {label}")

    def _validate_report(self, key_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if key_id != self._policy.target_key_id:
            raise ValueError("HOGP control report used an unauthorized key")
        if payload.get("schema") != "mousse-hogp-control-v1":
            raise ValueError("unsupported HOGP control report schema")
        if _sha256(payload.get("target_aep_sha256"), "target_aep_sha256") != \
                self._policy.target_aep_sha256:
            raise ValueError("HOGP target AEP identity mismatch")
        if _sha256(payload.get("adapter_instance_sha256"), "adapter_instance_sha256") != \
                self._policy.adapter_instance_sha256:
            raise ValueError("Bluetooth adapter identity mismatch")
        if _sha256(payload.get("paired_pnp_instance_sha256"),
                   "paired_pnp_instance_sha256") != \
                self._policy.paired_pnp_instance_sha256:
            raise ValueError("paired Bluetooth PnP identity mismatch")
        if _sha256(payload.get("hid_pnp_instance_sha256"),
                   "hid_pnp_instance_sha256") != \
                self._policy.hid_pnp_instance_sha256:
            raise ValueError("Bluetooth HID PnP identity mismatch")
        for name in ("radio_present", "paired", "hid_present", "elevated"):
            if not isinstance(payload.get(name), bool):
                raise ValueError(f"{name} must be boolean")
        radio_state = payload.get("radio_state")
        if radio_state not in {"On", "Off", "Disabled", "Unknown", "Unavailable"}:
            raise ValueError("radio_state is invalid")
        if (payload["radio_present"] and radio_state == "Unavailable") or (
                not payload["radio_present"] and radio_state != "Unavailable"):
            raise ValueError("radio state and presence are inconsistent")
        problem_code = payload.get("adapter_problem_code")
        if (isinstance(problem_code, bool) or not isinstance(problem_code, int) or
                not 0 <= problem_code <= 255):
            raise ValueError("adapter_problem_code must be an integer in [0, 255]")
        generation = payload.get("provider_generation")
        if generation is not None and not isinstance(generation, str):
            raise ValueError("provider_generation must be null or a string")
        if generation is not None:
            _canonical_uuid(generation, "provider_generation")
        acknowledgment = payload.get("acknowledgment")
        if acknowledgment is not None:
            if not isinstance(acknowledgment, dict):
                raise ValueError("acknowledgment must be an object")
            if (not isinstance(acknowledgment.get("command_id"), str) or
                    acknowledgment.get("state") not in self._ACK_STATES):
                raise ValueError("acknowledgment is invalid")
            _canonical_uuid(acknowledgment["command_id"], "acknowledgment.command_id")
        return payload

    def _new_command(
        self, action: str, now_ms: int, now_monotonic_ms: int,
    ) -> dict[str, Any] | None:
        attempt_key = (self._provider_generation, action)
        if attempt_key in self._attempted:
            return None
        if (self._last_command_monotonic_ms is not None and
                now_monotonic_ms - self._last_command_monotonic_ms <
                self._policy.command_cooldown_seconds * 1000):
            return None
        command = {
            "command_id": str(uuid4()),
            "action": action,
            "provider_generation": self._provider_generation,
            "expires_at_unix_ms": now_ms + self._policy.command_ttl_seconds * 1000,
        }
        self._attempted.add(attempt_key)
        self._last_command_monotonic_ms = now_monotonic_ms
        self._outstanding = command
        return command

    def accept(self, key_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        report = self._validate_report(key_id, payload)
        now_ms = self._clock_ms()
        now_monotonic_ms = self._monotonic_ms()
        try:
            transport = self._transport_status()
            if not isinstance(transport, dict):
                raise ValueError("HOGP transport status must be an object")
            advertising = self._boolean_status(
                transport, ("advertising",), "advertising",
            )
            authorized = self._boolean_status(
                transport, ("authorized_subscriber", "subscribed"),
                "authorized subscriber",
            )
            transport_available = True
        except Exception:
            transport = {}
            advertising = False
            authorized = False
            transport_available = False
        with self._lock:
            acknowledgment = report.get("acknowledgment")
            if (acknowledgment is not None and self._outstanding is not None and
                    acknowledgment["command_id"] == self._outstanding["command_id"]):
                self._last_ack = {
                    "command_id": acknowledgment["command_id"],
                    "state": acknowledgment["state"],
                }
                self._outstanding = None

            if authorized:
                self._outstanding = None
            elif (self._outstanding is not None and
                  now_ms > int(self._outstanding["expires_at_unix_ms"])):
                self._last_ack = {
                    "command_id": str(self._outstanding["command_id"]),
                    "state": "expired",
                }
                self._outstanding = None

            endpoint_missing = (
                transport_available and not authorized and report["radio_present"] and
                report["radio_state"] == "On" and
                report["adapter_problem_code"] == 0 and report["paired"] and
                not report["hid_present"]
            )
            if endpoint_missing:
                if self._endpoint_missing_since_monotonic_ms is None:
                    self._endpoint_missing_since_monotonic_ms = now_monotonic_ms
            else:
                self._endpoint_missing_since_monotonic_ms = None
            endpoint_grace_elapsed = (
                self._endpoint_missing_since_monotonic_ms is not None and
                now_monotonic_ms - self._endpoint_missing_since_monotonic_ms >=
                self._policy.endpoint_recovery_grace_seconds * 1000
            )

            command = (
                self._outstanding
                if transport_available and advertising else None
            )
            if (command is None and not authorized and transport_available and
                    advertising and
                    report["elevated"]):
                if (self._policy.allow_adapter_restart and
                        (not report["radio_present"] or
                         report["adapter_problem_code"] != 0)):
                    command = self._new_command(
                        "restart_bluetooth_adapter", now_ms, now_monotonic_ms,
                    )
                elif (self._policy.allow_endpoint_restart and endpoint_missing and
                      (endpoint_grace_elapsed or
                       report.get("provider_generation") not in
                       (None, self._provider_generation))):
                    command = self._new_command(
                        "restart_paired_endpoint", now_ms, now_monotonic_ms,
                    )

            return {
                "schema": "mousse-hogp-control-v1",
                "provider_generation": self._provider_generation,
                "transport": {
                    "available": transport_available,
                    "authorized_subscriber": authorized,
                    "subscriber_count": str(transport.get("subscriber_count", "")),
                    "advertising": str(transport.get("advertising", "")),
                },
                "command": dict(command) if command is not None else None,
                "last_acknowledgment": dict(self._last_ack)
                if self._last_ack is not None else None,
            }


class HogpControlReceiver:
    """HTTP-independent authenticated adapter for target control reports."""

    def __init__(self, verifier: Any, coordinator: HogpControlCoordinator) -> None:
        self._verifier = verifier
        self._coordinator = coordinator

    def accept(self, headers: Any, body: bytes, path: str) -> dict[str, Any]:
        import json

        if len(body) > 4096:
            raise ValueError("HOGP control body too large")
        key_id = headers.get("X-Agent-Key", "")
        timestamp_ms = int(headers.get("X-Timestamp", "-1"))
        sequence = int(headers.get("X-Sequence", "-1"))
        self._verifier.verify(
            key_id,
            headers.get("X-Signature", ""),
            "POST",
            path,
            timestamp_ms,
            sequence,
            body,
        )
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("HOGP control body must be an object")
        response = self._coordinator.accept(key_id, payload)
        response["accepted_seq"] = sequence
        return response
