using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using Windows.Devices.Enumeration;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Foundation;

internal static class PairingTool
{
    private const string Selector =
        "System.Devices.Aep.ProtocolId:=\"{BB7BB05E-5972-42B5-94FC-76EAA7084D49}\"";
    private static readonly Dictionary<string, object> Diagnostics =
        new Dictionary<string, object>();
    private static readonly string[] RequestedProperties =
    {
        "System.Devices.Aep.IsPresent",
        "System.Devices.Aep.IsConnected",
        "System.Devices.Aep.Bluetooth.Le.IsConnectable",
        "System.Devices.Aep.SignalStrength",
        "System.Devices.Aep.Bluetooth.LastSeenTime"
    };

    private static int Main(string[] args)
    {
        var inspectOnly = args.Length == 3 && args[0] == "--inspect-name";
        var connectOnly = args.Length == 4 && args[0] == "--connect-name";
        var pair = args.Length == 4 && args[0] == "--name";
        if (!inspectOnly && !connectOnly && !pair)
        {
            Console.Error.WriteLine(
                "Usage: PairingTool --inspect-name <exact-name> <result-json>");
            Console.Error.WriteLine(
                "       PairingTool (--name|--connect-name) <exact-name> <expected-id-sha256> <result-json>");
            return 2;
        }
        var exactName = args[1];
        string expectedIdSha256 = null;
        var resultPath = inspectOnly ? args[2] : args[3];
        if (exactName.Length == 0 || resultPath.Length == 0)
            return 2;
        try
        {
            expectedIdSha256 = inspectOnly ? null : NormalizeSha256(args[2]);
            return Run(exactName, expectedIdSha256, resultPath, inspectOnly, connectOnly);
        }
        catch (Exception ex)
        {
            var failure = new Dictionary<string, object>(Diagnostics)
            {
                { "device_name", exactName },
                { "expected_id_sha256", expectedIdSha256 },
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

    private static int Run(string exactName, string expectedIdSha256, string resultPath,
        bool inspectOnly, bool connectOnly)
    {
        var device = DiscoverLiveEndpoint(
            exactName, expectedIdSha256, TimeSpan.FromSeconds(35));
        var initiallyPaired = device.Pairing.IsPaired;
        var ceremonies = new List<string>();
        var status = initiallyPaired ? "AlreadyPaired" : "NotStarted";
        var protection = "None";
        var pairingRollbackStatus = "NotRequired";
        if (!initiallyPaired && !inspectOnly && !connectOnly)
        {
            var custom = device.Pairing.Custom;
            TypedEventHandler<DeviceInformationCustomPairing, DevicePairingRequestedEventArgs> handler =
                (sender, eventArgs) =>
            {
                ceremonies.Add(eventArgs.PairingKind.ToString());
                if (eventArgs.PairingKind != DevicePairingKinds.ConfirmOnly)
                    return;
                Console.WriteLine("Windows requested ConfirmOnly; accepting the authorized HOGP pairing.");
                eventArgs.Accept();
            };
            custom.PairingRequested += handler;
            try
            {
                var result = custom.PairAsync(
                    DevicePairingKinds.ConfirmOnly,
                    DevicePairingProtectionLevel.Encryption).AsTask().GetAwaiter().GetResult();
                status = result.Status.ToString();
                protection = result.ProtectionLevelUsed.ToString();
            }
            finally
            {
                custom.PairingRequested -= handler;
            }
        }

        var newlyPaired = status == DevicePairingResultStatus.Paired.ToString();
        var encryptionVerified = newlyPaired &&
            protection == DevicePairingProtectionLevel.Encryption.ToString();
        if (!inspectOnly && !connectOnly && initiallyPaired)
            status = "ExistingPairingRequiresExplicitUnpair";
        if (!inspectOnly && !connectOnly && newlyPaired && !encryptionVerified)
        {
            var rollback = device.Pairing.UnpairAsync().AsTask().GetAwaiter().GetResult();
            pairingRollbackStatus = rollback.Status.ToString();
            status = "RejectedProtectionLevel";
        }
        var paired = device.Pairing.IsPaired && pairingRollbackStatus == "NotRequired";
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
                using (var bluetoothDevice = BluetoothLEDevice.FromIdAsync(device.Id)
                    .AsTask().GetAwaiter().GetResult())
                {
                    if (bluetoothDevice == null)
                        throw new InvalidOperationException("BluetoothLEDevice.FromIdAsync returned null");
                    var services = bluetoothDevice.GetGattServicesForUuidAsync(
                        GattServiceUuids.HumanInterfaceDevice, BluetoothCacheMode.Uncached)
                        .AsTask().GetAwaiter().GetResult();
                    connectionStatus = services.Status.ToString();
                    hidServiceCount = services.Services.Count;
                    foreach (var service in services.Services) service.Dispose();
                }
            }
        }
        var resultFields = new Dictionary<string, object>(Diagnostics)
        {
            { "device_name", exactName },
            { "expected_id_sha256", expectedIdSha256 },
            { "initial_paired", initiallyPaired },
            { "pairing_status", status },
            { "protection_level_used", protection },
            { "encryption_verified", encryptionVerified },
            { "pairing_rollback_status", pairingRollbackStatus },
            { "ceremonies", ceremonies },
            { "paired", paired },
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

    private static DeviceInformation DiscoverLiveEndpoint(
        string exactName, string expectedIdSha256, TimeSpan timeout)
    {
        var gate = new ManualResetEventSlim(false);
        var sync = new object();
        var devices = new Dictionary<string, DeviceInformation>(StringComparer.Ordinal);
        var candidates = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
        var liveCandidates = new Dictionary<string, DeviceInformation>(StringComparer.Ordinal);
        DeviceInformation selected = null;
        var added = 0;
        var updated = 0;
        var enumerationCompleted = false;

        Action<DeviceInformation> evaluate = candidate =>
        {
            if (!string.Equals(candidate.Name, exactName, StringComparison.Ordinal))
                return;
            var state = Snapshot(candidate);
            var identity = (string)state["id_sha256"];
            candidates[identity] = state;
            var present = GetBoolean(candidate, "System.Devices.Aep.IsPresent");
            var connectable = GetBoolean(candidate, "System.Devices.Aep.Bluetooth.Le.IsConnectable");
            if (present && connectable &&
                (candidate.Pairing.CanPair || candidate.Pairing.IsPaired))
            {
                liveCandidates[identity] = candidate;
                if (expectedIdSha256 != null && identity == expectedIdSha256)
                {
                    selected = candidate;
                    gate.Set();
                }
            }
            else
                liveCandidates.Remove(identity);
        };

        var watcher = DeviceInformation.CreateWatcher(
            Selector, RequestedProperties, DeviceInformationKind.AssociationEndpoint);
        TypedEventHandler<DeviceWatcher, DeviceInformation> addedHandler = (sender, candidate) =>
        {
            lock (sync)
            {
                added++;
                devices[candidate.Id] = candidate;
                evaluate(candidate);
            }
        };
        TypedEventHandler<DeviceWatcher, DeviceInformationUpdate> updatedHandler = (sender, change) =>
        {
            lock (sync)
            {
                updated++;
                DeviceInformation candidate;
                if (devices.TryGetValue(change.Id, out candidate))
                {
                    candidate.Update(change);
                    evaluate(candidate);
                }
            }
        };
        TypedEventHandler<DeviceWatcher, object> completedHandler = (sender, ignored) =>
        {
            lock (sync)
            {
                enumerationCompleted = true;
                if (expectedIdSha256 == null)
                {
                    if (liveCandidates.Count == 1)
                        selected = liveCandidates.Values.Single();
                    gate.Set();
                }
            }
        };
        watcher.Added += addedHandler;
        watcher.Updated += updatedHandler;
        watcher.EnumerationCompleted += completedHandler;
        try
        {
            watcher.Start();
            gate.Wait(timeout);
        }
        finally
        {
            if (watcher.Status == DeviceWatcherStatus.Started ||
                watcher.Status == DeviceWatcherStatus.EnumerationCompleted)
                watcher.Stop();
            watcher.Added -= addedHandler;
            watcher.Updated -= updatedHandler;
            watcher.EnumerationCompleted -= completedHandler;
            gate.Dispose();
        }

        lock (sync)
        {
            Diagnostics["watcher_added"] = added;
            Diagnostics["watcher_updated"] = updated;
            Diagnostics["watcher_enumeration_completed"] = enumerationCompleted;
            Diagnostics["matching_candidates"] = candidates.Values.ToArray();
            Diagnostics["live_matching_candidates"] = liveCandidates.Count;
            Diagnostics["expected_id_sha256"] = expectedIdSha256;
            if (selected != null)
            {
                var state = Snapshot(selected);
                Diagnostics["selected_id_sha256"] = state["id_sha256"];
                Diagnostics["selected_is_present"] = state["is_present"];
                Diagnostics["selected_is_connectable"] = state["is_connectable"];
                Diagnostics["selected_is_connected"] = state["is_connected"];
                Diagnostics["selected_can_pair"] = state["can_pair"];
            }
        }
        if (selected == null)
            throw new InvalidOperationException(
                expectedIdSha256 == null
                    ? "Expected exactly one live, connectable and pairable Bluetooth LE endpoint during inspection"
                    : "No live Bluetooth LE endpoint matched the exact name and expected identity");
        return selected;
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
        return new Dictionary<string, object>
        {
            { "id_sha256", Hash(candidate.Id) },
            { "is_present", GetBoolean(candidate, "System.Devices.Aep.IsPresent") },
            { "is_connectable", GetBoolean(candidate, "System.Devices.Aep.Bluetooth.Le.IsConnectable") },
            { "is_connected", GetBoolean(candidate, "System.Devices.Aep.IsConnected") },
            { "can_pair", candidate.Pairing.CanPair },
            { "is_paired", candidate.Pairing.IsPaired }
        };
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
