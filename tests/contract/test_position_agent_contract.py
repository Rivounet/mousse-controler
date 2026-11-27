from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "position-agent" / "PositionAgent.cs"
MANAGER = ROOT / "scripts" / "target" / "Manage-InteractivePositionAgent.ps1"


class PositionAgentReconnectContractTests(unittest.TestCase):
    def test_reconnect_uses_exact_paired_connectable_endpoint(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("StringComparison.Ordinal", source)
        self.assertIn("candidate.Pairing.IsPaired", source)
        self.assertIn('System.Devices.Aep.IsPresent', source)
        self.assertIn('System.Devices.Aep.Bluetooth.Le.IsConnectable', source)

    def test_reconnect_opens_uncached_hid_service(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("GattServiceUuids.HumanInterfaceDevice", source)
        self.assertIn("BluetoothCacheMode.Uncached", source)
        self.assertIn("result.Services.Count != 1", source)

    def test_agent_has_no_input_injection_api(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in ("SendInput", "mouse_event", "SetCursorPos"):
            self.assertNotIn(forbidden, source)

    def test_capture_is_one_shot_visible_and_monitor_scoped(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("CAPTURE VISIBLE", source)
        self.assertIn("graphics.CopyFromScreen(selected.X, selected.Y", source)
        self.assertIn("point.X >= display.X", source)
        self.assertIn("point.Y >= display.Y", source)
        self.assertIn('request.moment != "before" && request.moment != "after"', source)
        self.assertNotIn("HttpListener", source)
        self.assertNotIn("TcpListener", source)

    def test_capture_upload_reuses_tls_pin_hmac_and_bounded_sequence(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('Post(seq, timestamp, "/v1/capture", body)', source)
        self.assertIn("request.max_bytes > 16 * 1024 * 1024", source)
        self.assertIn("ServerCertificateValidationCallback = ValidateCertificate", source)
        self.assertIn("Interlocked.Increment(ref sequence)", source)

    def test_interactive_manager_supports_reconnect_only_mode(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        self.assertIn("HogpReconnect", source)
        self.assertIn("--hogp-reconnect", source)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", source)


if __name__ == "__main__":
    unittest.main()
