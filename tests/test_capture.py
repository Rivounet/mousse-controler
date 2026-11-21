from __future__ import annotations

import base64
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from mousse_controler.capture import CaptureBroker, CaptureQuotaError
from mousse_controler.controller import PositionStore
from mousse_controler.position_server import PositionReceiver
from mousse_controler.security import HmacVerifier, sign


PNG = b"\x89PNG\r\n\x1a\n" + b"bounded-test-image"


class CaptureBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.broker = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                    max_total_bytes=4096)

    def tearDown(self):
        self.temporary.cleanup()

    def start_request(self, **kwargs):
        outcome = {}

        def run():
            try:
                outcome["result"] = self.broker.request_capture(
                    "action-1", kwargs.pop("moment", "after"), **kwargs)
            except Exception as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=run)
        thread.start()
        deadline = time.monotonic() + 1
        request = None
        while request is None and time.monotonic() < deadline:
            request = self.broker.next_request()
            if request is None:
                time.sleep(0.005)
        self.assertIsNotNone(request)
        return thread, outcome, request

    @staticmethod
    def upload(request, **updates):
        payload = {
            "capture_id": request["capture_id"],
            "action_id": request["action_id"],
            "moment": request["moment"],
            "state": "CAPTURED",
            "captured_at_ms": int(time.time() * 1000),
            "cursor": {"x": -100, "y": 50},
            "monitor": {"x": -1920, "y": 0, "width": 1920, "height": 1080,
                        "primary": False},
            "image_base64": base64.b64encode(PNG).decode("ascii"),
        }
        payload.update(updates)
        return json.dumps(payload, separators=(",", ":")).encode()

    def test_negative_coordinate_monitor_capture_is_stored_and_correlated(self):
        thread, outcome, request = self.start_request(retention_seconds=60, timeout=1)
        stored = self.broker.accept_upload(self.upload(request))
        thread.join(1)
        self.assertNotIn("error", outcome)
        self.assertEqual(stored["state"], "STORED")
        self.assertEqual(stored["cursor"], {"x": -100, "y": 50})
        self.assertTrue(Path(stored["storage_path"]).is_file())
        self.assertTrue(stored["analysis_ready"])

    def test_monitor_must_contain_cursor(self):
        thread, outcome, request = self.start_request(timeout=0.2)
        with self.assertRaisesRegex(ValueError, "does not contain"):
            self.broker.accept_upload(self.upload(
                request, monitor={"x": 0, "y": 0, "width": 100, "height": 100}))
        thread.join(1)
        self.assertIsInstance(outcome.get("error"), TimeoutError)

    def test_agent_failure_is_returned_without_file(self):
        thread, outcome, request = self.start_request(timeout=1)
        failed = json.dumps({
            "capture_id": request["capture_id"], "action_id": "action-1",
            "moment": "after", "state": "FAILED", "error": "secure desktop",
        }).encode()
        result = self.broker.accept_upload(failed)
        thread.join(1)
        self.assertEqual(result["state"], "FAILED")
        self.assertIsInstance(outcome.get("error"), RuntimeError)

    def test_explicit_delete_removes_private_image(self):
        thread, outcome, request = self.start_request(timeout=1)
        stored = self.broker.accept_upload(self.upload(request))
        thread.join(1)
        path = Path(stored["storage_path"])
        deleted = self.broker.delete(request["capture_id"])
        self.assertEqual(deleted["state"], "DELETED")
        self.assertFalse(path.exists())

    def test_delete_refusal_is_persisted_and_can_be_retried_after_restart(self):
        thread, outcome, request = self.start_request(timeout=1)
        stored = self.broker.accept_upload(self.upload(request))
        thread.join(1)
        path = Path(stored["storage_path"])
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            failed = self.broker.delete(request["capture_id"])
        self.assertEqual(failed["state"], "DELETE_FAILED")
        self.assertIn("deletion failed", failed["error"])
        self.assertEqual(failed["storage_path"], str(path))
        self.assertTrue(path.is_file())

        recovered = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                  max_total_bytes=4096)
        retained = recovered.get(request["capture_id"])
        self.assertEqual(retained["state"], "DELETE_FAILED")
        self.assertEqual(retained["storage_path"], str(path))
        deleted = recovered.delete(request["capture_id"])
        self.assertEqual(deleted["state"], "DELETED")
        self.assertIsNone(deleted["storage_path"])
        self.assertFalse(path.exists())

    def test_quota_refuses_upload_before_any_image_write(self):
        thread, outcome, request = self.start_request(timeout=1)
        used = self.broker.quota_status()["used_bytes"]
        self.broker._max_total_bytes = used + len(PNG)
        with self.assertRaises(CaptureQuotaError):
            self.broker.accept_upload(self.upload(request))
        thread.join(1)
        self.assertIsInstance(outcome.get("error"), RuntimeError)
        self.assertEqual(self.broker.get(request["capture_id"])["state"], "FAILED")
        self.assertFalse((Path(self.temporary.name) / f"{request['capture_id']}.png").exists())
        status = self.broker.quota_status()
        self.assertLessEqual(status["used_bytes"], status["max_total_bytes"])

    def test_restart_recovers_unindexed_capture_file_for_controlled_deletion(self):
        orphan = Path(self.temporary.name) / "orphan.png"
        orphan.write_bytes(PNG)
        recovered = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                  max_total_bytes=4096)
        records = recovered.list_for_action("__recovered__")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["state"], "DELETE_FAILED")
        self.assertEqual(records[0]["storage_path"], str(orphan))
        deleted = recovered.delete(records[0]["capture_id"])
        self.assertEqual(deleted["state"], "DELETED")
        self.assertFalse(orphan.exists())

    def test_delete_checks_expected_file_even_when_record_has_no_storage_path(self):
        thread, outcome, request = self.start_request(timeout=0.1)
        thread.join(1)
        self.assertIsInstance(outcome.get("error"), TimeoutError)
        late_file = Path(self.temporary.name) / f"{request['capture_id']}.png"
        late_file.write_bytes(PNG)
        deleted = self.broker.delete(request["capture_id"])
        self.assertEqual(deleted["state"], "DELETED")
        self.assertFalse(late_file.exists())

    def test_restart_reconciles_deleted_record_with_late_file(self):
        thread, outcome, request = self.start_request(timeout=0.1)
        thread.join(1)
        self.assertIsInstance(outcome.get("error"), TimeoutError)
        self.assertEqual(self.broker.delete(request["capture_id"])["state"], "DELETED")
        late_file = Path(self.temporary.name) / f"{request['capture_id']}.png"
        late_file.write_bytes(PNG)

        restarted = CaptureBroker(Path(self.temporary.name), max_bytes=1024,
                                  max_total_bytes=4096)
        retained = restarted.get(request["capture_id"])
        self.assertEqual(retained["state"], "DELETE_FAILED")
        self.assertEqual(retained["storage_path"], str(late_file))
        self.assertEqual(restarted.list_for_action("__recovered__"), [])

    def test_duplicate_upload_is_rejected(self):
        thread, outcome, request = self.start_request(timeout=1)
        body = self.upload(request)
        self.broker.accept_upload(body)
        thread.join(1)
        with self.assertRaisesRegex(ValueError, "not awaiting"):
            self.broker.accept_upload(body)

    def test_upload_size_and_png_type_are_bounded(self):
        thread, outcome, request = self.start_request(timeout=0.2)
        bad = self.upload(request, image_base64=base64.b64encode(b"not-png").decode())
        with self.assertRaisesRegex(ValueError, "not a PNG"):
            self.broker.accept_upload(bad)
        thread.join(1)
        self.assertIn("error", outcome)

    def test_capture_endpoint_requires_hmac_and_prevents_replay(self):
        secret = b"capture-secret"
        receiver = PositionReceiver(PositionStore(), HmacVerifier({"agent": secret}), self.broker)
        thread, outcome, request = self.start_request(timeout=1)
        body = self.upload(request)
        now = int(time.time() * 1000)
        headers = {
            "X-Agent-Key": "agent", "X-Timestamp": str(now), "X-Sequence": "5",
            "X-Signature": sign(secret, "POST", "/v1/capture", now, 5, body),
        }
        receiver.accept_capture(headers, body)
        thread.join(1)
        with self.assertRaisesRegex(ValueError, "replayed"):
            receiver.accept_capture(headers, body)

    def test_only_before_or_after_moments_are_allowed(self):
        with self.assertRaisesRegex(ValueError, "before or after"):
            self.broker.request_capture("action", "periodic", timeout=0.1)


if __name__ == "__main__":
    unittest.main()
