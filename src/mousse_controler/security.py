"""Canonical HMAC authentication for outbound position samples."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import threading
import time


class AuthenticationError(ValueError):
    pass


def canonical_message(method: str, path: str, timestamp_ms: int, sequence: int, body: bytes) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return f"{method.upper()}\n{path}\n{timestamp_ms}\n{sequence}\n{digest}".encode("ascii")


def sign(secret: bytes, method: str, path: str, timestamp_ms: int, sequence: int, body: bytes) -> str:
    return hmac.new(
        secret,
        canonical_message(method, path, timestamp_ms, sequence, body),
        hashlib.sha256,
    ).hexdigest()


@dataclass
class HmacVerifier:
    keys: dict[str, bytes]
    max_clock_skew_ms: int = 5_000

    def __post_init__(self) -> None:
        self._last_sequence: dict[str, int] = {}
        self._lock = threading.Lock()

    def verify(
        self,
        key_id: str,
        signature: str,
        method: str,
        path: str,
        timestamp_ms: int,
        sequence: int,
        body: bytes,
        now_ms: int | None = None,
    ) -> None:
        secret = self.keys.get(key_id)
        if secret is None:
            raise AuthenticationError("unknown key")
        current = int(time.time() * 1000) if now_ms is None else now_ms
        if abs(current - timestamp_ms) > self.max_clock_skew_ms:
            raise AuthenticationError("timestamp outside allowed window")
        expected = sign(secret, method, path, timestamp_ms, sequence, body)
        if not hmac.compare_digest(expected, signature.lower()):
            raise AuthenticationError("invalid signature")
        with self._lock:
            previous = self._last_sequence.get(key_id, -1)
            if sequence <= previous:
                raise AuthenticationError("replayed or unordered sequence")
            self._last_sequence[key_id] = sequence
