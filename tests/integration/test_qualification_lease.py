from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification" / "Manage-QualificationLease.ps1"
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
    "System32/WindowsPowerShell/v1.0/powershell.exe"
)


@unittest.skipUnless(os.name == "nt" and POWERSHELL.is_file(), "Windows PowerShell required")
class QualificationLeaseTests(unittest.TestCase):
    def invoke(self, lease: Path, action: str, *arguments: str,
               check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
                "-Action", action, "-LeasePath", str(lease), *arguments,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=check,
        )

    def test_lease_is_exclusive_token_protected_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory) / "qualification-lease.json"
            run_id = str(uuid.uuid4())
            acquired = json.loads(self.invoke(
                lease, "Acquire", "-RunId", run_id, "-Role", "Backend",
                "-PeerHost", "DESKTOP-NPIHO8K", "-GitSha", "a" * 40,
                "-TtlSeconds", "60",
            ).stdout)
            self.assertTrue(acquired["active"])
            self.assertEqual(acquired["run_id"], run_id)
            token = acquired["owner_token"]
            self.assertRegex(token, r"^[0-9A-F]{64}$")

            status = json.loads(self.invoke(lease, "Status").stdout)
            self.assertTrue(status["active"])
            self.assertNotIn("owner_token", status)
            self.assertNotIn("owner_token_sha256", status)

            competing = self.invoke(
                lease, "Acquire", "-RunId", str(uuid.uuid4()),
                "-Role", "Backend", "-PeerHost", "DESKTOP-NPIHO8K",
                "-GitSha", "b" * 40, check=False,
            )
            self.assertNotEqual(competing.returncode, 0)
            self.assertIn("already leased", competing.stderr)

            unauthorized = self.invoke(
                lease, "Release", "-RunId", run_id,
                "-OwnerToken", "0" * 64, check=False,
            )
            self.assertNotEqual(unauthorized.returncode, 0)
            self.assertTrue(lease.is_file())

            renewed = json.loads(self.invoke(
                lease, "Renew", "-RunId", run_id,
                "-OwnerToken", token, "-TtlSeconds", "60",
            ).stdout)
            self.assertTrue(renewed["active"])

            released = json.loads(self.invoke(
                lease, "Release", "-RunId", run_id, "-OwnerToken", token,
            ).stdout)
            self.assertTrue(released["released"])
            self.assertFalse(lease.exists())


if __name__ == "__main__":
    unittest.main()
