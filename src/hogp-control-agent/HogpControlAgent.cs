using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Management;
using System.Net;
using System.Net.Security;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Windows.Devices.Bluetooth;
using Windows.Devices.Enumeration;
using Windows.Devices.Radios;

namespace MousseControler.HogpControlAgent
{
    internal sealed class AgentConfig
    {
        public string Endpoint { get; set; }
        public string KeyId { get; set; }
        public string SecretDpapi { get; set; }
        public string CertificateSha256 { get; set; }
        public int IntervalMilliseconds { get; set; }
        public int RequestTimeoutMilliseconds { get; set; }
        public string HogpDeviceName { get; set; }
        public string TargetAepSha256 { get; set; }
        public string AdapterInstanceSha256 { get; set; }
        public string PairedPnpInstanceSha256 { get; set; }
        public string HidPnpInstanceSha256 { get; set; }
        public bool AllowAdapterRestart { get; set; }
        public bool AllowEndpointRestart { get; set; }
        public string StatePath { get; set; }
    }

    internal sealed class Acknowledgment
    {
        public string command_id { get; set; }
        public string state { get; set; }
    }

    internal sealed class AgentState
    {
        public long sequence { get; set; }
        public string provider_generation { get; set; }
        public Acknowledgment pending_acknowledgment { get; set; }
        public string[] processed_commands { get; set; }
    }

    internal sealed class IdentityCandidate
    {
        public string kind { get; set; }
        public string name { get; set; }
        public string pnp_class { get; set; }
        public string instance_sha256 { get; set; }
        public string status { get; set; }
        public int problem_code { get; set; }
    }

    internal sealed class AepCandidate
    {
        public string name { get; set; }
        public bool paired { get; set; }
        public string aep_sha256 { get; set; }
    }

    internal sealed class IdentityInspection
    {
        public string schema { get; set; }
        public string hogp_device_name { get; set; }
        public string radio_state { get; set; }
        public AepCandidate[] aep_candidates { get; set; }
        public IdentityCandidate[] pnp_candidates { get; set; }
    }

    internal sealed class ControlReport
    {
        public string schema { get; set; }
        public string provider_generation { get; set; }
        public string target_aep_sha256 { get; set; }
        public string adapter_instance_sha256 { get; set; }
        public string paired_pnp_instance_sha256 { get; set; }
        public string hid_pnp_instance_sha256 { get; set; }
        public bool radio_present { get; set; }
        public string radio_state { get; set; }
        public int adapter_problem_code { get; set; }
        public bool paired { get; set; }
        public bool hid_present { get; set; }
        public bool elevated { get; set; }
        public Acknowledgment acknowledgment { get; set; }
    }

    internal sealed class TransportState
    {
        public bool available { get; set; }
        public bool authorized_subscriber { get; set; }
        public string subscriber_count { get; set; }
        public string advertising { get; set; }
    }

    internal sealed class ControlCommand
    {
        public string command_id { get; set; }
        public string action { get; set; }
        public string provider_generation { get; set; }
        public long expires_at_unix_ms { get; set; }
    }

    internal sealed class ControlResponse
    {
        public long accepted_seq { get; set; }
        public string schema { get; set; }
        public string provider_generation { get; set; }
        public TransportState transport { get; set; }
        public ControlCommand command { get; set; }
        public Acknowledgment last_acknowledgment { get; set; }
    }

    internal sealed class PnpNode
    {
        internal string InstanceId;
        internal string InstanceSha256;
        internal string Name;
        internal string PnpClass;
        internal int ProblemCode;
        internal string Status;

        internal bool Healthy
        {
            get { return ProblemCode == 0 && string.Equals(Status, "OK", StringComparison.OrdinalIgnoreCase); }
        }
    }

    internal sealed class Observation
    {
        internal PnpNode Adapter;
        internal PnpNode PairedEndpoint;
        internal PnpNode Hid;
        internal bool RadioPresent;
        internal string RadioState;
        internal bool Paired;
    }

