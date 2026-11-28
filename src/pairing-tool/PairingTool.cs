using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using Windows.Devices.Enumeration;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.Advertisement;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Foundation;

internal static class PairingTool
{
    private sealed class AdvertisementObservation
    {
        internal bool ExactNameSeen;
        internal bool ConnectableSeen;
        internal bool HidServiceSeen;
        internal BluetoothAddressType AddressType;
        internal int Frames;
    }

    private sealed class AdvertisementSelection
    {
        internal ulong Address;
        internal BluetoothAddressType AddressType;
    }

    private const string Selector =
        "System.Devices.Aep.ProtocolId:=\"{BB7BB05E-5972-42B5-94FC-76EAA7084D49}\"";
    private static readonly Dictionary<string, object> Diagnostics =
        new Dictionary<string, object>();
    private static readonly string[] RequestedProperties =
    {
        "System.Devices.Aep.IsPresent",
        "System.Devices.Aep.IsConnected",
        "System.Devices.Aep.DeviceAddress",
        "System.Devices.Aep.Bluetooth.Le.IsConnectable",
        "System.Devices.Aep.SignalStrength",
        "System.Devices.Aep.Bluetooth.LastSeenTime"
    };

    private static int Main(string[] args)
    {
        var inspectOnly = args.Length == 3 && args[0] == "--inspect-name";
        var connectOnly = args.Length == 4 && args[0] == "--connect-name";
        var pair = args.Length == 3 && args[0] == "--pair-name";
        if (!inspectOnly && !connectOnly && !pair)
        {
            Console.Error.WriteLine(
                "Usage: PairingTool --inspect-name <exact-name> <result-json>");
            Console.Error.WriteLine(
                "       PairingTool --pair-name <exact-name> <result-json>");
            Console.Error.WriteLine(
                "       PairingTool --connect-name <exact-name> <paired-aep-id-sha256> <result-json>");
            return 2;
        }
        var exactName = args[1];
        string expectedPairedAepIdSha256 = null;
        var resultPath = connectOnly ? args[3] : args[2];
        if (exactName.Length == 0 || resultPath.Length == 0)
            return 2;
        try
        {
            expectedPairedAepIdSha256 = connectOnly ? NormalizeSha256(args[2]) : null;
            return Run(exactName, expectedPairedAepIdSha256, resultPath, inspectOnly, connectOnly);
        }
        catch (Exception ex)
        {
            var failure = new Dictionary<string, object>(Diagnostics)
            {
                { "device_name", exactName },
                { "expected_paired_aep_id_sha256", expectedPairedAepIdSha256 },
                { "paired_aep_id_sha256", null },
                { "paired", false },
                { "error_type", ex.GetType().Name },
                { "error_hresult", string.Format("0x{0:X8}", ex.HResult) },
                { "session_id", Process.GetCurrentProcess().SessionId }
            };
            WriteResult(resultPath, failure);
            Console.Error.WriteLine(ex.GetType().Name + ": " + ex.Message);
            return 1;
        }
    }

