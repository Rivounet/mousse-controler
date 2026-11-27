from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from scripts.qualification.qualify_mouse_actions_runtime import (
    QualificationLeaseGuard,
    validate_qualification_lease_pair,
)


class QualificationLeasePairTests(unittest.TestCase):
    def write_pair(self, directory: str, *, target_peer: str = "MINI-PC-BACKEND"):
        now = datetime.now(timezone.utc)
        run_id = str(uuid.uuid4())
        sha = "a" * 40
        common = {
            "schema": "mousse-qualification-lease-v1",
            "run_id": run_id,
            "git_sha": sha,
            "expires_at_utc": (now + timedelta(minutes=3)).isoformat(),
        }
        backend = {
            **common,
            "role": "backend",
            "machine": "MINI-PC-BACKEND",
            "peer_host": "DESKTOP-NPIHO8K",
            "owner_token_sha256": "B" * 64,
        }
        target = {
            **common,
            "role": "target",
            "machine": "DESKTOP-NPIHO8K",
            "peer_host": target_peer,
            "active": True,
            "observed_at_utc": now.isoformat(),
        }
        backend_path = Path(directory) / "backend.json"
        target_path = Path(directory) / "target.json"
        backend_path.write_text(json.dumps(backend), encoding="utf-8")
        target_path.write_text(json.dumps(target), encoding="utf-8")
        return backend_path, target_path, run_id, sha

    def test_matching_active_pair_is_accepted_without_exposing_owner_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, target, run_id, sha = self.write_pair(directory)

            result = validate_qualification_lease_pair(
                backend, target, run_id, sha)

            self.assertEqual(result["backend"], "MINI-PC-BACKEND")
            self.assertEqual(result["target"], "DESKTOP-NPIHO8K")
            self.assertNotIn("owner_token_sha256", result)

    def test_peer_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, target, run_id, sha = self.write_pair(
                directory, target_peer="OTHER-HOST")

            with self.assertRaisesRegex(ValueError, "peers do not match"):
                validate_qualification_lease_pair(backend, target, run_id, sha)

    def test_guard_reloads_lease_state_before_later_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, target, run_id, sha = self.write_pair(directory)
            guard = QualificationLeaseGuard(backend, target, run_id, sha)
            state = json.loads(backend.read_text(encoding="utf-8"))
            state["expires_at_utc"] = (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            ).isoformat()
            backend.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "backend qualification lease has expired"):
                guard.check()


if __name__ == "__main__":
    unittest.main()