    internal sealed class Agent : IDisposable
    {
        private const string AdapterRole = "bluetooth_adapter";
        private const string PairedEndpointRole = "paired_ble_endpoint";
        private const string HidChildRole = "hogp_hid_child";
        private static readonly TimeSpan DefaultEnumerationTimeout = TimeSpan.FromSeconds(10);
        private static readonly TimeSpan PairedAepEnumerationTimeout = TimeSpan.FromSeconds(30);
        private readonly AgentConfig config;
        private readonly byte[] secret;
        private readonly string certificatePin;
        private readonly string statePath;
        private readonly Mutex instanceMutex;
        private readonly JavaScriptSerializer serializer = new JavaScriptSerializer();
        private readonly HashSet<string> processedCommands = new HashSet<string>(StringComparer.Ordinal);
        private readonly Queue<string> processedOrder = new Queue<string>();
        private long sequence;
        private string providerGeneration;
        private Acknowledgment pendingAcknowledgment;

        internal Agent(AgentConfig selected)
        {
            config = selected;
            secret = ProtectedData.Unprotect(Convert.FromBase64String(config.SecretDpapi), null,
                DataProtectionScope.CurrentUser);
            try
            {
                certificatePin = NormalizeHex(config.CertificateSha256);
                statePath = Path.GetFullPath(config.StatePath);
                instanceMutex = new Mutex(false,
                    "Local\\MousseControler.HogpControlAgent." + Hash(statePath));
                if (!instanceMutex.WaitOne(0))
                    throw new InvalidOperationException("another HOGP control agent owns this state");
                LoadState();
            }
            catch
            {
                if (instanceMutex != null) instanceMutex.Dispose();
                Array.Clear(secret, 0, secret.Length);
                throw;
            }
        }

        public void Dispose()
        {
            if (secret != null) Array.Clear(secret, 0, secret.Length);
            if (instanceMutex != null)
            {
                try { instanceMutex.ReleaseMutex(); } catch (ApplicationException) { }
                instanceMutex.Dispose();
            }
        }

        private void LoadState()
        {
            sequence = checked(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1000L);
            if (!File.Exists(statePath)) return;
            AgentState state = serializer.Deserialize<AgentState>(File.ReadAllText(statePath));
            if (state == null || state.sequence < 0)
                throw new InvalidDataException("HOGP control state is invalid");
            if (state.provider_generation != null && !IsCanonicalGuid(state.provider_generation))
                throw new InvalidDataException("persisted provider generation is invalid");
            if (state.pending_acknowledgment != null &&
                (!IsCanonicalGuid(state.pending_acknowledgment.command_id) ||
                 !IsAcknowledgmentState(state.pending_acknowledgment.state)))
                throw new InvalidDataException("persisted acknowledgment is invalid");
            string[] commands = state.processed_commands ?? new string[0];
            if (commands.Length > 256 || commands.Any(item => !IsCanonicalGuid(item)) ||
                commands.Distinct(StringComparer.Ordinal).Count() != commands.Length)
                throw new InvalidDataException("persisted command history is invalid");
            sequence = Math.Max(sequence, state.sequence);
            providerGeneration = state.provider_generation;
            pendingAcknowledgment = state.pending_acknowledgment;
            foreach (string command in commands)
            {
                processedCommands.Add(command);
                processedOrder.Enqueue(command);
            }
        }

