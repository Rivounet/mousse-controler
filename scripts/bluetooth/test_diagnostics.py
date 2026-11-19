import json
import os
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("diagnose.ps1")


@unittest.skipUnless(os.name == "nt", "Windows-only Bluetooth diagnostic")
class BluetoothDiagnosticTests(unittest.TestCase):
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
            timeout=30,
        )
        cls.result = json.loads(completed.stdout)

    def test_declares_read_only_mode_and_forbidden_operations(self):
        self.assertEqual(self.result["diagnostic_mode"], "read-only")
        self.assertIn("BLE advertising", self.result["not_executed"])
        self.assertIn("HID report emission", self.result["not_executed"])

    def test_reports_real_adapter_capabilities(self):
        bluetooth = self.result["bluetooth"]
        self.assertTrue(bluetooth["adapter"]["name"])
        self.assertIsInstance(bluetooth["capabilities"]["peripheral_role"], bool)
        self.assertIsInstance(bluetooth["capabilities"]["low_energy"], bool)

    def test_reports_required_winrt_api_surface(self):
        api = self.result["bluetooth"]["winrt_api"]
        required = {
            "gatt_service_provider",
            "gatt_create_async",
            "gatt_start_advertising",
            "local_characteristic",
            "notify_value_async",
            "advertisement_publisher",
            "device_pairing",
        }
        self.assertEqual(required, set(api))
        self.assertTrue(all(isinstance(value, bool) for value in api.values()))


if __name__ == "__main__":
    unittest.main()
