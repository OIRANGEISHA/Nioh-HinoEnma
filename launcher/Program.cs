using System;
using System.IO;
using System.Drawing;
using System.Windows.Forms;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace HinoEnmaTool
{
    internal sealed class LauncherForm : Form
    {
        private readonly Label status = new Label();
        private readonly Label detail = new Label();
        private readonly Button retry = new Button();
        private readonly ProgressBar progress = new ProgressBar();
        private bool busy;

        internal LauncherForm(bool autoRun)
        {
            Text = "仁王 · 飞缘魔启动工具 " + Profile.DisplayVersion;
            ClientSize = new Size(480, 310);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;
            Font = new Font("Microsoft YaHei UI", 10);
            BackColor = Color.FromArgb(248, 249, 252);
            Label title = new Label { Text = "飞缘魔 · 一键启用", Location = new Point(24, 22), Size = new Size(420, 35), Font = new Font(Font.FontFamily, 17, FontStyle.Bold) };
            Label version = new Label { Text = "Steam 1.24.8  /  " + Profile.DisplayVersion, Location = new Point(25, 63), Size = new Size(425, 24), ForeColor = Color.DimGray };
            status.Location = new Point(24, 105); status.Size = new Size(430, 30); status.Font = new Font(Font.FontFamily, 12, FontStyle.Bold);
            detail.Location = new Point(24, 144); detail.Size = new Size(430, 78);
            progress.Location = new Point(25, 226); progress.Size = new Size(430, 5); progress.Style = ProgressBarStyle.Marquee;
            retry.Text = "重新检查"; retry.Location = new Point(236, 254); retry.Size = new Size(106, 35);
            Button close = new Button { Text = "关闭工具", Location = new Point(352, 254), Size = new Size(106, 35) };
            retry.Click += delegate { BeginCheck(); }; close.Click += delegate { Close(); };
            Controls.AddRange(new Control[] { title, version, status, detail, progress, retry, close });
            SetReport(new Report("checking", "先启动游戏，停在主菜单；本工具会检查并接入飞缘魔。", 0, true));
            FormClosing += delegate(object sender, FormClosingEventArgs e)
            { if (busy) { e.Cancel = true; detail.Text = "正在完成检查，请稍候再关闭。"; } };
            if (autoRun) Shown += delegate { BeginCheck(); };
        }

        internal void SetReport(Report report)
        {
            status.Text = report.State == "enabled" ? "已启用" : report.State == "checking" ? "正在检查游戏…" : "需要处理";
            status.ForeColor = report.State == "enabled" ? Color.FromArgb(21, 116, 68) : Color.FromArgb(143, 96, 20);
            detail.Text = report.Message;
            progress.Visible = report.State == "checking";
        }

        private void BeginCheck()
        {
            if (busy) return;
            busy = true; retry.Enabled = false;
            SetReport(new Report("checking", "正在核对游戏版本与人物状态…", 0, true));
            Task.Factory.StartNew(delegate
            {
                Report result;
                try
                {
                    // Idempotence and all refusal states are checked using a
                    // read-only process handle before requesting write access.
                    using (Game game = new Game(false)) result = game.Inspect();
                    if (result.State == "ready") using (Game game = new Game(true)) result = game.Enable();
                }
                catch (Exception error) { result = new Report("error", error.Message, 0, true); }
                BeginInvoke((Action)delegate { busy = false; retry.Enabled = true; SetReport(result); });
            });
        }
    }

    internal static class Program
    {
        [STAThread] private static int Main(string[] args)
        {
            if (args.Length == 2 && args[0] == "--diagnose")
            {
                Report result;
                try { using (Game game = new Game(false)) result = game.Inspect(); }
                catch (Exception error) { result = new Report("error", error.Message, 0, true); }
                File.WriteAllText(args[1], new JavaScriptSerializer().Serialize(result), new System.Text.UTF8Encoding(false));
                return result.State == "error" ? 1 : 0;
            }
            if (args.Length == 2 && args[0] == "--enable")
            {
                Report result;
                try
                {
                    using (Game game = new Game(false)) result = game.Inspect();
                    if (result.State == "ready") using (Game game = new Game(true)) result = game.Enable();
                }
                catch (Exception error) { result = new Report("error", error.Message, 0, true); }
                File.WriteAllText(args[1], new JavaScriptSerializer().Serialize(result), new System.Text.UTF8Encoding(false));
                return result.State == "enabled" ? 0 : 1;
            }
            if (args.Length == 2 && args[0] == "--self-test") return SelfTests.Run(args[1]);
            if (args.Length == 2 && args[0] == "--export-payloads") return SelfTests.ExportPayloads(args[1]);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            if (args.Length == 2 && args[0] == "--preview")
            {
                using (LauncherForm form = new LauncherForm(false))
                {
                    form.StartPosition = FormStartPosition.Manual;
                    form.Location = new Point(-32000, -32000);
                    form.ShowInTaskbar = false;
                    form.SetReport(new Report("enabled", "飞缘魔已接入。现在从主菜单载入关卡即可，可以关闭本工具。", 0, true));
                    form.Show();
                    Application.DoEvents();
                    using (Bitmap bitmap = new Bitmap(form.Width, form.Height))
                    { form.DrawToBitmap(bitmap, new Rectangle(0, 0, bitmap.Width, bitmap.Height)); bitmap.Save(args[1]); }
                    form.Hide();
                }
                return 0;
            }
            Application.Run(new LauncherForm(true));
            return 0;
        }
    }
}