        private void SaveState()
        {
            string parent = Path.GetDirectoryName(statePath);
            if (string.IsNullOrEmpty(parent))
                throw new InvalidDataException("state path has no parent directory");
            Directory.CreateDirectory(parent);
            AgentState state = new AgentState {
                sequence = sequence,
                provider_generation = providerGeneration,
                pending_acknowledgment = pendingAcknowledgment,
                processed_commands = processedOrder.ToArray(),
            };
            string temporary = statePath + ".new." + Guid.NewGuid().ToString("N");
            try
            {
                File.WriteAllText(temporary, serializer.Serialize(state), new UTF8Encoding(false));
                if (File.Exists(statePath)) File.Replace(temporary, statePath, null);
                else File.Move(temporary, statePath);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }

        private static bool IsAcknowledgmentState(string value)
        {
            return value == "executed" || value == "failed" ||
                value == "expired" || value == "not_required" ||
                value == "outcome_unknown";
        }

        internal void Run(CancellationToken token)
        {
            Console.WriteLine("Mousse HOGP Control Agent — outbound control plane only.");
            while (!token.IsCancellationRequested)
            {
                Stopwatch cycle = Stopwatch.StartNew();
                try
                {
                    Observation observation = Observe();
                    Acknowledgment sentAcknowledgment = pendingAcknowledgment;
                    ControlReport report = BuildReport(observation, sentAcknowledgment);
                    ControlResponse response = Post(report);
                    if (response == null || response.schema != "mousse-hogp-control-v1" ||
                        !IsCanonicalGuid(response.provider_generation))
                        throw new InvalidDataException("HOGP control response is invalid");
                    if (sentAcknowledgment != null && pendingAcknowledgment == sentAcknowledgment)
                        pendingAcknowledgment = null;
                    providerGeneration = response.provider_generation;
                    SaveState();
                    if (response.command != null)
                        HandleCommand(response.command, token);
                    Console.WriteLine("[{0:O}] radio={1}, adapter={2}, paired={3}, hid={4}, subscriber={5}",
                        DateTimeOffset.Now, observation.RadioState,
                        observation.Adapter == null ? "missing" : observation.Adapter.ProblemCode.ToString(CultureInfo.InvariantCulture),
                        observation.Paired, observation.Hid != null && observation.Hid.Healthy,
                        response.transport != null && response.transport.authorized_subscriber);
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine("[{0:O}] DEGRADED: {1}", DateTimeOffset.Now, ex.Message);
                }
                int remaining = config.IntervalMilliseconds - (int)cycle.ElapsedMilliseconds;
                if (remaining > 0) token.WaitHandle.WaitOne(remaining);
            }
        }

        private ControlReport BuildReport(Observation observation, Acknowledgment acknowledgment)
        {
            return new ControlReport {
                schema = "mousse-hogp-control-v1",
                provider_generation = providerGeneration,
                target_aep_sha256 = config.TargetAepSha256,
                adapter_instance_sha256 = config.AdapterInstanceSha256,
                paired_pnp_instance_sha256 = config.PairedPnpInstanceSha256,
                hid_pnp_instance_sha256 = config.HidPnpInstanceSha256,
                radio_present = observation.RadioPresent,
                radio_state = observation.RadioState,
                adapter_problem_code = observation.Adapter == null ? 255 : observation.Adapter.ProblemCode,
                paired = observation.Paired,
                hid_present = observation.Hid != null && observation.Hid.Healthy,
                elevated = IsElevated(),
                acknowledgment = acknowledgment,
            };
        }

        private Observation Observe()
        {
            List<PnpNode> nodes = ReadPnpNodes();
            PnpNode adapter = FindUnique(
                nodes, config.AdapterInstanceSha256, AdapterRole, false);
            PnpNode pairedEndpoint = FindUnique(
                nodes, config.PairedPnpInstanceSha256, PairedEndpointRole, false);
            PnpNode hid = FindUnique(
                nodes, config.HidPnpInstanceSha256, HidChildRole, false);
            Radio bluetoothRadio = AwaitResult(
                Radio.GetRadiosAsync().AsTask(), "Bluetooth radio enumeration")
                .SingleOrDefault(item => item.Kind == RadioKind.Bluetooth);
            DeviceInformationCollection endpoints = FindPairedAeps();
            DeviceInformation[] pairedMatches = endpoints.Where(item =>
                string.Equals(item.Name, config.HogpDeviceName, StringComparison.Ordinal) &&
                item.Pairing.IsPaired &&
                string.Equals(Hash(item.Id), config.TargetAepSha256, StringComparison.Ordinal))
                .ToArray();
            return new Observation {
                Adapter = adapter,
                PairedEndpoint = pairedEndpoint,
                Hid = hid,
                RadioPresent = bluetoothRadio != null,
                RadioState = bluetoothRadio == null ? "Unavailable" : bluetoothRadio.State.ToString(),
                Paired = pairedMatches.Length == 1,
            };
        }

        private void HandleCommand(ControlCommand command, CancellationToken token)
        {
            Guid commandId;
            if (!Guid.TryParseExact(command.command_id, "D", out commandId) ||
                command.provider_generation != providerGeneration ||
                DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() > command.expires_at_unix_ms)
                throw new InvalidDataException("HOGP control command is invalid or expired");
            if (processedCommands.Contains(command.command_id)) return;
            RememberCommand(command.command_id);
            pendingAcknowledgment = new Acknowledgment {
                command_id = command.command_id,
                state = "outcome_unknown",
            };
            SaveState();
            string state = "failed";
            try
            {
                if (!IsElevated()) throw new InvalidOperationException("agent is not elevated");
                if (command.action == "restart_bluetooth_adapter")
                {
                    if (!config.AllowAdapterRestart)
                        throw new InvalidOperationException("adapter restart is disabled locally");
                    Observation before = Observe();
                    if (before.Adapter != null && before.Adapter.Healthy &&
                        before.RadioPresent)
                    {
                        state = "not_required";
                        return;
                    }
                    if (before.Adapter == null || before.RadioState == "Off")
                        throw new InvalidOperationException(
                            "Bluetooth adapter restart precondition is no longer satisfied");
                    RestartExactNode(config.AdapterInstanceSha256, AdapterRole);
                    if (!WaitForPostcondition(true, token))
                        throw new InvalidOperationException("Bluetooth adapter restart postcondition failed");
                }
                else if (command.action == "restart_paired_endpoint")
                {
                    if (!config.AllowEndpointRestart)
                        throw new InvalidOperationException("endpoint restart is disabled locally");
                    Observation before = Observe();
                    if (before.Hid != null && before.Hid.Healthy)
                    {
                        state = "not_required";
                        return;
                    }
                    if (before.Adapter == null || !before.Adapter.Healthy ||
                        !before.RadioPresent || before.RadioState != "On" ||
                        !before.Paired || before.PairedEndpoint == null)
                        throw new InvalidOperationException(
                            "paired endpoint restart precondition is no longer satisfied");
                    RestartExactNode(config.PairedPnpInstanceSha256, PairedEndpointRole);
                    if (!WaitForPostcondition(false, token))
                        throw new InvalidOperationException("paired endpoint restart postcondition failed");
                }
                else
                {
                    throw new InvalidDataException("unsupported HOGP control action");
                }
                state = "executed";
            }
            finally
            {
                pendingAcknowledgment = new Acknowledgment {
                    command_id = command.command_id,
                    state = state,
                };
                SaveState();
            }
        }

        private bool WaitForPostcondition(bool adapterAction, CancellationToken token)
        {
            Stopwatch elapsed = Stopwatch.StartNew();
            do
            {
                if (token.WaitHandle.WaitOne(1000)) return false;
                Observation state = Observe();
                if (adapterAction)
                {
                    if (state.Adapter != null && state.Adapter.Healthy &&
                        state.RadioPresent && state.RadioState == "On") return true;
                }
                else if (state.PairedEndpoint != null && state.PairedEndpoint.Healthy &&
                         state.Hid != null && state.Hid.Healthy)
                {
                    return true;
                }
            } while (elapsed.Elapsed < TimeSpan.FromSeconds(60));
            return false;
        }

        private static void RestartExactNode(string expectedSha256, string role)
        {
            PnpNode node = FindUnique(ReadPnpNodes(), expectedSha256, role, true);
            if (node.InstanceId.IndexOfAny(new[] { '"', '\r', '\n' }) >= 0)
                throw new InvalidDataException("PnP instance identifier contains unsafe characters");
            string executable = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),
                "System32", "pnputil.exe");
            ProcessStartInfo start = new ProcessStartInfo {
                FileName = executable,
                Arguments = "/restart-device \"" + node.InstanceId + "\"",
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            using (Process process = Process.Start(start))
            {
                if (process == null) throw new InvalidOperationException("PnPUtil did not start");
                if (!process.WaitForExit(30000))
                {
                    try { process.Kill(); } catch { }
                    throw new TimeoutException("PnPUtil restart timed out");
                }
                if (process.ExitCode != 0)
                    throw new InvalidOperationException("PnPUtil restart failed with exit code " + process.ExitCode);
            }
        }

