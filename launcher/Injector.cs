using System;
using System.IO;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Collections.Generic;

namespace HinoEnmaTool
{
    internal sealed class Fixup
    {
        internal int Offset, Kind, Next;
        internal uint Target;
        internal Fixup(int offset, int kind, uint target, int next)
        { Offset = offset; Kind = kind; Target = target; Next = next; }
    }

    internal sealed class HookSpec
    {
        internal string Name;
        internal uint Rva;
        internal int CodeOffset, CodeCapacity;
        internal byte[] Original, Template;
        internal Fixup[] Fixups;
        internal HookSpec(string name, uint rva, int offset, int capacity, string original, string template, Fixup[] fixups)
        { Name = name; Rva = rva; CodeOffset = offset; CodeCapacity = capacity; Original = Convert.FromBase64String(original); Template = Convert.FromBase64String(template); Fixups = fixups; }

        internal byte[] Payload(long moduleBase, long allocation)
        {
            byte[] result = (byte[])Template.Clone();
            foreach (Fixup item in Fixups)
            {
                byte[] value;
                if (item.Kind == 0) value = BitConverter.GetBytes(allocation + Profile.DataOffset);
                else if (item.Kind == 1)
                {
                    long delta = moduleBase + item.Target - (allocation + CodeOffset + item.Next);
                    if (delta < int.MinValue || delta > int.MaxValue) throw new InvalidOperationException("工具内存距离不合适，停止接入。");
                    value = BitConverter.GetBytes((int)delta);
                }
                else if (item.Kind == 2) value = BitConverter.GetBytes(moduleBase + item.Target);
                else throw new InvalidOperationException("工具配置损坏。");
                Buffer.BlockCopy(value, 0, result, item.Offset, value.Length);
            }
            return result;
        }

        internal byte[] Jump(long moduleBase, long allocation)
        {
            long delta = allocation + CodeOffset - (moduleBase + Rva + 5);
            if (delta < int.MinValue || delta > int.MaxValue) throw new InvalidOperationException("跳转距离超出允许范围。");
            byte[] result = new byte[Original.Length];
            for (int i = 0; i < result.Length; i++) result[i] = 0x90;
            result[0] = 0xE9;
            Buffer.BlockCopy(BitConverter.GetBytes((int)delta), 0, result, 1, 4);
            return result;
        }
    }

    internal sealed class MemorySpan
    {
        internal readonly int Start, End;
        internal MemorySpan(int start, int end) { Start = start; End = end; }
    }

    internal sealed class LegacyProfile
    {
        internal readonly string Version;
        internal readonly int DataOffset, AllocationSize;
        internal readonly HookSpec[] Hooks;
        internal LegacyProfile(string version, int dataOffset, int allocationSize, HookSpec[] hooks)
        { Version = version; DataOffset = dataOffset; AllocationSize = allocationSize; Hooks = hooks; }
    }

    internal enum HookState { Original, Ours, Legacy, Other }

    internal static class PatchTransaction
    {
        internal static void Install(long moduleBase, long allocation, Action<HookSpec, byte[]> write)
        {
            List<HookSpec> touched = new List<HookSpec>();
            try
            {
                foreach (HookSpec hook in Profile.Hooks)
                {
                    touched.Add(hook);
                    write(hook, hook.Jump(moduleBase, allocation));
                }
            }
            catch (Exception failure)
            {
                bool restored = true;
                for (int index = touched.Count - 1; index >= 0; index--)
                    try { write(touched[index], touched[index].Original); }
                    catch { restored = false; }
                if (!restored) throw new InvalidOperationException("接入失败且部分代码未能恢复，请退出并重新启动游戏。", failure);
                throw;
            }
        }
    }

    internal static class Checks
    {
        internal static bool Equal(byte[] left, byte[] right)
        {
            if (left.Length != right.Length) return false;
            for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
            return true;
        }

        internal static long FirstAllocation(long moduleBase)
        { return (moduleBase + Profile.ImageSize + 0xFFFFL) & ~0xFFFFL; }

