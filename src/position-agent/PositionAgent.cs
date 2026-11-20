using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Devices.Enumeration;

namespace MousseControler.PositionAgent
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
    }

    internal sealed class HogpReconnectMonitor : IDisposable
    {
        private const string Selector =
            "System.Devices.Aep.ProtocolId:=\"{BB7BB05E-5972-42B5-94FC-76EAA7084D49}\"";
        private static readonly string[] RequestedProperties = {
            "System.Devices.Aep.IsPresent",
            "System.Devices.Aep.IsConnected",
            "System.Devices.Aep.Bluetooth.Le.IsConnectable"
        };
        private readonly string exactName;
        private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
        private readonly Thread worker;
        private BluetoothLEDevice device;
        private IReadOnlyList<GattDeviceService> services;

        internal HogpReconnectMonitor(string exactName)
        {
            this.exactName = exactName;
            worker = new Thread(Run) { IsBackground = true, Name = "HOGP reconnect monitor" };
        }

        internal void Start()
        {
            Console.WriteLine("HOGP reconnect monitor: paired endpoint '" + exactName + "'.");
            worker.Start();
        }

        public void Dispose()
        {
            cancellation.Cancel();
            bool stopped = !worker.IsAlive || worker.Join(35000);
            ReleaseConnection();
            if (stopped) cancellation.Dispose();
        }

        private void Run()
        {
            while (!cancellation.IsCancellationRequested)
            {
                try
                {
                    if (device == null || device.ConnectionStatus != BluetoothConnectionStatus.Connected)
                    {
                        ReleaseConnection();
                        ConnectOnce();
                    }
                }
                catch (Exception ex)
                {
                    ReleaseConnection();
                    Console.Error.WriteLine("[{0:O}] HOGP reconnect pending: {1}",
                        DateTimeOffset.Now, ex.Message);
                }
                cancellation.Token.WaitHandle.WaitOne(2000);
            }
        }

        private void ConnectOnce()
        {
            DeviceInformationCollection candidates = DeviceInformation.FindAllAsync(
                Selector, RequestedProperties, DeviceInformationKind.AssociationEndpoint)
                .AsTask().GetAwaiter().GetResult();
            DeviceInformation selected = null;
            foreach (DeviceInformation candidate in candidates)
            {
                if (!string.Equals(candidate.Name, exactName, StringComparison.Ordinal) ||
                    !candidate.Pairing.IsPaired ||
                    !GetBoolean(candidate, "System.Devices.Aep.IsPresent") ||
                    !GetBoolean(candidate, "System.Devices.Aep.Bluetooth.Le.IsConnectable"))
                    continue;
                selected = candidate;
                break;
            }
            if (selected == null) throw new InvalidOperationException("paired HOGP endpoint is not connectable");

            BluetoothLEDevice candidateDevice = BluetoothLEDevice.FromIdAsync(selected.Id)
                .AsTask().GetAwaiter().GetResult();
            if (candidateDevice == null) throw new InvalidOperationException("BluetoothLEDevice creation returned null");
            GattDeviceServicesResult result = candidateDevice.GetGattServicesForUuidAsync(
                GattServiceUuids.HumanInterfaceDevice, BluetoothCacheMode.Uncached)
                .AsTask().GetAwaiter().GetResult();
            if (result.Status != GattCommunicationStatus.Success || result.Services.Count != 1)
            {
                foreach (GattDeviceService service in result.Services) service.Dispose();
                candidateDevice.Dispose();
                throw new InvalidOperationException("HOGP service connection status: " + result.Status);
            }
            if (cancellation.IsCancellationRequested)
            {
                foreach (GattDeviceService service in result.Services) service.Dispose();
                candidateDevice.Dispose();
                return;
            }
            device = candidateDevice;
            services = result.Services;
            Console.WriteLine("[{0:O}] HOGP link connected; native HID service active.", DateTimeOffset.Now);
        }

        private static bool GetBoolean(DeviceInformation candidate, string name)
        {
            object value;
            return candidate.Properties.TryGetValue(name, out value) && value is bool && (bool)value;
        }

        private void ReleaseConnection()
        {
            if (services != null)
            {
                foreach (GattDeviceService service in services) service.Dispose();
                services = null;
            }
            if (device != null)
            {
                device.Dispose();
                device = null;
            }
        }
    }

    internal sealed class DisplayInfo
    {
        public int X;
        public int Y;
        public int Width;
        public int Height;
        public uint DpiX;
        public uint DpiY;
        public bool Primary;

        public string Canonical()
        {
            return string.Format(CultureInfo.InvariantCulture, "{0},{1},{2},{3},{4},{5},{6}",
                X, Y, Width, Height, DpiX, DpiY, Primary ? 1 : 0);
        }

        public string Json()
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{{\"x\":{0},\"y\":{1},\"width\":{2},\"height\":{3},\"dpi_x\":{4},\"dpi_y\":{5},\"primary\":{6}}}",
                X, Y, Width, Height, DpiX, DpiY, Primary ? "true" : "false");
        }
    }

    internal static class NativeMethods
    {
        [StructLayout(LayoutKind.Sequential)]
        internal struct Point { public int X; public int Y; }

        [StructLayout(LayoutKind.Sequential)]
        internal struct Rect { public int Left; public int Top; public int Right; public int Bottom; }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
        internal struct MonitorInfo
        {
            public int Size;
            public Rect Monitor;
            public Rect Work;
            public uint Flags;
        }

        internal delegate bool MonitorEnumProc(IntPtr monitor, IntPtr hdc, ref Rect rect, IntPtr data);

        [DllImport("user32.dll")]
        internal static extern bool GetPhysicalCursorPos(out Point point);

        [DllImport("user32.dll")]
        internal static extern bool SetProcessDpiAwarenessContext(IntPtr value);

        [DllImport("user32.dll")]
        internal static extern bool EnumDisplayMonitors(IntPtr hdc, IntPtr clip, MonitorEnumProc callback, IntPtr data);

        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        internal static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);

        [DllImport("shcore.dll")]
        internal static extern int GetDpiForMonitor(IntPtr monitor, int dpiType, out uint dpiX, out uint dpiY);

        [DllImport("kernel32.dll")]
        internal static extern bool ProcessIdToSessionId(uint processId, out uint sessionId);

        [DllImport("user32.dll", SetLastError = true)]
        internal static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint desiredAccess);

        [DllImport("user32.dll", SetLastError = true)]
        internal static extern bool CloseDesktop(IntPtr desktop);

        internal const uint DesktopReadObjects = 0x0001;
        internal const uint MonitorPrimary = 0x00000001;
    }

    internal sealed class Agent : IDisposable
    {
        private readonly AgentConfig config;
        private readonly byte[] secret;
        private readonly string certificatePin;
        private long sequence;
        private string previousTopology;
        private uint previousSession = uint.MaxValue;
        private readonly HogpReconnectMonitor reconnectMonitor;

        internal Agent(AgentConfig config)
        {
            this.config = config;
            sequence = checked(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1000L);
            secret = ProtectedData.Unprotect(Convert.FromBase64String(config.SecretDpapi), null,
                DataProtectionScope.CurrentUser);
            certificatePin = NormalizeHex(config.CertificateSha256);
            if (certificatePin.Length != 64) throw new InvalidDataException("certificate SHA-256 must contain 64 hex characters");
            if (!string.IsNullOrWhiteSpace(config.HogpDeviceName))
                reconnectMonitor = new HogpReconnectMonitor(config.HogpDeviceName);
        }

        public void Dispose()
        {
            if (reconnectMonitor != null) reconnectMonitor.Dispose();
            if (secret != null) Array.Clear(secret, 0, secret.Length);
        }

        internal void Run(CancellationToken token)
        {
            Console.WriteLine("Mousse Position Agent — visible, outbound-only. Ctrl+C to stop.");
            Console.WriteLine("Endpoint: " + config.Endpoint);
            if (reconnectMonitor != null) reconnectMonitor.Start();
            while (!token.IsCancellationRequested)
            {
                Stopwatch cycle = Stopwatch.StartNew();
                try
                {
                    NativeMethods.Point point;
                    long cursorStarted = Stopwatch.GetTimestamp();
                    if (!NativeMethods.GetPhysicalCursorPos(out point))
                        throw new InvalidOperationException("GetPhysicalCursorPos failed: " + Marshal.GetLastWin32Error());
                    long cursorReadMicroseconds = (Stopwatch.GetTimestamp() - cursorStarted) * 1000000L /
                        Stopwatch.Frequency;
                    uint session;
                    if (!NativeMethods.ProcessIdToSessionId((uint)Process.GetCurrentProcess().Id, out session))
                        throw new InvalidOperationException("ProcessIdToSessionId failed");
                    bool inputDesktop = InputDesktopAvailable();
                    List<DisplayInfo> displays = ReadDisplays();
                    string topology = TopologyHash(displays);
                    if (session != previousSession || topology != previousTopology)
                    {
                        Console.WriteLine("[{0:O}] session={1}, topology={2}, inputDesktop={3}",
                            DateTimeOffset.Now, session, topology.Substring(0, 12), inputDesktop);
                        previousSession = session;
                        previousTopology = topology;
                    }
                    if (!inputDesktop) throw new InvalidOperationException("interactive input desktop is unavailable");
                    long seq = Interlocked.Increment(ref sequence);
                    long timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                    string body = BuildBody(point, session, topology, displays, timestamp, cursorReadMicroseconds);
                    Post(seq, timestamp, Encoding.UTF8.GetBytes(body));
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine("[{0:O}] DEGRADED: {1}", DateTimeOffset.Now, ex.Message);
                }
                int remaining = config.IntervalMilliseconds - (int)cycle.ElapsedMilliseconds;
                if (remaining > 0) token.WaitHandle.WaitOne(remaining);
            }
            Console.WriteLine("Agent stopped; no input command capability was active.");
        }

        private static bool InputDesktopAvailable()
        {
            IntPtr desktop = NativeMethods.OpenInputDesktop(0, false, NativeMethods.DesktopReadObjects);
            if (desktop == IntPtr.Zero) return false;
            NativeMethods.CloseDesktop(desktop);
            return true;
        }

        private static List<DisplayInfo> ReadDisplays()
        {
            List<DisplayInfo> displays = new List<DisplayInfo>();
            NativeMethods.MonitorEnumProc callback = delegate(IntPtr monitor, IntPtr hdc, ref NativeMethods.Rect rect, IntPtr data)
            {
                NativeMethods.MonitorInfo info = new NativeMethods.MonitorInfo();
                info.Size = Marshal.SizeOf(typeof(NativeMethods.MonitorInfo));
                if (!NativeMethods.GetMonitorInfo(monitor, ref info)) return true;
                uint dpiX = 96, dpiY = 96;
                try { NativeMethods.GetDpiForMonitor(monitor, 0, out dpiX, out dpiY); }
                catch (DllNotFoundException) { }
                displays.Add(new DisplayInfo {
                    X = info.Monitor.Left,
                    Y = info.Monitor.Top,
                    Width = info.Monitor.Right - info.Monitor.Left,
                    Height = info.Monitor.Bottom - info.Monitor.Top,
                    DpiX = dpiX,
                    DpiY = dpiY,
                    Primary = (info.Flags & NativeMethods.MonitorPrimary) != 0,
                });
                return true;
            };
            if (!NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, callback, IntPtr.Zero) || displays.Count == 0)
                throw new InvalidOperationException("display topology enumeration failed");
            displays.Sort((a, b) => string.CompareOrdinal(a.Canonical(), b.Canonical()));
            return displays;
        }

        private static string TopologyHash(List<DisplayInfo> displays)
        {
            StringBuilder canonical = new StringBuilder();
            foreach (DisplayInfo display in displays) canonical.Append(display.Canonical()).Append(';');
            using (SHA256 sha = SHA256.Create()) return Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(canonical.ToString())));
        }

        private static string BuildBody(NativeMethods.Point point, uint session, string topology,
            List<DisplayInfo> displays, long observedAt, long cursorReadMicroseconds)
        {
            StringBuilder json = new StringBuilder();
            json.AppendFormat(CultureInfo.InvariantCulture,
                "{{\"x\":{0},\"y\":{1},\"session_id\":{2},\"session_active\":true,\"topology_generation\":\"{3}\",\"observed_at_unix_ms\":{4},\"cursor_read_us\":{5},\"displays\":[",
                point.X, point.Y, session, topology, observedAt, cursorReadMicroseconds);
            for (int i = 0; i < displays.Count; i++)
            {
                if (i != 0) json.Append(',');
                json.Append(displays[i].Json());
            }
            return json.Append("]}").ToString();
        }

        private void Post(long seq, long timestamp, byte[] body)
        {
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(config.Endpoint);
            request.Method = "POST";
            request.ContentType = "application/json";
            request.ContentLength = body.Length;
            request.KeepAlive = true;
            request.Timeout = config.RequestTimeoutMilliseconds;
            request.ReadWriteTimeout = config.RequestTimeoutMilliseconds;
            request.Headers["X-Agent-Key"] = config.KeyId;
            request.Headers["X-Timestamp"] = timestamp.ToString(CultureInfo.InvariantCulture);
            request.Headers["X-Sequence"] = seq.ToString(CultureInfo.InvariantCulture);
            request.Headers["X-Signature"] = Sign(seq, timestamp, body);
            request.ServerCertificateValidationCallback = ValidateCertificate;
            using (Stream stream = request.GetRequestStream()) stream.Write(body, 0, body.Length);
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            {
                if (response.StatusCode != HttpStatusCode.Accepted)
                    throw new WebException("position receiver returned " + (int)response.StatusCode);
            }
        }

        private bool ValidateCertificate(object sender, X509Certificate certificate, X509Chain chain, SslPolicyErrors errors)
        {
            if (certificate == null) return false;
            using (SHA256 sha = SHA256.Create())
                return FixedEquals(certificatePin, Hex(sha.ComputeHash(certificate.GetRawCertData())));
        }

        private string Sign(long seq, long timestamp, byte[] body)
        {
            string bodyHash;
            using (SHA256 sha = SHA256.Create()) bodyHash = Hex(sha.ComputeHash(body));
            string canonical = string.Format(CultureInfo.InvariantCulture,
                "POST\n/v1/position\n{0}\n{1}\n{2}", timestamp, seq, bodyHash.ToLowerInvariant());
            using (HMACSHA256 hmac = new HMACSHA256(secret))
                return Hex(hmac.ComputeHash(Encoding.ASCII.GetBytes(canonical))).ToLowerInvariant();
        }

        private static bool FixedEquals(string a, string b)
        {
            if (a.Length != b.Length) return false;
            int difference = 0;
            for (int i = 0; i < a.Length; i++) difference |= a[i] ^ b[i];
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
                NativeMethods.SetProcessDpiAwarenessContext(new IntPtr(-4)); // Per-monitor v2
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
                if ((args.Length == 2 || args.Length == 3) && args[0] == "--hogp-reconnect")
                {
                    if (string.IsNullOrWhiteSpace(args[1]))
                        throw new InvalidDataException("HOGP device name was empty");
                    if (args.Length == 3)
                    {
                        StreamWriter log = new StreamWriter(args[2], true, new UTF8Encoding(false));
                        log.AutoFlush = true;
                        Console.SetOut(log);
                        Console.SetError(log);
                    }
                    using (CancellationTokenSource cancellation = new CancellationTokenSource())
                    using (HogpReconnectMonitor monitor = new HogpReconnectMonitor(args[1]))
                    {
                        Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs eventArgs) {
                            eventArgs.Cancel = true;
                            cancellation.Cancel();
                        };
                        monitor.Start();
                        cancellation.Token.WaitHandle.WaitOne();
                    }
                    return 0;
                }
                if (args.Length != 2 || args[0] != "--config")
                {
                    Console.Error.WriteLine("Usage: PositionAgent.exe --config <agent.json>");
                    Console.Error.WriteLine("       PositionAgent.exe --hogp-reconnect <exact-device-name> [log-path]");
                    Console.Error.WriteLine("       PositionAgent.exe --protect-secret  (reads one line from stdin)");
                    return 2;
                }
                AgentConfig config = new JavaScriptSerializer().Deserialize<AgentConfig>(File.ReadAllText(args[1]));
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

        private static void ValidateConfig(AgentConfig config)
        {
            Uri endpoint;
            if (config == null || !Uri.TryCreate(config.Endpoint, UriKind.Absolute, out endpoint)
                || endpoint.Scheme != Uri.UriSchemeHttps || endpoint.AbsolutePath != "/v1/position")
                throw new InvalidDataException("endpoint must be HTTPS /v1/position");
            if (string.IsNullOrWhiteSpace(config.KeyId) || string.IsNullOrWhiteSpace(config.SecretDpapi))
                throw new InvalidDataException("key id and DPAPI secret are required");
            if (config.IntervalMilliseconds < 20 || config.IntervalMilliseconds > 1000)
                throw new InvalidDataException("interval must be between 20 and 1000 ms");
            if (config.RequestTimeoutMilliseconds < 100 || config.RequestTimeoutMilliseconds > 5000)
                throw new InvalidDataException("request timeout must be between 100 and 5000 ms");
        }
    }
}
