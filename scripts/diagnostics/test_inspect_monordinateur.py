import json
import os
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("Inspect-MonOrdinateur.ps1")


@unittest.skipUnless(os.name == "nt", "Windows-only target diagnostic")
class TargetDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
        )
        cls.result = json.loads(completed.stdout)

    def test_is_explicitly_read_only(self):
        self.assertEqual(self.result["schema"], 2)
        self.assertEqual(self.result["diagnostic_mode"], "read-only")
        forbidden = self.result["not_executed"]
        self.assertIn("firewall change", forbidden)
        self.assertIn("mouse input injection", forbidden)
        self.assertIn("service or scheduled task creation", forbidden)

    def test_reports_cursor_reference_frame(self):
        cursor = self.result["cursor"]
        self.assertIsInstance(cursor["get_cursor_pos_succeeded"], bool)
        virtual = cursor["virtual_screen"]
        self.assertEqual({"left", "top", "width", "height"}, set(virtual))
        self.assertGreater(virtual["width"], 0)
        self.assertGreater(virtual["height"], 0)

    def test_omits_sensitive_network_and_identity_fields(self):
        serialized = json.dumps(self.result).lower()
        for forbidden in ("username", "computername", "macaddress", "ipaddress", "instanceid"):
            self.assertNotIn(forbidden, serialized)
        self.assertIn("no address", self.result["network"]["note"].lower())

    def test_reports_session_bluetooth_and_optional_network_probe(self):
        self.assertIn("input_desktop_readable", self.result["session"])
        self.assertIn("radio_state", self.result["bluetooth"])
        self.assertFalse(self.result["network"]["mini_pc_tcp_probe"]["requested"])


class GattProbeSafetyTests(unittest.TestCase):
    def test_probe_never_calls_start_advertising(self):
        probe = SCRIPT.parents[1] / "bluetooth" / "probe-gatt-shape.ps1"
        source = probe.read_text(encoding="utf-8")
        self.assertNotIn(".StartAdvertising(", source)
        self.assertIn("advertising_called = $false", source)

    def test_radio_diagnostic_cannot_change_radio_state(self):
        diagnostic = SCRIPT.with_name("Inspect-BluetoothRadio.ps1")
        source = diagnostic.read_text(encoding="utf-8")
        self.assertNotIn("[Windows.Devices.Radios.Radio]::RequestAccessAsync", source)
        self.assertNotIn(".SetStateAsync(", source)
        self.assertNotIn(".StartAdvertising(", source)


if __name__ == "__main__":
    unittest.main()
