from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HogpControlAgentContractTests(unittest.TestCase):
    def test_control_agent_never_becomes_a_gatt_or_input_client(self) -> None:
        source = (ROOT / "src" / "hogp-control-agent" / "HogpControlAgent.cs").read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "BluetoothLEDevice",
            "GattSession",
            "MaintainConnection",
            "GetGattServices",
            "PairAsync",
            "UnpairAsync",
            "SendInput",
            "SetCursorPos",
            "mouse_event",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("/v1/hogp-control", source)
        self.assertIn("Windows.Devices.Radios", source)
        self.assertIn("Win32_PnPEntity", source)
        self.assertIn('"System32", "pnputil.exe"', source)
        self.assertIn("expected exactly one enrolled PnP instance", source)
        self.assertIn("IsInRole(WindowsBuiltInRole.Administrator)", source)
        self.assertIn("DataProtectionScope.CurrentUser", source)
        self.assertIn("HMACSHA256", source)
        self.assertIn("response correlation mismatch", source)
        self.assertIn("--inspect-identities", source)
        self.assertIn("outcome_unknown", source)
        self.assertIn("not_required", source)
        self.assertIn("restart precondition is no longer satisfied", source)
        self.assertIn("File.Replace(temporary, statePath, null)", source)
        self.assertIn("another HOGP control agent owns this state", source)
        self.assertIn('"BTHLE\\\\DEV_"', source)
        self.assertIn('"BTHLEDEVICE\\\\"', source)
        self.assertIn('StartsWith("USB\\\\"', source)
        self.assertIn('StartsWith("PCI\\\\"', source)
        self.assertIn("expected exactly one enrolled PnP instance for role", source)
        self.assertIn("Task.WhenAny", source)
        self.assertIn("searcher.Options.Timeout", source)

    def test_agent_build_is_separate_and_uses_windows_metadata(self) -> None:
        source = (ROOT / "scripts" / "build" / "Build-HogpControlAgent.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("Resolve-MousseBuildTools -RequireWindowsSdk", source)
        self.assertIn("HogpControlAgent.exe", source)
        self.assertIn("System.Management.dll", source)
        self.assertNotIn("PositionAgent.exe", source)

    def test_deployed_control_agent_is_a_distinct_elevated_task(self) -> None:
        source = (ROOT / "scripts" / "target" / "Manage-HogpControlAgent.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("MousseControler-MC-HOGP-NATIVE-OWNER-001-ControlAgent", source)
        self.assertIn("-RunLevel Highest", source)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", source)
        self.assertIn("$env:ProgramFiles", source)
        self.assertIn("$env:ProgramData", source)
        self.assertIn("Set-ProtectedDirectoryAcl", source)
        self.assertIn("ExpectedExecutableSha256", source)
        self.assertIn("mousse-hogp-control-install-v1", source)
        self.assertIn("Assert-InstallationIntegrity", source)
        self.assertIn("principal_sid", source)
        self.assertIn("Resolve-PrincipalSid", source)
        self.assertIn("MSFT_TaskLogonTrigger", source)
        self.assertIn("LogonType.ToString() -ne 'Interactive'", source)
        self.assertIn("action.WorkingDirectory", source)
        self.assertNotIn("$env:LOCALAPPDATA", source)
        self.assertNotIn("PositionAgent", source)
        self.assertNotIn("PairingTool", source)

    def test_backend_control_plane_is_separate_from_mouse_commands(self) -> None:
        source = (ROOT / "src" / "mousse_controler" / "hogp_control.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"restart_bluetooth_adapter"', source)
        self.assertIn('"restart_paired_endpoint"', source)
        for forbidden in ("move(", "buttons(", "scroll(", "PairAsync", "GattSession"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