        internal static List<PnpNode> ReadPnpNodes()
        {
            List<PnpNode> nodes = new List<PnpNode>();
            using (ManagementObjectSearcher searcher = new ManagementObjectSearcher(
                "SELECT PNPDeviceID,Name,PNPClass,Status,ConfigManagerErrorCode FROM Win32_PnPEntity"))
            {
                searcher.Options.Timeout = TimeSpan.FromSeconds(10);
                using (ManagementObjectCollection results = searcher.Get())
                {
                    foreach (ManagementObject item in results)
                    {
                        string instance = Convert.ToString(
                            item["PNPDeviceID"], CultureInfo.InvariantCulture);
                        if (string.IsNullOrWhiteSpace(instance)) continue;
                        nodes.Add(new PnpNode {
                            InstanceId = instance,
                            InstanceSha256 = Hash(instance),
                            Name = Convert.ToString(item["Name"], CultureInfo.InvariantCulture),
                            PnpClass = Convert.ToString(item["PNPClass"], CultureInfo.InvariantCulture),
                            Status = Convert.ToString(item["Status"], CultureInfo.InvariantCulture),
                            ProblemCode = item["ConfigManagerErrorCode"] == null ? 255 :
                                Convert.ToInt32(
                                    item["ConfigManagerErrorCode"],
                                    CultureInfo.InvariantCulture),
                        });
                    }
                }
            }
            return nodes;
        }