        internal static List<MemorySpan> CodePages(HookSpec[] hooks, int allocationSize, MemorySpan[] dataPages)
        {
            SortedSet<int> pages = new SortedSet<int>();
            foreach (HookSpec hook in hooks)
            {
                int end = checked(hook.CodeOffset + hook.CodeCapacity);
                if (hook.CodeOffset < 0 || hook.CodeCapacity <= 0 || hook.Template.Length == 0 ||
                    hook.Template.Length > hook.CodeCapacity || end > allocationSize)
                    throw new InvalidOperationException("工具代码范围无效。");
                int first = hook.CodeOffset & ~0xFFF;
                int last = checked((end + 0xFFF) & ~0xFFF);
                foreach (MemorySpan data in dataPages)
                    if (Math.Max(first, data.Start) < Math.Min(last, data.End))
                        throw new InvalidOperationException("工具代码与数据页重叠。");
                for (int at = first; at < last; at += 0x1000) pages.Add(at);
            }
            List<MemorySpan> result = new List<MemorySpan>();
            int start = -1, finish = -1;
            foreach (int page in pages)
            {
                if (page != finish)
                {
                    if (start >= 0) result.Add(new MemorySpan(start, finish));
                    start = page;
                }
                finish = page + 0x1000;
            }
            if (start >= 0) result.Add(new MemorySpan(start, finish));
            return result;
        }

        private static bool SettingsRecognized(Func<long, int, byte[]> read, long candidate, int dataOffset)
        {
            byte[] settings = read(candidate + dataOffset, 0x40);
            uint selected = BitConverter.ToUInt32(settings, 0);
            uint loaded = BitConverter.ToUInt32(settings, 4);
            return CharacterSelection.Supported(selected) &&
                (loaded == 0 || loaded == 0x58E5E || loaded == 0x51BE1) && settings[0x2A] <= 2;
        }

        private static bool Matches(Func<long, int, byte[]> read, long moduleBase, long candidate,
                                    HookSpec[] hooks, int dataOffset)
        {
            try
            {
                foreach (HookSpec hook in hooks)
                {
                    if (!Equal(read(moduleBase + hook.Rva, hook.Original.Length), hook.Jump(moduleBase, candidate))) return false;
                    byte[] wanted = hook.Payload(moduleBase, candidate);
                    if (!Equal(read(candidate + hook.CodeOffset, wanted.Length), wanted)) return false;
                }
                return SettingsRecognized(read, candidate, dataOffset);
            }
            catch (System.ComponentModel.Win32Exception) { return false; }
            catch (IOException) { return false; }
            catch (InvalidOperationException) { return false; }
        }

        internal static HookState Inspect(Func<long, int, byte[]> read, long moduleBase, out long allocation)
        {
            allocation = 0;
            bool original = true;
            foreach (HookSpec hook in Profile.Hooks)
                original &= Equal(read(moduleBase + hook.Rva, hook.Original.Length), hook.Original);
            if (original) return HookState.Original;
            HookSpec first = Profile.Hooks[0];
            byte[] jump = read(moduleBase + first.Rva, first.Original.Length);
            if (jump[0] != 0xE9) return HookState.Other;
            long candidate = moduleBase + first.Rva + 5 + BitConverter.ToInt32(jump, 1) - first.CodeOffset;
            long start = FirstAllocation(moduleBase);
            if ((candidate & 0xFFFFL) != 0 || candidate < start || candidate >= start + 512L * 0x10000) return HookState.Other;
            if (Matches(read, moduleBase, candidate, Profile.Hooks, Profile.DataOffset))
            {
                allocation = candidate;
                return HookState.Ours;
            }
            // Old complete layouts are recognizable but never eligible for
            // reinjection or character writes. Every extra current native
            // site must remain pristine, so a mixed installation is refused.
            foreach (LegacyProfile previous in Profile.LegacyProfiles)
            {
                if (previous.DataOffset != Profile.DataOffset ||
                    !Matches(read, moduleBase, candidate, previous.Hooks, previous.DataOffset)) continue;
                bool complete = true;
                foreach (HookSpec current in Profile.Hooks)
                {
                    bool existed = false;
                    foreach (HookSpec old in previous.Hooks) existed |= old.Rva == current.Rva;
                    if (!existed && !Equal(read(moduleBase + current.Rva, current.Original.Length), current.Original))
                    { complete = false; break; }
                }
                if (complete) { allocation = candidate; return HookState.Legacy; }
            }
            return HookState.Other;
        }
    }

