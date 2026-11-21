"""Authenticated, bounded one-shot screen capture broker and retention store."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
import base64
import binascii
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid
from typing import Any, Callable


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


class CaptureQuotaError(RuntimeError):
    """The capture cannot be admitted without exceeding a hard storage bound."""


class CaptureBroker:
    """Queues capture requests for delivery in the agent's outbound HTTPS flow."""

    def __init__(self, storage_directory: Path, *, max_pending: int = 64,
                 max_records: int = 2048, max_bytes: int = 16 * 1024 * 1024,
                 max_total_bytes: int = 512 * 1024 * 1024,
                 storage_observer: Callable[[str, int], None] | None = None):
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
        self._index_path = self.storage_directory / ".capture-index.json"
        self._storage_observer = storage_observer
        self._load_index()

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
            try:
                self._persist_index_locked()
            except BaseException:
                self._pending.remove(record.capture_id)
                self._order.remove(record.capture_id)
                del self._records[record.capture_id]
                raise
        if not record.event.wait(timeout):
            with self._lock:
                if record.state in ("PENDING", "DELIVERED"):
                    record.state = "FAILED"
                    record.error = "capture response deadline exceeded"
                    record.event.set()
                    self._persist_index_locked()
            raise TimeoutError("capture response deadline exceeded")
        snapshot = record.snapshot()
        if record.state not in ("STORED", "DELETED") or record.captured_at_ms is None:
            raise RuntimeError(record.error or "capture failed")
        return snapshot

    def next_request(self) -> dict[str, Any] | None:
        now = int(time.time() * 1000)
        with self._lock:
            self._prune_locked(now)
            self._persist_index_locked()
            while self._pending:
                identifier = self._pending.popleft()
                record = self._records.get(identifier)
                if record is None or record.state != "PENDING":
                    continue
                if now > record.expires_at_ms:
                    record.state = "FAILED"
                    record.error = "capture request expired before delivery"
                    record.event.set()
                    self._persist_index_locked()
                    continue
                record.state = "DELIVERED"
                record.delivered_at_ms = now
                self._persist_index_locked()
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
                self._persist_index_locked()
                raise ValueError("capture upload expired")
            if payload.get("state") != "CAPTURED":
                record.state = "FAILED"
                record.error = str(payload.get("error", "capture agent failed"))[:512]
                record.event.set()
                self._persist_index_locked()
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
        with self._lock:
            record = self._records[identifier]
            if record.state != "DELIVERED":
                raise ValueError("capture is not awaiting an upload")
            self.storage_directory.mkdir(parents=True, exist_ok=True)
            self._observe_storage_locked("upload_begin")
            destination = self.storage_directory / f"{identifier}.png"
            temporary = self.storage_directory / f".{identifier}.tmp"
            if destination.exists() or temporary.exists():
                raise RuntimeError("capture storage path already exists")
            candidate = replace(
                record, state="STORED", captured_at_ms=captured_at,
                cursor={"x": x, "y": y}, monitor={
                "x": mx, "y": my, "width": width, "height": height,
                "primary": bool(monitor.get("primary", False)),
                }, content_type="image/png", size_bytes=len(image),
                storage_path=str(destination),
                delete_at_ms=captured_at + record.retention_seconds * 1000,
                error=None,
            )
            self._records[identifier] = candidate
            try:
                prospective_index = self._encode_index_locked()
            finally:
                self._records[identifier] = record
            try:
                self._ensure_upload_capacity_locked(len(image), len(prospective_index))
            except CaptureQuotaError as exc:
                record.state = "FAILED"
                record.error = str(exc)
                record.event.set()
                try:
                    self._persist_index_locked()
                except CaptureQuotaError:
                    pass
                raise
            try:
                self._ensure_allocation_capacity_locked(
                    len(image), "capture image temporary",
                )
                with temporary.open("xb") as stream:
                    stream.write(image)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._observe_storage_locked("image_temporary_written")
                temporary.replace(destination)
                self._observe_storage_locked("image_committed")
                record.state = candidate.state
                record.captured_at_ms = candidate.captured_at_ms
                record.cursor = candidate.cursor
                record.monitor = candidate.monitor
                record.content_type = candidate.content_type
                record.size_bytes = candidate.size_bytes
                record.storage_path = candidate.storage_path
                record.delete_at_ms = candidate.delete_at_ms
                record.error = None
                self._prune_locked(int(time.time() * 1000))
                self._persist_index_locked()
            except BaseException as exc:
                remaining = (destination if destination.is_file() else
                             temporary if temporary.is_file() else None)
                if remaining is not None:
                    record.state = "DELETE_FAILED"
                    record.storage_path = str(remaining)
                    record.size_bytes = remaining.stat().st_size
                    record.error = f"capture storage transaction interrupted: {exc}"
                else:
                    record.state = "FAILED"
                    record.error = f"capture storage transaction failed: {exc}"
                record.event.set()
                try:
                    self._persist_index_locked()
                except BaseException:
                    pass
                raise
            record.event.set()
            return record.snapshot()

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
            if self._delete_file_locked(record):
                record.state = "DELETED"
                record.delete_at_ms = int(time.time() * 1000)
                record.error = None
            self._persist_index_locked()
            return record.snapshot()

    def prune(self) -> int:
        with self._lock:
            removed = self._prune_locked(int(time.time() * 1000))
            self._persist_index_locked()
            return removed

    def quota_status(self) -> dict[str, int | bool]:
        with self._lock:
            used = self._directory_usage_locked()
            return {
                "used_bytes": used,
                "max_total_bytes": self._max_total_bytes,
                "available_bytes": max(0, self._max_total_bytes - used),
                "over_quota": used > self._max_total_bytes,
            }

    def _make_record_room_locked(self) -> None:
        while len(self._records) >= self._max_records:
            evicted = False
            for identifier in list(self._order):
                record = self._records[identifier]
                if record.state in ("PENDING", "DELIVERED"):
                    continue
                if not self._delete_file_locked(record):
                    continue
                self._order.remove(identifier)
                del self._records[identifier]
                evicted = True
                break
            if not evicted:
                self._persist_index_locked()
                raise RuntimeError("capture record capacity exceeded by retained files")

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
            if (record.state in ("STORED", "DELETE_FAILED") and
                    record.delete_at_ms is not None and now >= record.delete_at_ms):
                if self._delete_file_locked(record):
                    record.state = "DELETED"
                    record.error = None
                    removed += 1
            if record.state in ("STORED", "DELETE_FAILED") and record.size_bytes:
                total += record.size_bytes
                stored.append(record)
        if total > self._max_total_bytes:
            for record in sorted(stored, key=lambda item: item.captured_at_ms or 0):
                if self._delete_file_locked(record):
                    record.state = "DELETED"
                    record.error = None
                    total -= record.size_bytes or 0
                    removed += 1
                if total <= self._max_total_bytes:
                    break
        return removed

    def _delete_file_locked(self, record: CaptureRecord) -> bool:
        paths = ([Path(record.storage_path)] if record.storage_path else [
            self.storage_directory / f"{record.capture_id}.png",
            self.storage_directory / f".{record.capture_id}.tmp",
        ])
        for path in paths:
            try:
                path.unlink(missing_ok=True)
                if path.exists():
                    raise OSError("capture file still exists after deletion")
            except OSError as exc:
                record.storage_path = str(path)
                if record.size_bytes is None:
                    try:
                        if path.is_file():
                            record.size_bytes = path.stat().st_size
                    except OSError:
                        pass
                record.state = "DELETE_FAILED"
                record.error = f"capture deletion failed: {exc}"
                return False
        record.storage_path = None
        return True

    def _load_index(self) -> None:
        if not self.storage_directory.exists():
            return
        changed = False
        if self._index_path.exists():
            try:
                if self._index_path.stat().st_size > 8 * 1024 * 1024:
                    raise RuntimeError("capture index exceeds safe size")
                payload = json.loads(self._index_path.read_text(encoding="utf-8"))
                if payload.get("version") != 1 or not isinstance(payload.get("records"), list):
                    raise ValueError("unsupported capture index")
                for data in payload["records"]:
                    record = self._record_from_index(data)
                    if record.state in ("PENDING", "DELIVERED"):
                        record.state = "FAILED"
                        record.error = "capture interrupted by service restart"
                        record.event.set()
                        changed = True
                    recorded_path = Path(record.storage_path) if record.storage_path else None
                    expected_paths = [
                        self.storage_directory / f"{record.capture_id}.png",
                        self.storage_directory / f".{record.capture_id}.tmp",
                    ]
                    candidates = ([recorded_path] if recorded_path else []) + expected_paths
                    existing_path = next((path for path in dict.fromkeys(candidates)
                                          if path.is_file()), None)
                    if existing_path is None and record.storage_path:
                        record.storage_path = None
                        record.state = "DELETED"
                        record.error = None
                        changed = True
                    elif existing_path is not None and (
                            record.state == "DELETED" or recorded_path != existing_path):
                        record.storage_path = str(existing_path)
                        record.size_bytes = existing_path.stat().st_size
                        record.state = "DELETE_FAILED"
                        record.error = "capture file still present after recorded deletion"
                        changed = True
                    self._records[record.capture_id] = record
                    self._order.append(record.capture_id)
            except (OSError, RuntimeError, TypeError, ValueError, KeyError,
                    json.JSONDecodeError):
                self._records.clear()
                self._order.clear()
                invalid = self.storage_directory / (
                    f".capture-index.invalid-{uuid.uuid4()}.json"
                )
                try:
                    self._index_path.replace(invalid)
                except OSError as exc:
                    raise RuntimeError("capture index is invalid and cannot be preserved") from exc
                changed = True
        tracked = {Path(record.storage_path).name for record in self._records.values()
                   if record.storage_path}
        candidates = (list(self.storage_directory.glob("*.png")) +
                      list(self.storage_directory.glob(".*.tmp")))
        for path in candidates:
            if path.name in tracked:
                continue
            now = int(path.stat().st_mtime * 1000)
            identifier = f"recovered-{uuid.uuid4()}"
            record = CaptureRecord(
                capture_id=identifier, action_id="__recovered__", moment="recovered",
                requested_at_ms=now, expires_at_ms=now, retention_seconds=0,
                max_bytes=self._max_bytes, state="DELETE_FAILED", captured_at_ms=now,
                content_type="image/png" if path.suffix.lower() == ".png" else None,
                size_bytes=path.stat().st_size, storage_path=str(path), delete_at_ms=now,
                error="capture file recovered after unclean shutdown",
            )
            self._records[identifier] = record
            self._order.append(identifier)
            changed = True
        if len(self._records) > self._max_records:
            raise RuntimeError("retained capture files exceed record capacity")
        if changed:
            self._persist_index_locked()

    def _record_from_index(self, data: dict[str, Any]) -> CaptureRecord:
        identifier = str(data["capture_id"])
        raw_identifier = (identifier.removeprefix("recovered-")
                          if identifier.startswith("recovered-") else identifier)
        try:
            uuid.UUID(raw_identifier)
        except ValueError as exc:
            raise ValueError("invalid capture index identifier") from exc
        file_name = data.get("file_name")
        storage_path = None
        if file_name is not None:
            file_name = str(file_name)
            if Path(file_name).name != file_name:
                raise ValueError("invalid capture index file name")
            storage_path = str(self.storage_directory / file_name)
        return CaptureRecord(
            capture_id=identifier, action_id=str(data["action_id"]),
            moment=str(data["moment"]), requested_at_ms=int(data["requested_at_ms"]),
            expires_at_ms=int(data["expires_at_ms"]),
            retention_seconds=int(data["retention_seconds"]),
            max_bytes=int(data["max_bytes"]), state=str(data["state"]),
            delivered_at_ms=data.get("delivered_at_ms"),
            captured_at_ms=data.get("captured_at_ms"), cursor=data.get("cursor"),
            monitor=data.get("monitor"), content_type=data.get("content_type"),
            size_bytes=data.get("size_bytes"), storage_path=storage_path,
            delete_at_ms=data.get("delete_at_ms"), error=data.get("error"),
        )

    def _encode_index_locked(self) -> bytes:
        records = []
        for identifier in self._order:
            record = self._records[identifier]
            snapshot = record.snapshot()
            snapshot.pop("analysis_ready", None)
            storage_path = snapshot.pop("storage_path", None)
            snapshot["file_name"] = Path(storage_path).name if storage_path else None
            snapshot["retention_seconds"] = record.retention_seconds
            snapshot["max_bytes"] = record.max_bytes
            snapshot["expires_at_ms"] = record.expires_at_ms
            records.append(snapshot)
        return json.dumps(
            {"version": 1, "records": records}, separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def _directory_usage_locked(self) -> int:
        if not self.storage_directory.exists():
            return 0
        total = 0
        for root, directories, files in os.walk(self.storage_directory, followlinks=False):
            directories[:] = [name for name in directories
                              if not (Path(root) / name).is_symlink()]
            for name in files:
                try:
                    total += (Path(root) / name).lstat().st_size
                except FileNotFoundError:
                    continue
        return total

    def _ensure_disk_space_locked(self, additional_bytes: int) -> None:
        free = shutil.disk_usage(self.storage_directory).free
        if free < additional_bytes:
            raise CaptureQuotaError(
                f"capture storage has insufficient free space: need {additional_bytes}, free {free}"
            )

    def _ensure_allocation_capacity_locked(self, additional_bytes: int,
                                           allocation: str) -> int:
        current = self._directory_usage_locked()
        peak = current + additional_bytes
        if peak > self._max_total_bytes:
            raise CaptureQuotaError(
                f"capture quota admission denied for {allocation}: peak {peak} exceeds "
                f"{self._max_total_bytes}"
            )
        self._ensure_disk_space_locked(additional_bytes)
        return peak

    def _ensure_upload_capacity_locked(self, image_size: int, index_size: int) -> int:
        # Transaction stages and physical peaks:
        #   1. current index/files + image temporary;
        #   2. current index/files + image final (rename, same byte count);
        #   3. current index/files + image final + unique index temporary;
        #   4. image final + new index (atomic replacement lowers usage).
        # No existing file is subtracted before it has physically disappeared.
        return self._ensure_allocation_capacity_locked(
            image_size + index_size, "capture image and atomic index",
        )

    def _observe_storage_locked(self, stage: str) -> int:
        used = self._directory_usage_locked()
        if used > self._max_total_bytes:
            raise RuntimeError(
                f"capture quota invariant violated at {stage}: "
                f"{used} exceeds {self._max_total_bytes}"
            )
        if self._storage_observer is not None:
            self._storage_observer(stage, used)
        return used

    def _persist_index_locked(self) -> None:
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        encoded = self._encode_index_locked()
        self._ensure_allocation_capacity_locked(len(encoded), "atomic index temporary")
        temporary = self.storage_directory / f".capture-index.{uuid.uuid4()}.tmp"
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        self._observe_storage_locked("index_temporary_written")
        temporary.replace(self._index_path)
        self._observe_storage_locked("index_committed")
