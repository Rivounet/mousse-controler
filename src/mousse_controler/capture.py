"""Authenticated, bounded one-shot screen capture broker and retention store."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import base64
import binascii
import json
from pathlib import Path
import threading
import time
import uuid
from typing import Any


@dataclass
class CaptureRecord:
    capture_id: str
    action_id: str
    moment: str
    requested_at_ms: int
    expires_at_ms: int
    retention_seconds: int
    max_bytes: int
    state: str = "PENDING"
    delivered_at_ms: int | None = None
    captured_at_ms: int | None = None
    cursor: dict[str, int] | None = None
    monitor: dict[str, Any] | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    storage_path: str | None = None
    delete_at_ms: int | None = None
    error: str | None = None
    event: threading.Event = field(default_factory=threading.Event, repr=False)

    def snapshot(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "action_id": self.action_id,
            "moment": self.moment,
            "state": self.state,
            "requested_at_ms": self.requested_at_ms,
            "delivered_at_ms": self.delivered_at_ms,
            "captured_at_ms": self.captured_at_ms,
            "cursor": dict(self.cursor) if self.cursor else None,
            "monitor": dict(self.monitor) if self.monitor else None,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "storage_path": self.storage_path,
            "delete_at_ms": self.delete_at_ms,
            "error": self.error,
            "analysis_ready": self.state == "STORED" and self.storage_path is not None,
        }


class CaptureBroker:
    """Queues capture requests for delivery in the agent's outbound HTTPS flow."""

    def __init__(self, storage_directory: Path, *, max_pending: int = 64,
                 max_records: int = 2048, max_bytes: int = 16 * 1024 * 1024,
                 max_total_bytes: int = 512 * 1024 * 1024):
        if min(max_pending, max_records, max_bytes, max_total_bytes) < 1:
            raise ValueError("capture limits must be positive")
        self.storage_directory = Path(storage_directory)
        self._max_pending = max_pending
        self._max_records = max_records
        self._max_bytes = max_bytes
        self._max_total_bytes = max_total_bytes
        self._records: dict[str, CaptureRecord] = {}
        self._order: deque[str] = deque()
        self._pending: deque[str] = deque()
        self._lock = threading.Lock()

    def request_capture(self, action_id: str, moment: str, *,
                        retention_seconds: int = 86_400, timeout: float = 8.0) -> dict[str, Any]:
        if moment not in ("before", "after"):
            raise ValueError("capture moment must be before or after")
        if not 0 <= retention_seconds <= 2_592_000:
            raise ValueError("capture retention outside allowed bounds")
        if not 0.1 <= timeout <= 30:
            raise ValueError("capture timeout outside allowed bounds")
        now = int(time.time() * 1000)
        record = CaptureRecord(
            capture_id=str(uuid.uuid4()), action_id=action_id, moment=moment,
            requested_at_ms=now, expires_at_ms=now + int(timeout * 1000),
            retention_seconds=retention_seconds, max_bytes=self._max_bytes,
        )
        with self._lock:
            self._prune_locked(now)
            if len(self._pending) >= self._max_pending:
                raise RuntimeError("capture request capacity exceeded")
            self._make_record_room_locked()
            self._records[record.capture_id] = record
            self._order.append(record.capture_id)
            self._pending.append(record.capture_id)
        if not record.event.wait(timeout):
            with self._lock:
                if record.state in ("PENDING", "DELIVERED"):
                    record.state = "FAILED"
                    record.error = "capture response deadline exceeded"
                    record.event.set()
            raise TimeoutError("capture response deadline exceeded")
        snapshot = record.snapshot()
        if record.state not in ("STORED", "DELETED") or record.captured_at_ms is None:
            raise RuntimeError(record.error or "capture failed")
        return snapshot

    def next_request(self) -> dict[str, Any] | None:
        now = int(time.time() * 1000)
        with self._lock:
            self._prune_locked(now)
            while self._pending:
                identifier = self._pending.popleft()
                record = self._records.get(identifier)
                if record is None or record.state != "PENDING":
                    continue
                if now > record.expires_at_ms:
                    record.state = "FAILED"
                    record.error = "capture request expired before delivery"
                    record.event.set()
                    continue
                record.state = "DELIVERED"
                record.delivered_at_ms = now
                return {
                    "capture_id": record.capture_id,
                    "action_id": record.action_id,
                    "moment": record.moment,
                    "expires_at_ms": record.expires_at_ms,
                    "max_bytes": record.max_bytes,
                    "format": "png",
                }
        return None

    def accept_upload(self, body: bytes) -> dict[str, Any]:
        if len(body) > (self._max_bytes * 4 // 3) + 16_384:
            raise ValueError("capture envelope too large")
        payload = json.loads(body.decode("utf-8"))
        identifier = str(payload.get("capture_id", ""))
        with self._lock:
            record = self._records.get(identifier)
            if record is None:
                raise ValueError("unknown capture id")
            if record.state != "DELIVERED":
                raise ValueError("capture is not awaiting an upload")
            if str(payload.get("action_id", "")) != record.action_id or payload.get("moment") != record.moment:
                raise ValueError("capture correlation mismatch")
            now = int(time.time() * 1000)
            if now > record.expires_at_ms:
                record.state = "FAILED"
                record.error = "capture upload expired"
                record.event.set()
                raise ValueError("capture upload expired")
            if payload.get("state") != "CAPTURED":
                record.state = "FAILED"
                record.error = str(payload.get("error", "capture agent failed"))[:512]
                record.event.set()
                return record.snapshot()
        try:
            image = base64.b64decode(str(payload["image_base64"]), validate=True)
        except (KeyError, ValueError, binascii.Error) as exc:
            raise ValueError("invalid capture image encoding") from exc
        if not image or len(image) > self._max_bytes:
            raise ValueError("capture image outside size bounds")
        if not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("capture is not a PNG image")
        cursor = payload.get("cursor")
        monitor = payload.get("monitor")
        if not isinstance(cursor, dict) or not isinstance(monitor, dict):
            raise ValueError("capture metadata is incomplete")
        x, y = int(cursor["x"]), int(cursor["y"])
        mx, my = int(monitor["x"]), int(monitor["y"])
        width, height = int(monitor["width"]), int(monitor["height"])
        if not 1 <= width <= 16_384 or not 1 <= height <= 16_384:
            raise ValueError("capture monitor dimensions outside bounds")
        if not (mx <= x < mx + width and my <= y < my + height):
            raise ValueError("capture monitor does not contain cursor")
        captured_at = int(payload["captured_at_ms"])
        if abs(int(time.time() * 1000) - captured_at) > 30_000:
            raise ValueError("capture timestamp outside allowed window")
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        destination = self.storage_directory / f"{identifier}.png"
        temporary = self.storage_directory / f".{identifier}.tmp"
        temporary.write_bytes(image)
        temporary.replace(destination)
        with self._lock:
            record = self._records[identifier]
            record.state = "STORED"
            record.captured_at_ms = captured_at
            record.cursor = {"x": x, "y": y}
            record.monitor = {
                "x": mx, "y": my, "width": width, "height": height,
                "primary": bool(monitor.get("primary", False)),
            }
            record.content_type = "image/png"
            record.size_bytes = len(image)
            record.storage_path = str(destination)
            record.delete_at_ms = captured_at + record.retention_seconds * 1000
            record.event.set()
            snapshot = record.snapshot()
            self._prune_locked(int(time.time() * 1000))
        return snapshot

    def fail_upload(self, body: bytes) -> dict[str, Any]:
        return self.accept_upload(body)

    def get(self, capture_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(capture_id)
            if record is None:
                raise KeyError("unknown capture id")
            return record.snapshot()

    def list_for_action(self, action_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [self._records[item].snapshot() for item in self._order
                    if self._records[item].action_id == action_id]

    def delete(self, capture_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(capture_id)
            if record is None:
                raise KeyError("unknown capture id")
            self._delete_file_locked(record)
            record.state = "DELETED"
            record.delete_at_ms = int(time.time() * 1000)
            return record.snapshot()

    def prune(self) -> int:
        with self._lock:
            return self._prune_locked(int(time.time() * 1000))

    def _make_record_room_locked(self) -> None:
        while len(self._records) >= self._max_records:
            identifier = self._order[0]
            record = self._records[identifier]
            if record.state in ("PENDING", "DELIVERED"):
                raise RuntimeError("capture record capacity exceeded")
            self._order.popleft()
            self._delete_file_locked(record)
            del self._records[identifier]

    def _prune_locked(self, now: int) -> int:
        removed = 0
        total = 0
        stored: list[CaptureRecord] = []
        for identifier in list(self._order):
            record = self._records[identifier]
            if record.state in ("PENDING", "DELIVERED") and now > record.expires_at_ms:
                record.state = "FAILED"
                record.error = "capture request expired"
                record.event.set()
            if record.state == "STORED" and record.delete_at_ms is not None and now >= record.delete_at_ms:
                self._delete_file_locked(record)
                record.state = "DELETED"
                removed += 1
            if record.state == "STORED" and record.size_bytes:
                total += record.size_bytes
                stored.append(record)
        if total > self._max_total_bytes:
            for record in sorted(stored, key=lambda item: item.captured_at_ms or 0):
                self._delete_file_locked(record)
                record.state = "DELETED"
                total -= record.size_bytes or 0
                removed += 1
                if total <= self._max_total_bytes:
                    break
        return removed

    @staticmethod
    def _delete_file_locked(record: CaptureRecord) -> None:
        if record.storage_path:
            try:
                Path(record.storage_path).unlink(missing_ok=True)
            except OSError as exc:
                record.error = f"capture deletion failed: {exc}"
                return
            record.storage_path = None