    internal static class CharacterSelection
    {
        internal static bool Supported(uint value)
        { return value == 0 || value == 0x58E5E || value == 0x51BE1; }

        internal static string Name(uint value)
        { return value == 0 ? "威廉" : "飞缘魔"; }

        // Only the next-load selector changes. In particular, leave the
        // resolved template and current actor intact until native preload.
        internal static bool Apply(Func<long, int, byte[]> read, Action<long, byte[]> write,
                                   long moduleBase, long allocation, uint value)
        {
            if (!Supported(value)) throw new InvalidOperationException("角色选择无效。");
            long recognized;
            if (Checks.Inspect(read, moduleBase, out recognized) != HookState.Ours || recognized != allocation)
                throw new InvalidOperationException("当前接入状态已变化，请重新检查。");
            long address = allocation + Profile.DataOffset;
            byte[] previous = read(address, 4), selected = BitConverter.GetBytes(value);
            if (Checks.Equal(previous, selected)) return false;
            try
            {
                write(address, selected);
                if (!Checks.Equal(read(address, 4), selected)) throw new IOException("角色选择未完整写入。");
            }
            catch (Exception failure)
            {
                try
                {
                    write(address, previous);
                    if (!Checks.Equal(read(address, 4), previous)) throw new IOException("角色选择恢复检查失败。");
                }
                catch (Exception)
                { throw new InvalidOperationException("角色选择未能恢复，请退出并重新启动游戏。", failure); }
                throw;
            }
            return true;
        }
    }

    internal sealed class Report
    {
        public string State, Message;
        public int Pid;
        public bool ReadOnly;
        public string Template;
        public uint SelectedTemplate;
        public string SelectedCharacter, CurrentCharacter;
        public bool CharacterChangePending;
        public uint Starts;
        public uint QueuedDoorStarts;
        public uint CameraSuppressions;
        public uint FragmentUses;
        public uint KodamaStarts;
        public uint ConsumableUses;
        public uint LastConsumableId;
        public bool AttributesEnabled;
        public uint AttributeInitializations, AttributeRecalculations;
        public uint BossHp, HpBonus, BossKi, KiBonus, BossDefense, DefenseBonus;
        public uint BossAttack, SelectedMeleeSlot, NativeWeaponAttack, NakedReferenceAttack, WeaponRoutes;
        public uint WeaponHudUpdates, WeaponHudRefreshUpdates, WeaponHudMeleeSwitchUpdates, WeaponHudRangedSwitchUpdates;
        public long WeaponHudWidget;
        public uint RevenantStarts, RevenantInstance, RevenantQueuedRequests, RevenantHoldFlags;
        public uint YokaiGrabPasses;
        public long RevenantObject;
        public int AttackBonus, NativeWeaponId;
        public long ModuleBase, Allocation;
        public string Version = Profile.Version;
        internal Report(string state, string message, int pid, bool readOnly)
        { State = state; Message = message; Pid = pid; ReadOnly = readOnly; }
    }

    internal static class MemoryReader
    {
        // Payloads can exceed one page. Keep every native read bounded and
        // reject incomplete chunks before recognition or write verification.
        internal static byte[] Read(long address, int length, Func<long, int, byte[]> readChunk)
        {
            const long limit = 0x0000800000000000L;
            if (length < 1 || length > 0x2000 || address < 0x10000 || address > limit - length)
                throw new InvalidOperationException("读取超出工具允许范围。");
            byte[] result = new byte[length];
            for (int offset = 0; offset < length; offset += 0x1000)
            {
                int size = Math.Min(0x1000, length - offset);
                byte[] chunk = readChunk(address + offset, size);
                if (chunk == null || chunk.Length != size)
                    throw new IOException("游戏数据未完整读取。");
                Buffer.BlockCopy(chunk, 0, result, offset, size);
            }
            return result;
        }
    }