    private static int Run(string exactName, string expectedPairedAepIdSha256, string resultPath,
        bool inspectOnly, bool connectOnly)
    {
        var device = connectOnly
            ? DiscoverPairedEndpoint(exactName, expectedPairedAepIdSha256)
            : ResolveAdvertisingEndpoint(
                exactName, DiscoverAdvertisingEndpoint(exactName, TimeSpan.FromSeconds(20)));
        var initiallyPaired = device.Pairing.IsPaired;
        var status = initiallyPaired ? "AlreadyPaired" : "NotStarted";
        var protection = "None";
        var pairingRollbackStatus = "NotRequired";
        string errorType = null;
        string errorHresult = null;
        if (!initiallyPaired && !inspectOnly && !connectOnly)
        {
            try
            {
                var result = device.Pairing.PairAsync(DevicePairingProtectionLevel.Encryption)
                    .AsTask().GetAwaiter().GetResult();
                status = result.Status.ToString();
                protection = result.ProtectionLevelUsed.ToString();
            }
            catch (Exception ex)
            {
                status = "OperationFailed";
                protection = "Unverified";
                errorType = ex.GetType().Name;
                errorHresult = string.Format("0x{0:X8}", ex.HResult);
            }
        }

        var newlyPaired = status == DevicePairingResultStatus.Paired.ToString();
        var encryptionVerified = newlyPaired &&
            protection == DevicePairingProtectionLevel.Encryption.ToString();
        if (!inspectOnly && !connectOnly && initiallyPaired)
            status = "ExistingPairingRequiresExplicitUnpair";
        if (!inspectOnly && !connectOnly && !initiallyPaired &&
            device.Pairing.IsPaired && !encryptionVerified)
        {
            if (errorType == null) errorType = "RejectedProtectionLevel";
            try
            {
                var rollback = device.Pairing.UnpairAsync().AsTask().GetAwaiter().GetResult();
                pairingRollbackStatus = rollback.Status.ToString();
                status = "RejectedProtectionLevel";
            }
            catch (Exception ex)
            {
                pairingRollbackStatus = "OperationFailed";
                status = "RollbackFailed";
                errorType = ex.GetType().Name;
                errorHresult = string.Format("0x{0:X8}", ex.HResult);
            }
        }
        var paired = device.Pairing.IsPaired;
        if (!inspectOnly && !connectOnly && !initiallyPaired && paired &&
            !encryptionVerified && errorType == null)
            errorType = "RollbackIncomplete";
        var pairedAepIdSha256 = paired && (connectOnly || encryptionVerified)
            ? Hash(device.Id)
            : null;
        var connectionStatus = "NotRequested";
        var hidServiceCount = 0;
        if (connectOnly)
        {
            if (!initiallyPaired)
            {
                connectionStatus = "NotPaired";
            }
            else
            {
                try
                {
                    using (var bluetoothDevice = BluetoothLEDevice.FromIdAsync(device.Id)
                        .AsTask().GetAwaiter().GetResult())
                    {
                        if (bluetoothDevice == null)
                            throw new InvalidOperationException(
                                "BluetoothLEDevice.FromIdAsync returned null");
                        var services = bluetoothDevice.GetGattServicesForUuidAsync(
                            GattServiceUuids.HumanInterfaceDevice, BluetoothCacheMode.Uncached)
                            .AsTask().GetAwaiter().GetResult();
                        connectionStatus = services.Status.ToString();
                        hidServiceCount = services.Services.Count;
                        foreach (var service in services.Services) service.Dispose();
                    }
                }
                catch (Exception ex)
                {
                    connectionStatus = "OperationFailed";
                    errorType = ex.GetType().Name;
                    errorHresult = string.Format("0x{0:X8}", ex.HResult);
                }
            }
        }
        var resultFields = new Dictionary<string, object>(Diagnostics)
        {
            { "device_name", exactName },
            { "expected_paired_aep_id_sha256", expectedPairedAepIdSha256 },
            { "paired_aep_id_sha256", pairedAepIdSha256 },
            { "initial_paired", initiallyPaired },
            { "pairing_status", status },
            { "protection_level_used", protection },
            { "encryption_verified", encryptionVerified },
            { "pairing_rollback_status", pairingRollbackStatus },
            { "paired", paired },
            { "error_type", errorType },
            { "error_hresult", errorHresult },
            { "session_id", Process.GetCurrentProcess().SessionId }
        };
        resultFields["inspect_only"] = inspectOnly;
        resultFields["connect_only"] = connectOnly;
        resultFields["gatt_status"] = connectionStatus;
        resultFields["hid_service_count"] = hidServiceCount;
        WriteResult(resultPath, resultFields);
        Console.WriteLine((inspectOnly ? "Inspection" : "Pairing") + " status: " + status);
        return inspectOnly || (connectOnly && initiallyPaired && connectionStatus == "Success") ||
            (paired && encryptionVerified) ? 0 : 1;
    }

