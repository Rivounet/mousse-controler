from pathlib import Path
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
        for forbidden in ("SendInput", "mouse_event", "SetCursorPos", "CopyFromScreen"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