    internal sealed class Game : IDisposable
    {
        private readonly Process process;
        private IntPtr handle;
        private readonly bool writable;
        private long privateAllocation;
        internal readonly long Base;
        internal readonly int Pid;

        internal Game(bool writable)
        {
            if (IntPtr.Size != 8) throw new InvalidOperationException("此工具需要 Windows 64 位系统。");
            Process[] found = Process.GetProcessesByName("nioh");
            if (found.Length != 1)
            {
                foreach (Process item in found) item.Dispose();
                throw new InvalidOperationException(found.Length == 0 ? "请先从 Steam 启动《仁王》，停在 NEW GAME / CONTINUE 主菜单，再点“重新检查”。" : "检测到多个《仁王》进程，请只保留一个。");
            }
            process = found[0];
            try
            {
                Pid = process.Id;
                ProcessModule module = process.MainModule;
                Base = module.BaseAddress.ToInt64();
                if (module.ModuleMemorySize != Profile.ImageSize) throw new InvalidOperationException("游戏版本不匹配。本工具只支持已核对的 Steam 1.24.8。");
                string digest;
                using (FileStream file = new FileStream(module.FileName, FileMode.Open, FileAccess.Read, FileShare.Read))
                using (SHA256 sha = SHA256.Create()) digest = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
                if (digest != Profile.Sha256) throw new InvalidOperationException("游戏程序不匹配。本工具只支持已核对的 Steam 1.24.8。");
                this.writable = writable;
                uint access = Native.Query | Native.ReadMemory | (writable ? Native.WriteMemory | Native.Operation : 0);
                handle = Native.OpenProcess(access, false, Pid);
                if (handle == IntPtr.Zero) throw Native.Error("无法连接游戏。");
                VerifyHeader();
                Alive();
            }
            catch { Dispose(); throw; }
        }

        internal byte[] Read(long address, int length)
        {
            return MemoryReader.Read(address, length, delegate(long at, int size)
            {
                byte[] bytes = new byte[size];
                UIntPtr count;
                if (!Native.ReadProcessMemory(handle, new IntPtr(at), bytes, (UIntPtr)size, out count)) throw Native.Error("游戏内存读取失败。");
                if (count.ToUInt64() != (ulong)size) throw new InvalidOperationException("游戏数据未完整读取。");
                return bytes;
            });
        }

        private void Alive()
        {
            uint code;
            if (!Native.GetExitCodeProcess(handle, out code)) throw Native.Error("无法确认游戏状态。");
            if (code != 259 || process.HasExited) throw new InvalidOperationException("游戏已经退出，请重新启动后运行工具。");
        }

        private void VerifyHeader()
        {
            byte[] bytes = Read(Base, 0x1000);
            int nt = BitConverter.ToInt32(bytes, 0x3C);
            if (bytes[0] != 'M' || bytes[1] != 'Z' || nt < 0x40 || nt + 88 > bytes.Length ||
                BitConverter.ToUInt32(bytes, nt) != 0x00004550 ||
                BitConverter.ToUInt16(bytes, nt + 4) != 0x8664 ||
                BitConverter.ToUInt32(bytes, nt + 8) != Profile.Timestamp ||
                BitConverter.ToUInt32(bytes, nt + 80) != Profile.ImageSize)
                throw new InvalidOperationException("运行中的游戏程序与工具不匹配。");
            if (!Checks.Equal(Read(Base + Profile.LookupRva, Profile.LookupBytes.Length), Profile.LookupBytes))
                throw new InvalidOperationException("人物查询代码已被修改，停止接入。");
        }

        private long Player() { return BitConverter.ToInt64(Read(Base + Profile.PlayerSlotRva, 8), 0); }