    private static AdvertisementSelection DiscoverAdvertisingEndpoint(
        string exactName, TimeSpan timeout)
    {
        var sync = new object();
        var observations = new Dictionary<ulong, AdvertisementObservation>();
        var watcher = new BluetoothLEAdvertisementWatcher
        {
            ScanningMode = BluetoothLEScanningMode.Active
        };
        TypedEventHandler<BluetoothLEAdvertisementWatcher,
            BluetoothLEAdvertisementReceivedEventArgs> handler = (sender, eventArgs) =>
        {
            lock (sync)
            {
                AdvertisementObservation observation;
                if (!observations.TryGetValue(eventArgs.BluetoothAddress, out observation))
                {
                    observation = new AdvertisementObservation();
                    observations[eventArgs.BluetoothAddress] = observation;
                }
                observation.AddressType = eventArgs.BluetoothAddressType;
                observation.Frames++;
                if (string.Equals(eventArgs.Advertisement.LocalName, exactName,
                    StringComparison.Ordinal))
                    observation.ExactNameSeen = true;
                if (eventArgs.AdvertisementType ==
                    BluetoothLEAdvertisementType.ConnectableUndirected)
                    observation.ConnectableSeen = true;
                if (eventArgs.Advertisement.ServiceUuids.Any(uuid =>
                    uuid == GattServiceUuids.HumanInterfaceDevice))
                    observation.HidServiceSeen = true;
            }
        };
        watcher.Received += handler;
        try
        {
            watcher.Start();
            Thread.Sleep(timeout);
        }
        finally
        {
            watcher.Stop();
            watcher.Received -= handler;
        }

        lock (sync)
        {
            var candidates = observations.Where(item =>
                item.Value.ExactNameSeen && item.Value.ConnectableSeen &&
                item.Value.HidServiceSeen).ToArray();
            Diagnostics["advertisement_address_count"] = observations.Count;
            Diagnostics["advertisement_candidate_count"] = candidates.Length;
            Diagnostics["advertisement_candidates"] = candidates.Select(item =>
                new Dictionary<string, object>
                {
                    { "id_sha256", HashAddress(item.Key) },
                    { "identity_kind", "bluetooth_address_sha256" },
                    { "address_type", item.Value.AddressType.ToString() },
                    { "frames", item.Value.Frames }
                }).ToArray();
            if (candidates.Length != 1)
                throw new InvalidOperationException(
                    "Expected exactly one live connectable HID advertisement with the exact name");
            if (candidates[0].Value.AddressType == BluetoothAddressType.Unspecified)
                throw new InvalidOperationException(
                    "The live Bluetooth advertisement did not expose a usable address type");
            Diagnostics["advertisement_id_sha256"] = HashAddress(candidates[0].Key);
            Diagnostics["advertisement_address_type"] =
                candidates[0].Value.AddressType.ToString();
            return new AdvertisementSelection
            {
                Address = candidates[0].Key,
                AddressType = candidates[0].Value.AddressType
            };
        }
    }

    private static DeviceInformation ResolveAdvertisingEndpoint(
        string exactName, AdvertisementSelection advertisement)
    {
        using (var bluetoothDevice = BluetoothLEDevice.FromBluetoothAddressAsync(
            advertisement.Address, advertisement.AddressType).AsTask().GetAwaiter().GetResult())
        {
            if (bluetoothDevice == null)
                throw new InvalidOperationException(
                    "The live Bluetooth advertisement could not be resolved to a Windows endpoint");
            var candidate = DeviceInformation.CreateFromIdAsync(
                bluetoothDevice.DeviceId, RequestedProperties,
                DeviceInformationKind.AssociationEndpoint).AsTask().GetAwaiter().GetResult();
            if (candidate == null)
                throw new InvalidOperationException(
                    "The live Bluetooth advertisement resolved to no Windows device information");
            if (!string.Equals(candidate.Name, exactName, StringComparison.Ordinal))
                throw new InvalidOperationException(
                    "The resolved Bluetooth endpoint did not retain the exact advertised name");
            if (!GetBoolean(candidate, "System.Devices.Aep.IsPresent") ||
                (!candidate.Pairing.CanPair && !candidate.Pairing.IsPaired))
                throw new InvalidOperationException(
                    "The resolved Bluetooth endpoint is not present or pairable");
            PublishSelectedEndpointDiagnostics(candidate);
            return candidate;
        }
    }

