from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "src" / "pairing-tool" / "PairingTool.cs"
MANAGER = ROOT / "scripts" / "target" / "Manage-InteractivePairing.ps1"
DIRECT_PAIRING = ROOT / "scripts" / "target" / "Pair-BluetoothDevice.ps1"
FINGERPRINT = (
    ROOT / "scripts" / "qualification" / "Get-BluetoothAddressFingerprint.ps1"
)
UNPAIR = (
    ROOT / "scripts" / "qualification" / "Unpair-BluetoothDeviceByAddress.ps1"
)


class PairingIdentityContractTests(unittest.TestCase):
    def test_pair_and_connect_require_an_expected_identity(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("NormalizeSha256(args[2])", source)
        self.assertIn("liveCandidates.TryGetValue(expectedIdSha256, out selected)", source)
        self.assertIn("No live Bluetooth LE endpoint matched the exact name and expected physical identity", source)
        self.assertEqual(source.count('{ "expected_id_sha256", expectedIdSha256 }'), 2)
        self.assertNotIn('Diagnostics["expected_id_sha256"]', source)

    def test_aep_duplicates_are_collapsed_by_hashed_physical_address(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn('"System.Devices.Aep.DeviceAddress"', source)
        self.assertIn("HashDeviceAddress(candidate)", source)
        self.assertIn('"identity_kind", "bluetooth_address_sha256"', source)
        self.assertIn("liveCandidates[identity] = candidate", source)
        self.assertNotIn("present && connectable", source)

    def test_inspection_correlates_name_connectable_advertisement_and_hid_service(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("BluetoothLEAdvertisementWatcher", source)
        self.assertIn("BluetoothLEScanningMode.Active", source)
        self.assertIn("BluetoothLEAdvertisementType.ConnectableUndirected", source)
        self.assertIn("GattServiceUuids.HumanInterfaceDevice", source)
        self.assertIn("ExactNameSeen && item.Value.ConnectableSeen", source)
        self.assertIn("item.Value.HidServiceSeen", source)
        self.assertIn("observedAdvertisementIdentity != expectedIdSha256", source)

    def test_new_pairing_requires_observed_encryption_and_rolls_back_otherwise(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("result.ProtectionLevelUsed.ToString()", source)
        self.assertIn("DevicePairingProtectionLevel.Encryption.ToString()", source)
        self.assertIn("device.Pairing.UnpairAsync()", source)
        self.assertIn("ExistingPairingRequiresExplicitUnpair", source)
        self.assertIn("RejectedProtectionLevel", source)

    def test_connect_refuses_an_unpaired_endpoint_even_if_gatt_is_reachable(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("if (!initiallyPaired)", source)
        self.assertIn('connectionStatus = "NotPaired"', source)
        self.assertIn("connectOnly && initiallyPaired && connectionStatus", source)

    def test_inspection_requires_one_live_candidate(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("liveCandidates.Count == 1", source)
        self.assertIn("Expected exactly one live and pairable physical Bluetooth LE endpoint", source)

    def test_pairing_manager_passes_the_expected_identity(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        self.assertIn("ExpectedDeviceIdSha256", source)
        self.assertIn("^[0-9A-Fa-f]{64}$", source)
        self.assertIn("$ExpectedDeviceIdSha256.ToUpperInvariant()", source)

    def test_direct_pairing_cannot_fall_back_to_name_only(self) -> None:
        source = DIRECT_PAIRING.read_text(encoding="utf-8")
        self.assertIn("ExpectedDeviceIdSha256", source)
        self.assertIn("System.Devices.Aep.DeviceAddress", source)
        self.assertIn("ComputeHash($identityBytes)", source)
        self.assertIn("$_.IdSha256 -ceq $result.expected_id_sha256", source)
        self.assertIn("ProtectionLevelUsed", source)
        self.assertIn("UnpairAsync", source)
        self.assertIn("Existing pairing cannot prove", source)
        self.assertIn("paired_aep_id_sha256 = $null", source)
        self.assertIn("[Text.Encoding]::UTF8.GetBytes($device.Id)", source)

    def test_direct_pairing_always_persists_a_fail_closed_diagnostic(self) -> None:
        source = DIRECT_PAIRING.read_text(encoding="utf-8")
        self.assertIn("error_type = 'RejectedProtectionLevel'", source)
        self.assertIn("pairing_rollback_status = 'OperationFailed'", source)
        self.assertIn("} finally {\n    if ($null -ne $device)", source)
        self.assertIn("Move-Item -LiteralPath $temporaryResult", source)
        self.assertLess(source.index("$result = [ordered]@{"), source.index("try {"))
        self.assertLess(
            source.index("Move-Item -LiteralPath $temporaryResult"),
            source.index("exit $exitCode"),
        )

    def test_diagnostic_fingerprint_never_outputs_the_raw_adapter_address(self) -> None:
        source = FINGERPRINT.read_text(encoding="utf-8")
        self.assertIn("BluetoothAddress.ToString('X12')", source)
        self.assertIn("SHA256", source)
        self.assertIn("[Array]::Clear", source)
        output = source[source.index("[ordered]@{"):]
        self.assertNotIn("$normalized", output)
        self.assertNotIn("BluetoothAddress", output)

    def test_unpair_is_address_and_name_scoped_and_supports_what_if(self) -> None:
        source = UNPAIR.read_text(encoding="utf-8")
        self.assertIn("SupportsShouldProcess", source)
        self.assertIn("FromBluetoothAddressAsync", source)
        self.assertIn("ExpectedName", source)
        self.assertIn("Bluetooth device name does not match ExpectedName", source)
        self.assertIn("UnpairAsync", source)
        self.assertNotIn("Remove-Item", source)


if __name__ == "__main__":
    unittest.main()
