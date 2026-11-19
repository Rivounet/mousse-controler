from __future__ import annotations

import json
import threading
import time
import unittest

from mousse_controler.controller import PositionStore
from mousse_controler.position_server import PositionReceiver
from mousse_controler.security import AuthenticationError, HmacVerifier, sign


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.secret = b"test-secret-not-for-production"
        self.verifier = HmacVerifier({"agent": self.secret})
        self.body = b'{}'
        self.now = 1_800_000_000_000

    def signature(self, sequence=1, timestamp=None):
        timestamp = self.now if timestamp is None else timestamp
        return sign(self.secret, "POST", "/v1/position", timestamp, sequence, self.body)

    def test_valid_signature_then_replay_rejected(self):
        signature = self.signature()
        self.verifier.verify("agent", signature, "POST", "/v1/position", self.now, 1, self.body, self.now)
        with self.assertRaisesRegex(AuthenticationError, "replayed"):
            self.verifier.verify("agent", signature, "POST", "/v1/position", self.now, 1, self.body, self.now)

    def test_bad_signature_does_not_consume_sequence(self):
        with self.assertRaisesRegex(AuthenticationError, "invalid"):
            self.verifier.verify("agent", "00" * 32, "POST", "/v1/position", self.now, 1, self.body, self.now)
        self.verifier.verify("agent", self.signature(), "POST", "/v1/position", self.now, 1, self.body, self.now)

    def test_old_timestamp_rejected(self):
        timestamp = self.now - 6000
        with self.assertRaisesRegex(AuthenticationError, "timestamp"):
            self.verifier.verify("agent", self.signature(timestamp=timestamp), "POST", "/v1/position", timestamp, 1, self.body, self.now)

    def test_concurrent_duplicate_sequence_is_accepted_once(self):
        barrier = threading.Barrier(8)
        outcomes = []

        def verify():
            barrier.wait()
            try:
                self.verifier.verify(
                    "agent", self.signature(sequence=9), "POST", "/v1/position",
                    self.now, 9, self.body, self.now,
                )
                outcomes.append("accepted")
            except AuthenticationError:
                outcomes.append("rejected")

        threads = [threading.Thread(target=verify) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(outcomes.count("accepted"), 1)
        self.assertEqual(outcomes.count("rejected"), 7)

    def test_receiver_accepts_bounded_position(self):
        now = int(time.time() * 1000)
        body = json.dumps({
            "x": -10,
            "y": 200,
            "session_id": 3,
            "topology_generation": "hash",
            "observed_at_unix_ms": now,
            "session_active": True,
            "displays": [{"x": 0, "y": 0, "width": 1920, "height": 1080}],
        }, separators=(",", ":")).encode()
        headers = {
            "X-Agent-Key": "agent",
            "X-Timestamp": str(now),
            "X-Sequence": "1",
            "X-Signature": sign(self.secret, "POST", "/v1/position", now, 1, body),
        }
        store = PositionStore()
        receiver = PositionReceiver(store, HmacVerifier({"agent": self.secret}))
        self.assertEqual(receiver.accept(headers, body), 1)
        self.assertEqual(store.latest().x, -10)
