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
        private readonly Button william = new Button();
        private readonly Button hinoenma = new Button();
        private readonly Label character = new Label();
        private readonly ProgressBar progress = new ProgressBar();
        private bool busy;

        internal LauncherForm(bool autoRun)
        {
            Text = "仁王 · 飞缘魔启动工具 " + Profile.DisplayVersion;
            ClientSize = new Size(480, 425);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.Dpi;
            Font = new Font("Microsoft YaHei UI", 10);
            BackColor = Color.FromArgb(248, 249, 252);
            Label title = new Label { Text = "飞缘魔 · 启用与角色切换", Location = new Point(24, 22), Size = new Size(430, 35), Font = new Font(Font.FontFamily, 17, FontStyle.Bold) };
            Label version = new Label { Text = "Steam 1.24.8  /  实验版 " + Profile.DisplayVersion, Location = new Point(25, 63), Size = new Size(425, 24), ForeColor = Color.DimGray };
            status.Location = new Point(24, 105); status.Size = new Size(430, 30); status.Font = new Font(Font.FontFamily, 12, FontStyle.Bold);
            detail.Location = new Point(24, 144); detail.Size = new Size(430, 78);
            character.Location = new Point(24, 236); character.Size = new Size(430, 48); character.ForeColor = Color.DimGray;
            progress.Location = new Point(25, 290); progress.Size = new Size(430, 5); progress.Style = ProgressBarStyle.Marquee;
            william.Text = "切换回威廉"; william.Location = new Point(24, 308); william.Size = new Size(210, 36);
            hinoenma.Text = "切换为飞缘魔"; hinoenma.Location = new Point(245, 308); hinoenma.Size = new Size(210, 36);
            Label hint = new Label { Text = Profile.LivingWeapon ? "9 九十九 · F6 净化；角色切换需返回主菜单后载入。" : Profile.ManualPurification ? "F6 净化常世；角色切换需返回主菜单后载入。" : "切换在返回主菜单并继续游戏后生效。", Location = new Point(24, 350), Size = new Size(430, 22), ForeColor = Color.DimGray };
            retry.Text = "重新检查"; retry.Location = new Point(236, 379); retry.Size = new Size(106, 35);
            Button close = new Button { Text = "关闭工具", Location = new Point(352, 379), Size = new Size(106, 35) };
            retry.Click += delegate { BeginCheck(); }; close.Click += delegate { Close(); };
            william.Click += delegate { BeginCharacterChange(0); };
            hinoenma.Click += delegate { BeginCharacterChange(0x58E5E); };
            Controls.AddRange(new Control[] { title, version, status, detail, character, progress, william, hinoenma, hint, retry, close });
            SetReport(new Report("checking", "先启动游戏，停在主菜单；本工具会检查并接入飞缘魔。", 0, true));
            FormClosing += delegate(object sender, FormClosingEventArgs e)
            { if (busy) { e.Cancel = true; detail.Text = "正在完成检查，请稍候再关闭。"; } };
            if (autoRun) Shown += delegate { BeginCheck(); };
        }

        internal void SetReport(Report report)
        {
            status.Text = report.State == "enabled" ? "下次载入：" + report.SelectedCharacter : report.State == "checking" ? "正在检查游戏…" : "需要处理";
            status.ForeColor = report.State == "enabled" ? Color.FromArgb(21, 116, 68) : Color.FromArgb(143, 96, 20);
            detail.Text = report.Message;
            progress.Visible = report.State == "checking";
            character.Text = report.State == "enabled" ? "当前角色：" + report.CurrentCharacter + "\n下次载入：" + report.SelectedCharacter : "检查完成后可选择下次载入的角色。";
            william.Enabled = !busy && report.State == "enabled" && report.SelectedTemplate != 0;
            hinoenma.Enabled = !busy && report.State == "enabled" && report.SelectedTemplate == 0;
        }

        private void BeginCharacterChange(uint selection)
        {
            if (busy) return;
            busy = true; retry.Enabled = false;
            SetReport(new Report("checking", "正在选择" + CharacterSelection.Name(selection) + "…", 0, true));
            Task.Factory.StartNew(delegate
            {
                Report result;
                try { result = Program.SelectCharacter(selection); }
                catch (Exception error) { result = new Report("error", error.Message, 0, true); }
                BeginInvoke((Action)delegate { busy = false; retry.Enabled = true; SetReport(result); });
            });
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
        internal static Report SelectCharacter(uint selection)
        {
            Report before;
            using (Game game = new Game(false)) before = game.Inspect();
            if (before.State != "enabled") return before;
            using (Game game = new Game(true)) return game.SelectCharacter(selection, before);
        }

        [STAThread] private static int Main(string[] args)
        {
            if (args.Length == 2 && (args[0] == "--william" || args[0] == "--hinoenma"))
            {
                uint selection = args[0] == "--william" ? 0U : 0x58E5EU;
                Report result;
                try { result = SelectCharacter(selection); }
                catch (Exception error) { result = new Report("error", error.Message, 0, true); }
                File.WriteAllText(args[1], new JavaScriptSerializer().Serialize(result), new System.Text.UTF8Encoding(false));
                return result.State == "enabled" && result.SelectedTemplate == selection ? 0 : 1;
            }
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
            if (args.Length == 2 && args[0] == "--export-legacy-payloads") return SelfTests.ExportLegacyPayloads(args[1]);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            if (args.Length == 2 && args[0] == "--preview")
            {
                using (LauncherForm form = new LauncherForm(false))
                {
                    form.StartPosition = FormStartPosition.Manual;
                    form.Location = new Point(-32000, -32000);
                    form.ShowInTaskbar = false;
                    Report preview = new Report("enabled", "当前正在使用飞缘魔。可选择下次载入的角色，选择后返回主菜单再继续游戏。", 0, true);
                    preview.SelectedTemplate = 0x58E5E; preview.SelectedCharacter = "飞缘魔"; preview.CurrentCharacter = "飞缘魔";
                    form.SetReport(preview);
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
