using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

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
    }

    internal sealed class CaptureRequest
    {
        public string capture_id { get; set; }
        public string action_id { get; set; }
        public string moment { get; set; }
        public long expires_at_ms { get; set; }
        public int max_bytes { get; set; }
        public string format { get; set; }
    }

    internal sealed class PositionResponse
    {
        public long accepted_seq { get; set; }
        public CaptureRequest capture_request { get; set; }
    }

    internal sealed class CapturePoint
    {
        public int x { get; set; }
        public int y { get; set; }
    }

    internal sealed class CaptureMonitor
    {
        public int x { get; set; }
        public int y { get; set; }
        public int width { get; set; }
        public int height { get; set; }
        public bool primary { get; set; }
    }

    internal sealed class CaptureUpload
    {
        public string capture_id { get; set; }
        public string action_id { get; set; }
        public string moment { get; set; }
        public string state { get; set; }
        public long captured_at_ms { get; set; }
        public CapturePoint cursor { get; set; }
        public CaptureMonitor monitor { get; set; }
        public string image_base64 { get; set; }
        public string error { get; set; }
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

        internal Agent(AgentConfig config)
        {
            this.config = config;
            sequence = checked(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1000L);
            secret = ProtectedData.Unprotect(Convert.FromBase64String(config.SecretDpapi), null,
                DataProtectionScope.CurrentUser);
            certificatePin = NormalizeHex(config.CertificateSha256);
            if (certificatePin.Length != 64) throw new InvalidDataException("certificate SHA-256 must contain 64 hex characters");
        }

        public void Dispose()
        {
            if (secret != null) Array.Clear(secret, 0, secret.Length);
        }

        internal void Run(CancellationToken token)
        {
            Console.WriteLine("Mousse Position Agent — visible, outbound-only. Ctrl+C to stop.");
            Console.WriteLine("Endpoint: " + config.Endpoint);
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
                    string response = Post(seq, timestamp, "/v1/position", Encoding.UTF8.GetBytes(body));
                    PositionResponse accepted = new JavaScriptSerializer().Deserialize<PositionResponse>(response);
                    if (accepted == null || accepted.accepted_seq != seq)
                        throw new InvalidDataException("position response correlation mismatch");
                    if (accepted.capture_request != null)
                        HandleCapture(accepted.capture_request);
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

        private void HandleCapture(CaptureRequest request)
        {
            Guid captureGuid;
            if (request == null || !Guid.TryParse(request.capture_id, out captureGuid) ||
                string.IsNullOrWhiteSpace(request.action_id) || request.action_id.Length > 128 ||
                (request.moment != "before" && request.moment != "after") ||
                request.format != "png" || request.max_bytes < 1024 || request.max_bytes > 16 * 1024 * 1024)
                throw new InvalidDataException("capture request is invalid or outside bounds");
            if (DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() > request.expires_at_ms)
                throw new InvalidDataException("capture request expired");

            NativeMethods.Point point;
            if (!NativeMethods.GetPhysicalCursorPos(out point))
                throw new InvalidOperationException("GetPhysicalCursorPos failed before capture");
            List<DisplayInfo> displays = ReadDisplays();
            DisplayInfo selected = null;
            foreach (DisplayInfo display in displays)
            {
                if (point.X >= display.X && point.X < display.X + display.Width &&
                    point.Y >= display.Y && point.Y < display.Y + display.Height)
                {
                    selected = display;
                    break;
                }
            }
            if (selected == null) throw new InvalidOperationException("cursor is outside every enumerated monitor");

            string previousTitle = null;
            try
            {
                try { previousTitle = Console.Title; Console.Title = "Mousse — CAPTURE VISIBLE"; }
                catch (IOException) { }
                Console.WriteLine("[{0:O}] CAPTURE VISIBLE: {1} action={2} monitor={3}x{4} at ({5},{6})",
                    DateTimeOffset.Now, request.moment, request.action_id, selected.Width, selected.Height,
                    selected.X, selected.Y);
                byte[] image;
                using (Bitmap bitmap = new Bitmap(selected.Width, selected.Height, PixelFormat.Format24bppRgb))
                {
                    using (Graphics graphics = Graphics.FromImage(bitmap))
                        graphics.CopyFromScreen(selected.X, selected.Y, 0, 0,
                            new Size(selected.Width, selected.Height), CopyPixelOperation.SourceCopy);
                    using (MemoryStream stream = new MemoryStream())
                    {
                        bitmap.Save(stream, ImageFormat.Png);
                        image = stream.ToArray();
                    }
                }
                if (image.Length > request.max_bytes)
                    throw new InvalidDataException("captured monitor exceeds configured byte limit");
                CaptureUpload upload = new CaptureUpload {
                    capture_id = request.capture_id,
                    action_id = request.action_id,
                    moment = request.moment,
                    state = "CAPTURED",
                    captured_at_ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                    cursor = new CapturePoint { x = point.X, y = point.Y },
                    monitor = new CaptureMonitor {
                        x = selected.X, y = selected.Y, width = selected.Width, height = selected.Height,
                        primary = selected.Primary,
                    },
                    image_base64 = Convert.ToBase64String(image),
                };
                Array.Clear(image, 0, image.Length);
                PostCapture(upload);
                Console.WriteLine("[{0:O}] Capture uploaded: {1}", DateTimeOffset.Now, request.capture_id);
            }
            catch (Exception ex)
            {
                CaptureUpload failed = new CaptureUpload {
                    capture_id = request.capture_id,
                    action_id = request.action_id,
                    moment = request.moment,
                    state = "FAILED",
                    captured_at_ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                    error = ex.Message,
                };
                try { PostCapture(failed); }
                catch (Exception reportError)
                {
                    Console.Error.WriteLine("[{0:O}] Capture failure could not be reported: {1}",
                        DateTimeOffset.Now, reportError.Message);
                }
                throw;
            }
            finally
            {
                if (previousTitle != null) try { Console.Title = previousTitle; } catch (IOException) { }
            }
        }

        private void PostCapture(CaptureUpload upload)
        {
            JavaScriptSerializer serializer = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
            byte[] body = Encoding.UTF8.GetBytes(serializer.Serialize(upload));
            if (body.Length > 24 * 1024 * 1024) throw new InvalidDataException("capture envelope exceeds limit");
            long seq = Interlocked.Increment(ref sequence);
            long timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            Post(seq, timestamp, "/v1/capture", body);
        }

        private string Post(long seq, long timestamp, string path, byte[] body)
        {
            Uri endpoint = new Uri(new Uri(config.Endpoint), path);
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
            request.Headers["X-Signature"] = Sign(seq, timestamp, path, body);
            request.ServerCertificateValidationCallback = ValidateCertificate;
            using (Stream stream = request.GetRequestStream()) stream.Write(body, 0, body.Length);
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            {
                if (response.StatusCode != HttpStatusCode.Accepted)
                    throw new WebException("agent receiver returned " + (int)response.StatusCode);
                using (Stream stream = response.GetResponseStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                    return reader.ReadToEnd();
            }
        }

        private bool ValidateCertificate(object sender, X509Certificate certificate, X509Chain chain, SslPolicyErrors errors)
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
                if (args.Length != 2 || args[0] != "--config")
                {
                    Console.Error.WriteLine("Usage: PositionAgent.exe --config <agent.json>");
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
