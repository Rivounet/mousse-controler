import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TargetUpdateContractTests(unittest.TestCase):
    def test_agent_update_is_task_scoped_hash_checked_and_reversible(self):
        source = (ROOT / "scripts" / "target" / "Update-InteractivePositionAgent.ps1").read_text(
            encoding="utf-8")
        self.assertIn("Get-ScheduledTask -TaskName $TaskName", source)
        self.assertIn("PositionAgent.exe", source)
        self.assertIn("Get-FileHash -Algorithm SHA256", source)
        self.assertIn(".mc-mouse-actions.previous", source)
        self.assertIn("PositionAgent did not stop within the bounded deadline", source)
        self.assertNotIn("Remove-Item -Recurse", source)

    def test_witness_is_visible_and_only_observes_mouse_messages(self):
        source = (ROOT / "scripts" / "qualification" / "MouseWitness.cs").read_text(
            encoding="utf-8")
        self.assertIn("SAFE MOUSE TEST SURFACE", source)
        self.assertIn("LEFT_DOWN", source)
        self.assertIn("DRAG_MOVE", source)
        self.assertIn("WHEEL_VERTICAL", source)
        self.assertIn("IMessageFilter", source)
        self.assertIn("target.FindForm() != this", source)
        for forbidden in ("SendInput", "mouse_event", "SetCursorPos", "CopyFromScreen"):
            self.assertNotIn(forbidden, source)

    def test_witness_launcher_uses_a_scoped_interactive_temporary_task(self):
        source = (ROOT / "scripts" / "qualification" /
                  "Start-InteractiveMouseQualification.ps1").read_text(encoding="utf-8")
        self.assertIn("MousseControler-MouseWitness-Qualification", source)
        self.assertIn("-LogonType Interactive -RunLevel Limited", source)
        self.assertIn("Register-ScheduledTask -TaskName $QualificationTaskName", source)
        self.assertIn("Unregister-ScheduledTask -TaskName $QualificationTaskName", source)
        self.assertIn("Refusing to manage unrelated task", source)
        self.assertNotIn("Start-Process -FilePath $witness", source)
        self.assertNotIn("Remove-Item -Recurse", source)

    def test_capture_evidence_export_is_cropped_inside_repository(self):
        source = (ROOT / "scripts" / "qualification" /
                  "qualify_mouse_actions_runtime.py").read_text(encoding="utf-8")
        self.assertIn("capture evidence directory must be inside the repository", source)
        self.assertIn("Export-CaptureEvidence.ps1", source)
        self.assertIn("capture_delete", source)
        self.assertIn("for attempt in range(3)", source)
        self.assertIn("finally:\n                deleted = invoke", source)
        exporter = (ROOT / "scripts" / "qualification" /
                    "Export-CaptureEvidence.ps1").read_text(encoding="utf-8")
        self.assertIn("Capture evidence crop exceeds source image bounds", exporter)
        self.assertIn("[Drawing.Rectangle]::new", exporter)
        self.assertIn("[Security.Cryptography.SHA256]::Create()", exporter)
        self.assertNotIn("Get-FileHash", exporter)
        self.assertNotIn("Remove-Item -Recurse", exporter)

    @unittest.skipUnless(os.name == "nt", "PowerShell capture exporter is Windows-only")
    def test_capture_evidence_export_computes_sha_without_get_file_hash(self):
        one_pixel_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        exporter = ROOT / "scripts" / "qualification" / "Export-CaptureEvidence.ps1"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            destination = Path(directory) / "evidence.png"
            source.write_bytes(one_pixel_png)
            completed = subprocess.run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(exporter),
                "-SourcePath", str(source),
                "-DestinationPath", str(destination),
                "-X", "0", "-Y", "0", "-Width", "1", "-Height", "1",
            ], check=True, capture_output=True, text=True)
            result = json.loads(completed.stdout)
            self.assertEqual(result["width"], 1)
            self.assertEqual(result["height"], 1)
            self.assertEqual(
                result["sha256"], hashlib.sha256(destination.read_bytes()).hexdigest().upper())


if __name__ == "__main__":
    unittest.main()
