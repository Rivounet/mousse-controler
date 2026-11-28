from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "position-agent" / "PositionAgent.cs"
MANAGER = ROOT / "scripts" / "target" / "Manage-InteractivePositionAgent.ps1"


class PositionAgentSeparationContractTests(unittest.TestCase):
    def test_agent_has_no_bluetooth_client_or_reconnect_mode(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "Windows.Devices.Bluetooth",
            "Windows.Devices.Enumeration",
            "BluetoothLEDevice",
            "GattSession",
            "MaintainConnection",
            "HogpReconnectMonitor",
            "--hogp-reconnect",
        ):
            self.assertNotIn(forbidden, source)

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

    def test_interactive_manager_only_starts_telemetry_mode(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        self.assertIn("--config", source)
        self.assertNotIn("HogpReconnect", source)
        self.assertNotIn("--hogp-reconnect", source)
        self.assertNotIn("HogpPairedAepIdSha256", source)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", source)

    def test_agent_build_does_not_require_winrt_contracts(self) -> None:
        source = (ROOT / "scripts" / "build" / "Build-PositionAgent.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("RequireWindowsSdk", source)
        self.assertNotIn("WindowsMetadata", source)
        self.assertNotIn("UniversalContract", source)


if __name__ == "__main__":
    unittest.main()