        internal static string PairedAepSelector()
        {
            return BluetoothLEDevice.GetDeviceSelectorFromPairingState(true);
        }

        internal static DeviceInformationCollection FindPairedAeps()
        {
            return AwaitResult(
                DeviceInformation.FindAllAsync(
                    PairedAepSelector(), null,
                    DeviceInformationKind.AssociationEndpoint).AsTask(),
                "paired Bluetooth AEP enumeration", PairedAepEnumerationTimeout);
        }

        internal static T AwaitResult<T>(Task<T> task, string operation)
        {
            return AwaitResult(task, operation, DefaultEnumerationTimeout);
        }

        internal static T AwaitResult<T>(Task<T> task, string operation, TimeSpan timeout)
        {
            if (timeout <= TimeSpan.Zero)
                throw new ArgumentOutOfRangeException("timeout");
            Task completed = Task.WhenAny(task, Task.Delay(timeout))
                .GetAwaiter().GetResult();
            if (!object.ReferenceEquals(completed, task))
                throw new TimeoutException(operation + " timed out");
            return task.GetAwaiter().GetResult();
        }

        private static PnpNode FindUnique(
            List<PnpNode> nodes, string sha256, string role, bool required)
        {
            PnpNode[] matches = nodes.Where(item =>
                string.Equals(item.InstanceSha256, sha256, StringComparison.Ordinal) &&
                MatchesRole(item, role)).ToArray();
            if (matches.Length == 1) return matches[0];
            if (!required && matches.Length == 0) return null;
            throw new InvalidOperationException(
                "expected exactly one enrolled PnP instance for role " + role);
        }

