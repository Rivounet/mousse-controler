using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace MousseControler.Qualification
{
    internal sealed class WitnessForm : Form
    {
        private readonly StreamWriter log;
        private readonly string statePath;

        internal WitnessForm(string logPath, string statePath)
        {
            this.statePath = statePath;
            Text = "Mousse — SAFE MOUSE TEST SURFACE";
            StartPosition = FormStartPosition.CenterScreen;
            Size = new Size(900, 650);
            MinimumSize = new Size(600, 400);
            TopMost = true;
            BackColor = Color.FromArgb(245, 247, 250);
            DoubleBuffered = true;
            Controls.Add(new Label {
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleCenter,
                Font = new Font(FontFamily.GenericSansSerif, 18, FontStyle.Bold),
                ForeColor = Color.FromArgb(30, 50, 70),
                Text = "SURFACE SÛRE MOUSSE\r\n\r\n" +
                       "Les clics, glisser-déposer et roulettes de qualification\r\n" +
                       "sont journalisés ici sans agir sur une autre application.\r\n\r\n" +
                       "Fermez cette fenêtre pour arrêter le témoin.",
            });
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(logPath)));
            log = new StreamWriter(logPath, false, new UTF8Encoding(false)) { AutoFlush = true };
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            Rectangle client = RectangleToScreen(ClientRectangle);
            string state = string.Format(CultureInfo.InvariantCulture,
                "{{\"ready\":true,\"x\":{0},\"y\":{1},\"width\":{2},\"height\":{3},\"pid\":{4}}}",
                client.X, client.Y, client.Width, client.Height,
                System.Diagnostics.Process.GetCurrentProcess().Id);
            File.WriteAllText(statePath, state, new UTF8Encoding(false));
            Log("READY", 0);
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            Log("CLOSED", 0);
            log.Dispose();
            base.OnFormClosed(e);
        }

        protected override void WndProc(ref Message message)
        {
            string name = null;
            int detail = 0;
            switch (message.Msg)
            {
                case 0x0201: name = "LEFT_DOWN"; break;
                case 0x0202: name = "LEFT_UP"; break;
                case 0x0203: name = "LEFT_DOUBLE"; break;
                case 0x0204: name = "RIGHT_DOWN"; break;
                case 0x0205: name = "RIGHT_UP"; break;
                case 0x0206: name = "RIGHT_DOUBLE"; break;
                case 0x0207: name = "MIDDLE_DOWN"; break;
                case 0x0208: name = "MIDDLE_UP"; break;
                case 0x0209: name = "MIDDLE_DOUBLE"; break;
                case 0x020A: name = "WHEEL_VERTICAL"; detail = SignedHighWord(message.WParam); break;
                case 0x020B: name = "XBUTTON_DOWN"; detail = HighWord(message.WParam); break;
                case 0x020C: name = "XBUTTON_UP"; detail = HighWord(message.WParam); break;
                case 0x020E: name = "WHEEL_HORIZONTAL"; detail = SignedHighWord(message.WParam); break;
                case 0x0200:
                    int held = LowWord(message.WParam);
                    if ((held & 0x001F) != 0) { name = "DRAG_MOVE"; detail = held; }
                    break;
            }
            if (name != null) Log(name, detail);
            base.WndProc(ref message);
        }

        private void Log(string name, int detail)
        {
            Point cursor = Cursor.Position;
            log.WriteLine(string.Format(CultureInfo.InvariantCulture,
                "{{\"event\":\"{0}\",\"at_ms\":{1},\"x\":{2},\"y\":{3},\"detail\":{4}}}",
                name, DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(), cursor.X, cursor.Y, detail));
        }

        private static int HighWord(IntPtr value)
        {
            return ((int)value.ToInt64() >> 16) & 0xFFFF;
        }

        private static int SignedHighWord(IntPtr value)
        {
            return (short)HighWord(value);
        }

        private static int LowWord(IntPtr value)
        {
            return (int)value.ToInt64() & 0xFFFF;
        }
    }

    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            if (args.Length != 2)
            {
                Console.Error.WriteLine("Usage: MouseWitness.exe <events.jsonl> <state.json>");
                return 2;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new WitnessForm(args[0], args[1]));
            return 0;
        }
    }
}