        private void Write(long address, byte[] bytes, bool code)
        {
            if (!writable) throw new InvalidOperationException("只读检查不能修改游戏。");
            bool site = false;
            foreach (HookSpec hook in Profile.Hooks) site |= address == Base + hook.Rva && bytes.Length == hook.Original.Length;
            bool own = privateAllocation != 0 && address >= privateAllocation && address + bytes.Length <= privateAllocation + Profile.AllocationSize;
            if ((code && !site) || (!code && !own)) throw new InvalidOperationException("写入目标超出允许范围。");
            uint protection = 0;
            if (code && !Native.VirtualProtectEx(handle, new IntPtr(address), (UIntPtr)bytes.Length, Native.ExecuteReadWrite, out protection)) throw Native.Error("无法准备游戏代码。");
            try
            {
                UIntPtr count;
                if (!Native.WriteProcessMemory(handle, new IntPtr(address), bytes, (UIntPtr)bytes.Length, out count)) throw Native.Error("接入游戏失败。");
                if (count.ToUInt64() != (ulong)bytes.Length || !Checks.Equal(Read(address, bytes.Length), bytes)) throw new InvalidOperationException("写入核对失败。");
                if (code && !Native.FlushInstructionCache(handle, new IntPtr(address), (UIntPtr)bytes.Length)) throw Native.Error("无法刷新游戏代码。");
            }
            finally
            {
                if (code)
                {
                    uint ignored;
                    if (!Native.VirtualProtectEx(handle, new IntPtr(address), (UIntPtr)bytes.Length, protection, out ignored)) throw Native.Error("无法恢复代码页保护。");
                }
            }
        }

