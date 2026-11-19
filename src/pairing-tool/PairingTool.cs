using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Text;
using System.Web.Script.Serialization;
using Windows.Devices.Enumeration;
using Windows.Foundation;

internal static class PairingTool
{
    private const string Selector =
        "System.Devices.Aep.ProtocolId:=\"{BB7BB05E-5972-42B5-94FC-76EAA7084D49}\"";

    private static int Main(string[] args)
    {
        if (args.Length != 3 || args[0] != "--name" || args[2].Length == 0)
        {
            Console.Error.WriteLine("Usage: PairingTool --name <exact-name> <result-json>");
            return 2;
        }
        try
        {
            return Run(args[1], args[2]);
        }
        catch (Exception ex)
        {
            WriteResult(args[2], new Dictionary<string, object>
            {
                { "device_name", args[1] },
                { "paired", false },
                { "error_type", ex.GetType().Name },
                { "error_hresult", string.Format("0x{0:X8}", ex.HResult) },
                { "session_id", Process.GetCurrentProcess().SessionId }
            });
            Console.Error.WriteLine(ex.GetType().Name + ": " + ex.Message);
            return 1;
        }
    }

    private static int Run(string exactName, string resultPath)
    {
        var properties = new[] { "System.Devices.Aep.IsPaired" };
        var devices = DeviceInformation.FindAllAsync(
            Selector, properties, DeviceInformationKind.AssociationEndpoint).AsTask().GetAwaiter().GetResult();
        var matches = devices.Where(candidate => string.Equals(candidate.Name, exactName, StringComparison.Ordinal)).ToList();
        if (matches.Count != 1)
            throw new InvalidOperationException("Expected exactly one Bluetooth endpoint with the requested name");

        var device = matches[0];
        var initiallyPaired = device.Pairing.IsPaired;
        var ceremonies = new List<string>();
        var status = initiallyPaired ? "AlreadyPaired" : "NotStarted";
        var protection = "None";
        if (!initiallyPaired)
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

        var paired = initiallyPaired || status == DevicePairingResultStatus.Paired.ToString() ||
            status == DevicePairingResultStatus.AlreadyPaired.ToString();
        WriteResult(resultPath, new Dictionary<string, object>
        {
            { "device_name", exactName },
            { "initial_paired", initiallyPaired },
            { "pairing_status", status },
            { "protection_level_used", protection },
            { "ceremonies", ceremonies },
            { "paired", paired },
            { "session_id", Process.GetCurrentProcess().SessionId }
        });
        Console.WriteLine("Pairing status: " + status);
        return paired ? 0 : 1;
    }

    private static void WriteResult(string path, IDictionary<string, object> result)
    {
        var serializer = new JavaScriptSerializer();
        File.WriteAllText(path, serializer.Serialize(result), new UTF8Encoding(false));
    }
}