        internal static string Role(PnpNode node)
        {
            foreach (string role in new[] { AdapterRole, PairedEndpointRole, HidChildRole })
                if (MatchesRole(node, role)) return role;
            return null;
        }

        private static bool MatchesRole(PnpNode node, string role)
        {
            if (role == AdapterRole)
                return string.Equals(node.PnpClass, "Bluetooth", StringComparison.OrdinalIgnoreCase) &&
                    (node.InstanceId.StartsWith("USB\\", StringComparison.OrdinalIgnoreCase) ||
                     node.InstanceId.StartsWith("PCI\\", StringComparison.OrdinalIgnoreCase));
            if (role == PairedEndpointRole)
                return string.Equals(node.PnpClass, "Bluetooth", StringComparison.OrdinalIgnoreCase) &&
                    node.InstanceId.StartsWith("BTHLE\\DEV_", StringComparison.OrdinalIgnoreCase);
            if (role == HidChildRole)
                return node.InstanceId.StartsWith("BTHLEDEVICE\\", StringComparison.OrdinalIgnoreCase) &&
                    (string.Equals(node.PnpClass, "HIDClass", StringComparison.OrdinalIgnoreCase) ||
                     string.Equals(node.PnpClass, "Mouse", StringComparison.OrdinalIgnoreCase));
            throw new InvalidDataException("unsupported enrolled PnP role");
        }

        private ControlResponse Post(ControlReport report)
        {
            byte[] body = Encoding.UTF8.GetBytes(serializer.Serialize(report));
            long seq = Interlocked.Increment(ref sequence);
            SaveState();
            long timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            Uri endpoint = new Uri(config.Endpoint);
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(endpoint);
            request.Method = "POST";
            request.ContentType = "application/json";
            request.ContentLength = body.Length;
            request.KeepAlive = true;
            request.Timeout = config.RequestTimeoutMilliseconds;
            request.ReadWriteTimeout = config.RequestTimeoutMilliseconds;
            request.Headers["X-Agent-Key"] = config.KeyId;
            request.Headers["X-Timestamp"] = timestamp.ToString(CultureInfo.InvariantCulture);
            request.Headers["X-Sequence"] = seq.ToString(CultureInfo.InvariantCulture);
            request.Headers["X-Signature"] = Sign(seq, timestamp, endpoint.AbsolutePath, body);
            request.ServerCertificateValidationCallback = ValidateCertificate;
            using (Stream stream = request.GetRequestStream()) stream.Write(body, 0, body.Length);
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            {
                if (response.StatusCode != HttpStatusCode.Accepted)
                    throw new WebException("HOGP control receiver returned " + (int)response.StatusCode);
                using (Stream stream = response.GetResponseStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                {
                    ControlResponse accepted = serializer.Deserialize<ControlResponse>(reader.ReadToEnd());
                    if (accepted == null || accepted.accepted_seq != seq)
                        throw new InvalidDataException("HOGP control response correlation mismatch");
                    return accepted;
                }
            }
        }

        private bool ValidateCertificate(object sender, X509Certificate certificate,
            X509Chain chain, SslPolicyErrors errors)
        {
            if (certificate == null) return false;
            using (SHA256 sha = SHA256.Create())
                return FixedEquals(certificatePin, Hex(sha.ComputeHash(certificate.GetRawCertData())));
        }

        private string Sign(long seq, long timestamp, string path, byte[] body)
        {
            string bodyHash;
            using (SHA256 sha = SHA256.Create()) bodyHash = Hex(sha.ComputeHash(body));
            string canonical = string.Format(CultureInfo.InvariantCulture,
                "POST\n{0}\n{1}\n{2}\n{3}", path, timestamp, seq, bodyHash.ToLowerInvariant());
            using (HMACSHA256 hmac = new HMACSHA256(secret))
                return Hex(hmac.ComputeHash(Encoding.ASCII.GetBytes(canonical))).ToLowerInvariant();
        }

        private void RememberCommand(string commandId)
        {
            processedCommands.Add(commandId);
            processedOrder.Enqueue(commandId);
            while (processedOrder.Count > 256)
                processedCommands.Remove(processedOrder.Dequeue());
        }

        private static bool IsElevated()
        {
            using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
                return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
        }

        private static bool IsCanonicalGuid(string value)
        {
            Guid parsed;
            return Guid.TryParseExact(value, "D", out parsed) &&
                string.Equals(parsed.ToString("D"), value, StringComparison.Ordinal);
        }

        internal static string Hash(string value)
        {
            using (SHA256 sha = SHA256.Create())
                return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(value)));
        }