        internal Report Inspect()
        {
            Alive();
            long allocation;
            HookState state = Checks.Inspect(Read, Base, out allocation);
            if (state == HookState.Legacy) return new Report("needs_restart", "已识别完整的旧版接入（包括 Beta 5.3）。请退出并重新启动游戏，停在主菜单后使用 Beta 5.3.1。", Pid, true);
            if (state == HookState.Other) return new Report("modified", "相关游戏代码已被其他工具修改。请关闭其他 CT 或工具，并重新启动游戏。", Pid, true);
            long actor = Player();
            if (state == HookState.Ours)
            {
                Report result = new Report("enabled", "本次游戏已启用飞缘魔。可以关闭工具，继续游玩。", Pid, true);
                result.ModuleBase = Base; result.Allocation = allocation;
                byte[] data = Read(allocation + Profile.DataOffset, Profile.RevenantInteraction ? 0xD0 : Profile.WeaponHudRefreshView ? 0xB8 : Profile.WeaponHudView ? 0xA4 : Profile.WeaponStatsOverlay ? 0xA0 : Profile.AttributeOverlay ? 0x90 : 0x58);
                result.SelectedTemplate = BitConverter.ToUInt32(data, 0);
                result.SelectedCharacter = CharacterSelection.Name(result.SelectedTemplate);
                result.Starts = BitConverter.ToUInt32(data, 0x34);
                result.QueuedDoorStarts = BitConverter.ToUInt32(data, 0x40);
                result.CameraSuppressions = BitConverter.ToUInt32(data, 0x44);
                result.FragmentUses = BitConverter.ToUInt32(data, 0x48);
                result.KodamaStarts = BitConverter.ToUInt32(data, 0x4C);
                result.ConsumableUses = BitConverter.ToUInt32(data, 0x50);
                result.LastConsumableId = BitConverter.ToUInt32(data, 0x54);
                if (Profile.AttributeOverlay)
                {
                    result.AttributesEnabled = data[0x58] == 1;
                    result.AttributeInitializations = BitConverter.ToUInt32(data, 0x5C);
                    result.AttributeRecalculations = BitConverter.ToUInt32(data, 0x60);
                    result.BossHp = BitConverter.ToUInt32(data, 0x64);
                    result.HpBonus = BitConverter.ToUInt32(data, 0x68);
                    result.BossKi = BitConverter.ToUInt32(data, 0x6C);
                    result.KiBonus = BitConverter.ToUInt32(data, 0x70);
                    result.BossDefense = BitConverter.ToUInt32(data, 0x74);
                    result.DefenseBonus = BitConverter.ToUInt32(data, 0x78);
                }
                if (Profile.WeaponStatsOverlay)
                {
                    result.BossAttack = BitConverter.ToUInt32(data, 0x7C);
                    result.AttackBonus = BitConverter.ToInt32(data, 0x80);
                    result.SelectedMeleeSlot = BitConverter.ToUInt32(data, 0x8C);
                    result.NativeWeaponAttack = BitConverter.ToUInt32(data, 0x90);
                    result.NakedReferenceAttack = BitConverter.ToUInt32(data, 0x94);
                    result.NativeWeaponId = BitConverter.ToInt32(data, 0x98);
                    result.WeaponRoutes = BitConverter.ToUInt32(data, 0x9C);
                }
                if (Profile.WeaponHudView)
                    result.WeaponHudUpdates = BitConverter.ToUInt32(data, 0xA0);
                if (Profile.WeaponHudRefreshView)
                {
                    result.WeaponHudRefreshUpdates = BitConverter.ToUInt32(data, 0xA4);
                    result.WeaponHudMeleeSwitchUpdates = BitConverter.ToUInt32(data, 0xA8);
                    result.WeaponHudRangedSwitchUpdates = BitConverter.ToUInt32(data, 0xAC);
                    result.WeaponHudWidget = BitConverter.ToInt64(data, 0xB0);
                }
                if (Profile.RevenantInteraction)
                {
                    result.RevenantStarts = BitConverter.ToUInt32(data, 0xB8);
                    result.RevenantInstance = BitConverter.ToUInt32(data, 0xBC);
                    result.RevenantObject = BitConverter.ToInt64(data, 0xC0);
                    result.RevenantQueuedRequests = BitConverter.ToUInt32(data, 0xC8);
                    result.RevenantHoldFlags = BitConverter.ToUInt32(data, 0xCC);
                }
                if (Profile.YokaiGrab)
                    result.YokaiGrabPasses = BitConverter.ToUInt32(Read(allocation + Profile.DataOffset + 0xF00, 4), 0);
                if (actor != 0) result.Template = BitConverter.ToUInt32(Read(actor, 8), 0).ToString("X8");
                bool william = result.Template == "00000064";
                bool hinoenma = result.Template == "00058E5E" || result.Template == "00051BE1";
                result.CurrentCharacter = actor == 0 ? "等待载入关卡" : william ? "威廉" : hinoenma ? "飞缘魔" : "其他角色";
                result.CharacterChangePending = (william && result.SelectedTemplate != 0) || (hinoenma && result.SelectedTemplate == 0);
                if (actor == 0) result.Message = "下次载入角色为" + result.SelectedCharacter + "。从主菜单继续游戏即可，可以关闭本工具。";
                else if (result.CharacterChangePending) result.Message = "已选择" + result.SelectedCharacter + "。请返回 NEW GAME / CONTINUE 主菜单，再继续游戏，角色切换后生效。";
                else result.Message = "当前角色为" + result.CurrentCharacter + "。可以关闭工具，继续游玩；也可以选择下次载入的角色。";
                return result;
            }
            if (actor != 0) return new Report("needs_menu", "请先返回 NEW GAME / CONTINUE 主菜单，再点“重新检查”。人物替换需要重新载入关卡。", Pid, true);
            return new Report("ready", "请确保已停在 NEW GAME / CONTINUE 主菜单。", Pid, true);
        }

