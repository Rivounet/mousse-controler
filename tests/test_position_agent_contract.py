from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
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

    def test_interactive_manager_supports_reconnect_only_mode(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        self.assertIn("HogpReconnect", source)
        self.assertIn("--hogp-reconnect", source)


if __name__ == "__main__":
    unittest.main()