        private static bool FixedEquals(string left, string right)
        {
            if (left == null || right == null || left.Length != right.Length) return false;
            int difference = 0;
            for (int index = 0; index < left.Length; index++) difference |= left[index] ^ right[index];
            return difference == 0;
        }

        private static string NormalizeHex(string value)
        {
            return (value ?? "").Replace(":", "").Replace(" ", "").ToUpperInvariant();
        }

        private static string Hex(byte[] bytes)
        {
            StringBuilder value = new StringBuilder(bytes.Length * 2);
            foreach (byte item in bytes) value.Append(item.ToString("X2", CultureInfo.InvariantCulture));
            return value.ToString();
        }
    }

    internal static class Program
    {
        private static int Main(string[] args)
        {
            try
            {
                if (args.Length == 1 && args[0] == "--protect-secret")
                {
                    string plain = Console.In.ReadLine();
                    if (string.IsNullOrEmpty(plain)) throw new InvalidDataException("secret was empty");
                    byte[] clear = Encoding.UTF8.GetBytes(plain);
                    try
                    {
                        Console.WriteLine(Convert.ToBase64String(ProtectedData.Protect(clear, null,
                            DataProtectionScope.CurrentUser)));
                    }
                    finally { Array.Clear(clear, 0, clear.Length); }
                    return 0;
                }
                if (args.Length == 3 && args[0] == "--inspect-identities")
                {
                    InspectIdentities(args[1], args[2]);
                    return 0;
                }
                if (args.Length != 2 || args[0] != "--config")
                {
                    Console.Error.WriteLine("Usage: HogpControlAgent.exe --config <agent.json>");
                    Console.Error.WriteLine("       HogpControlAgent.exe --protect-secret");
                    Console.Error.WriteLine("       HogpControlAgent.exe --inspect-identities <HOGP-name> <result.json>");
                    return 2;
                }
                AgentConfig config = new JavaScriptSerializer().Deserialize<AgentConfig>(
                    File.ReadAllText(args[1]));
                ValidateConfig(config);
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
                using (CancellationTokenSource cancellation = new CancellationTokenSource())
                {
                    Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs eventArgs) {
                        eventArgs.Cancel = true;
                        cancellation.Cancel();
                    };
                    using (Agent agent = new Agent(config)) agent.Run(cancellation.Token);
                }
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("FATAL: " + ex.Message);
                return 1;
            }
        }

        private static void InspectIdentities(string hogpDeviceName, string resultPath)
        {
            if (string.IsNullOrWhiteSpace(hogpDeviceName) || string.IsNullOrWhiteSpace(resultPath))
                throw new InvalidDataException("HOGP name and result path are required");
            DeviceInformationCollection endpoints = Agent.FindPairedAeps();
            Radio[] radios = Agent.AwaitResult(
                Radio.GetRadiosAsync().AsTask(), "Bluetooth radio enumeration")
                .Where(item => item.Kind == RadioKind.Bluetooth).ToArray();
            List<PnpNode> nodes = Agent.ReadPnpNodes();
            IdentityInspection report = new IdentityInspection {
                schema = "mousse-hogp-control-identities-v1",
                hogp_device_name = hogpDeviceName,
                radio_state = radios.Length == 1 ? radios[0].State.ToString() :
                    (radios.Length == 0 ? "Unavailable" : "Ambiguous"),
                aep_candidates = endpoints.Where(item =>
                    string.Equals(item.Name, hogpDeviceName, StringComparison.Ordinal))
                    .Select(item => new AepCandidate {
                        name = item.Name,
                        paired = item.Pairing.IsPaired,
                        aep_sha256 = Agent.Hash(item.Id),
                    }).ToArray(),
                pnp_candidates = nodes.Where(item => Agent.Role(item) != null)
                    .Select(item => new IdentityCandidate {
                        kind = Agent.Role(item),
                        name = item.Name,
                        pnp_class = item.PnpClass,
                        instance_sha256 = item.InstanceSha256,
                        status = item.Status,
                        problem_code = item.ProblemCode,
                    }).ToArray(),
            };
            string destination = Path.GetFullPath(resultPath);
            string parent = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(parent)) Directory.CreateDirectory(parent);
            string json = new JavaScriptSerializer().Serialize(report);
            File.WriteAllText(destination, json, new UTF8Encoding(false));
            Console.WriteLine(json);
        }

        private static void ValidateConfig(AgentConfig config)
        {
            Uri endpoint;
            if (config == null || !Uri.TryCreate(config.Endpoint, UriKind.Absolute, out endpoint) ||
                endpoint.Scheme != Uri.UriSchemeHttps || endpoint.AbsolutePath != "/v1/hogp-control")
                throw new InvalidDataException("endpoint must be HTTPS /v1/hogp-control");
            if (string.IsNullOrWhiteSpace(config.KeyId) || config.KeyId.Length > 128 ||
                string.IsNullOrWhiteSpace(config.SecretDpapi))
                throw new InvalidDataException("key id and DPAPI secret are required");
            if (!IsSha256(config.CertificateSha256))
                throw new InvalidDataException("certificate SHA-256 must contain 64 hex characters");
            if (string.IsNullOrWhiteSpace(config.HogpDeviceName) || config.HogpDeviceName.Length > 256)
                throw new InvalidDataException("HOGP device name is required");
            foreach (string value in new[] {
                config.TargetAepSha256, config.AdapterInstanceSha256,
                config.PairedPnpInstanceSha256, config.HidPnpInstanceSha256,
            })
            {
                if (!IsSha256(value))
                    throw new InvalidDataException("enrolled identities must contain 64 hex characters");
            }
            config.TargetAepSha256 = Normalize(config.TargetAepSha256);
            config.AdapterInstanceSha256 = Normalize(config.AdapterInstanceSha256);
            config.PairedPnpInstanceSha256 = Normalize(config.PairedPnpInstanceSha256);
            config.HidPnpInstanceSha256 = Normalize(config.HidPnpInstanceSha256);
            if (config.IntervalMilliseconds < 1000 || config.IntervalMilliseconds > 60000)
                throw new InvalidDataException("interval must be between 1000 and 60000 ms");
            if (config.RequestTimeoutMilliseconds < 1000 || config.RequestTimeoutMilliseconds > 30000)
                throw new InvalidDataException("request timeout must be between 1000 and 30000 ms");
            if (string.IsNullOrWhiteSpace(config.StatePath))
                throw new InvalidDataException("state path is required");
            string statePath = Path.GetFullPath(config.StatePath);
            string stateRoot = Path.GetFullPath(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "MousseControler", "Qualification", "MC-HOGP-NATIVE-OWNER-001"));
            if (!statePath.StartsWith(stateRoot + Path.DirectorySeparatorChar,
                StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("state path must be inside the protected qualification root");
            config.StatePath = statePath;
        }

        private static string Normalize(string value)
        {
            return (value ?? "").Replace(":", "").Replace(" ", "").ToUpperInvariant();
        }

        private static bool IsSha256(string value)
        {
            string normalized = Normalize(value);
            return normalized.Length == 64 && normalized.All(character =>
                (character >= '0' && character <= '9') ||
                (character >= 'A' && character <= 'F'));
        }
    }
}