        internal Report SelectCharacter(uint selection, Report expected)
        {
            if (!writable) throw new InvalidOperationException("只读检查不能切换角色。");
            if (!CharacterSelection.Supported(selection)) throw new InvalidOperationException("角色选择无效。");
            Report before = Inspect();
            if (before.State != "enabled") return before;
            if (expected.Pid != Pid || expected.ModuleBase != Base || expected.Allocation != before.Allocation)
                throw new InvalidOperationException("游戏进程已变化，请重新检查。");
            privateAllocation = before.Allocation;
            bool changed;
            using (GameThreads threads = new GameThreads(Pid, Base))
            {
                Alive(); VerifyHeader();
                changed = CharacterSelection.Apply(Read,
                    delegate(long address, byte[] bytes) { Write(address, bytes, false); },
                    Base, privateAllocation, selection);
            }
            Report result = Inspect();
            if (result.State != "enabled" || result.SelectedTemplate != selection)
                throw new InvalidOperationException("角色选择后的检查未通过，请重新检查。");
            result.ReadOnly = !changed;
            return result;
        }

        internal Report Enable()
        {
            if (!writable) throw new InvalidOperationException("只读检查不能启用替换。");
            Report before = Inspect();
            if (before.State != "ready") return before;
            bool linked = false;
            try
            {
                List<MemorySpan> codePages = Checks.CodePages(Profile.Hooks, Profile.AllocationSize, Profile.ProtectedDataPages);
                long start = Checks.FirstAllocation(Base);
                for (int index = 0; index < 512; index++)
                {
                    IntPtr allocated = Native.VirtualAllocEx(handle, new IntPtr(start + index * 0x10000L), (UIntPtr)Profile.AllocationSize, Native.CommitReserve, Native.ReadWrite);
                    if (allocated != IntPtr.Zero) { privateAllocation = allocated.ToInt64(); break; }
                }
                if (privateAllocation == 0) throw new InvalidOperationException("无法分配接入内存，请重新启动游戏后再试。");
                foreach (HookSpec hook in Profile.Hooks) Write(privateAllocation + hook.CodeOffset, hook.Payload(Base, privateAllocation), false);
                byte[] data = new byte[0x1000];
                Buffer.BlockCopy(BitConverter.GetBytes((uint)0x58E5E), 0, data, 0, 4);
                data[0x2A] = 2;
                data[0x58] = Profile.AttributeOverlay ? (byte)1 : (byte)0;
                Write(privateAllocation + Profile.DataOffset, data, false);
                uint old;
                // Core data, paired-grab scratch, and innate-cache pages stay
                // RW. Validate complete capacities before protecting code.
                foreach (MemorySpan span in codePages)
                {
                    UIntPtr length = (UIntPtr)(span.End - span.Start);
                    if (!Native.VirtualProtectEx(handle, new IntPtr(privateAllocation + span.Start), length, Native.ExecuteRead, out old))
                        throw Native.Error("无法准备扩展工具代码。");
                    if (!Native.FlushInstructionCache(handle, new IntPtr(privateAllocation + span.Start), length))
                        throw Native.Error("无法刷新扩展工具代码。");
                }
                using (GameThreads threads = new GameThreads(Pid, Base, handle, Read))
                {
                    Alive();
                    VerifyHeader();
                    long ignored;
                    if (Player() != 0 || Checks.Inspect(Read, Base, out ignored) != HookState.Original)
                        throw new InvalidOperationException("游戏状态已经变化。请停在主菜单后重新检查。");
                    linked = true;
                    PatchTransaction.Install(Base, privateAllocation,
                        delegate(HookSpec hook, byte[] bytes) { Write(Base + hook.Rva, bytes, true); });
                }
                Report result = Inspect();
                if (result.State != "enabled") throw new InvalidOperationException("接入后的检查未通过，请重启游戏再试。");
                result.ReadOnly = false;
                result.Message = "飞缘魔已接入。现在从主菜单载入关卡即可，可以关闭本工具。";
                return result;
            }
            finally
            {
                // Once a site has pointed to the private allocation, retain it
                // until game exit so no resumed thread can enter freed memory.
                if (!linked && privateAllocation != 0)
                {
                    Native.VirtualFreeEx(handle, new IntPtr(privateAllocation), UIntPtr.Zero, Native.Release);
                    privateAllocation = 0;
                }
            }
        }

        public void Dispose()
        {
            if (handle != IntPtr.Zero) { Native.CloseHandle(handle); handle = IntPtr.Zero; }
            if (process != null) process.Dispose();
        }
    }
}
