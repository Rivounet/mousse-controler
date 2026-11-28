from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "src" / "pairing-tool" / "PairingTool.cs"
MANAGER = ROOT / "scripts" / "target" / "Manage-InteractivePairing.ps1"
FINGERPRINT = (
    ROOT / "scripts" / "qualification" / "Get-BluetoothAddressFingerprint.ps1"
)
UNPAIR = (
    ROOT / "scripts" / "qualification" / "Unpair-BluetoothDeviceByAddress.ps1"
)


class PairingIdentityContractTests(unittest.TestCase):
    def test_pair_and_connect_use_distinct_identity_contracts(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn('args[0] == "--pair-name"', source)
        self.assertIn('args[0] == "--connect-name"', source)
        self.assertIn("NormalizeSha256(args[2])", source)
        self.assertIn("expectedPairedAepIdSha256", source)
        self.assertIn('"expected_paired_aep_id_sha256"', source)
        self.assertNotIn('args[0] == "--name"', source)

    def test_pair_resolves_the_unique_live_advertisement_in_one_process(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("DiscoverAdvertisingEndpoint(exactName", source)
        self.assertIn("eventArgs.BluetoothAddressType", source)
        self.assertIn("advertisement.Address, advertisement.AddressType", source)
        self.assertIn("BluetoothAddressType.Unspecified", source)
        self.assertIn("DeviceInformation.CreateFromIdAsync(", source)
        self.assertIn("bluetoothDevice.DeviceId", source)
        self.assertNotIn("DiscoverLiveEndpoint(", source)

    def test_inspection_correlates_name_connectable_advertisement_and_hid_service(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("BluetoothLEAdvertisementWatcher", source)
        self.assertIn("BluetoothLEScanningMode.Active", source)
        self.assertIn("BluetoothLEAdvertisementType.ConnectableUndirected", source)
        self.assertIn("GattServiceUuids.HumanInterfaceDevice", source)
        self.assertIn("ExactNameSeen && item.Value.ConnectableSeen", source)
        self.assertIn("item.Value.HidServiceSeen", source)
        self.assertIn("candidates.Length != 1", source)
        self.assertIn('Diagnostics["advertisement_id_sha256"]', source)

    def test_new_pairing_uses_standard_encrypted_pairing_and_rolls_back_otherwise(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn(
            "device.Pairing.PairAsync(DevicePairingProtectionLevel.Encryption)",
            source,
        )
        self.assertIn("result.ProtectionLevelUsed.ToString()", source)
        self.assertIn("DevicePairingProtectionLevel.Encryption.ToString()", source)
        self.assertIn("device.Pairing.UnpairAsync()", source)
        self.assertIn("device.Pairing.IsPaired && !encryptionVerified", source)
        self.assertIn('pairingRollbackStatus = "OperationFailed"', source)
        self.assertIn('errorType = "RollbackIncomplete"', source)
        self.assertIn("ExistingPairingRequiresExplicitUnpair", source)
        self.assertIn("RejectedProtectionLevel", source)
        self.assertNotIn("device.Pairing.Custom", source)
        self.assertNotIn("PairingRequested", source)

    def test_success_publishes_only_the_durable_paired_aep_hash(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("var pairedAepIdSha256 = paired &&", source)
        self.assertIn("? Hash(device.Id)", source)
        self.assertIn('{ "paired_aep_id_sha256", pairedAepIdSha256 }', source)
        self.assertNotIn('"paired_aep_id", device.Id', source)

    def test_connect_selects_the_exact_durable_paired_endpoint(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("DiscoverPairedEndpoint(exactName, expectedPairedAepIdSha256)", source)
        self.assertIn("candidate.Pairing.IsPaired", source)
        self.assertIn("Hash(candidate.Id), expectedPairedAepIdSha256", source)
        self.assertIn("matches.Length != 1", source)

    def test_connect_refuses_an_unpaired_endpoint_even_if_gatt_is_reachable(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("if (!initiallyPaired)", source)
        self.assertIn('connectionStatus = "NotPaired"', source)
        self.assertIn("connectOnly && initiallyPaired && connectionStatus", source)

    def test_pairing_manager_requires_a_durable_identity_only_for_connect(self) -> None:
        source = MANAGER.read_text(encoding="utf-8")
        self.assertIn("ExpectedPairedAepIdSha256", source)
        self.assertIn("^[0-9A-Fa-f]{64}$", source)
        self.assertIn("if ($Mode -eq 'Connect'", source)
        self.assertIn("$ExpectedPairedAepIdSha256.ToUpperInvariant()", source)
        self.assertIn("'--pair-name'", source)
        self.assertFalse((ROOT / "scripts" / "target" / "Pair-BluetoothDevice.ps1").exists())

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