    private static DeviceInformation DiscoverPairedEndpoint(
        string exactName, string expectedPairedAepIdSha256)
    {
        var devices = DeviceInformation.FindAllAsync(
            Selector, RequestedProperties, DeviceInformationKind.AssociationEndpoint)
            .AsTask().GetAwaiter().GetResult();
        var matches = devices.Where(candidate =>
            string.Equals(candidate.Name, exactName, StringComparison.Ordinal) &&
            candidate.Pairing.IsPaired &&
            string.Equals(Hash(candidate.Id), expectedPairedAepIdSha256,
                StringComparison.Ordinal)).ToArray();
        Diagnostics["paired_endpoint_match_count"] = matches.Length;
        if (matches.Length != 1)
            throw new InvalidOperationException(
                "Expected exactly one paired endpoint with the authorized durable AEP identity");
        PublishSelectedEndpointDiagnostics(matches[0]);
        return matches[0];
    }

    private static void PublishSelectedEndpointDiagnostics(DeviceInformation candidate)
    {
        var state = Snapshot(candidate);
        Diagnostics["selected_aep_id_sha256"] = Hash(candidate.Id);
        Diagnostics["selected_address_sha256"] = state["address_sha256"];
        Diagnostics["selected_is_present"] = state["is_present"];
        Diagnostics["selected_is_connectable"] = state["is_connectable"];
        Diagnostics["selected_is_connected"] = state["is_connected"];
        Diagnostics["selected_can_pair"] = state["can_pair"];
    }

    private static string NormalizeSha256(string value)
    {
        var normalized = (value ?? "").Trim().ToUpperInvariant();
        if (normalized.Length != 64 || normalized.Any(character =>
            !((character >= '0' && character <= '9') ||
              (character >= 'A' && character <= 'F'))))
            throw new ArgumentException("expected device identity must contain 64 hex characters");
        return normalized;
    }

    private static Dictionary<string, object> Snapshot(DeviceInformation candidate)
    {
        var addressSha256 = HashDeviceAddress(candidate);
        return new Dictionary<string, object>
        {
            { "address_sha256", addressSha256 },
            { "is_present", GetBoolean(candidate, "System.Devices.Aep.IsPresent") },
            { "is_connectable", GetBoolean(candidate, "System.Devices.Aep.Bluetooth.Le.IsConnectable") },
            { "is_connected", GetBoolean(candidate, "System.Devices.Aep.IsConnected") },
            { "can_pair", candidate.Pairing.CanPair },
            { "is_paired", candidate.Pairing.IsPaired }
        };
    }

    private static string HashDeviceAddress(DeviceInformation candidate)
    {
        object value;
        if (!candidate.Properties.TryGetValue("System.Devices.Aep.DeviceAddress", out value))
            return null;
        var normalized = (value as string ?? "").Replace(":", "").Replace("-", "")
            .Trim().ToUpperInvariant();
        if (normalized.Length != 12 || normalized.Any(character =>
            !((character >= '0' && character <= '9') ||
              (character >= 'A' && character <= 'F'))))
            return null;
        return Hash(normalized);
    }

    private static string HashAddress(ulong address)
    {
        return Hash(address.ToString("X12", CultureInfo.InvariantCulture));
    }

    private static bool GetBoolean(DeviceInformation candidate, string name)
    {
        object value;
        return candidate.Properties.TryGetValue(name, out value) && value is bool && (bool)value;
    }

    private static string Hash(string value)
    {
        using (var sha256 = SHA256.Create())
            return string.Concat(sha256.ComputeHash(Encoding.UTF8.GetBytes(value))
                .Select(part => part.ToString("X2")));
    }

    private static void WriteResult(string path, IDictionary<string, object> result)
    {
        var serializer = new JavaScriptSerializer();
        File.WriteAllText(path, serializer.Serialize(result), new UTF8Encoding(false));
    }
}
