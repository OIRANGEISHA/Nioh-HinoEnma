using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Collections.Generic;

namespace HinoEnmaTool
{
    internal static class Native
    {
        internal const uint Query = 0x1000, ReadMemory = 0x10, WriteMemory = 0x20, Operation = 0x08;
        internal const uint CommitReserve = 0x3000, Release = 0x8000, ReadWrite = 0x04, ExecuteRead = 0x20, ExecuteReadWrite = 0x40;

        [DllImport("kernel32.dll", SetLastError=true)] internal static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] data, UIntPtr size, out UIntPtr count);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool WriteProcessMemory(IntPtr process, IntPtr address, byte[] data, UIntPtr size, out UIntPtr count);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern IntPtr VirtualAllocEx(IntPtr process, IntPtr address, UIntPtr size, uint allocationType, uint protection);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool VirtualFreeEx(IntPtr process, IntPtr address, UIntPtr size, uint freeType);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool VirtualProtectEx(IntPtr process, IntPtr address, UIntPtr size, uint protection, out uint oldProtection);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool FlushInstructionCache(IntPtr process, IntPtr address, UIntPtr size);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool GetExitCodeProcess(IntPtr process, out uint code);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern IntPtr CreateToolhelp32Snapshot(uint flags, int pid);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool Thread32First(IntPtr snapshot, ref ThreadEntry entry);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool Thread32Next(IntPtr snapshot, ref ThreadEntry entry);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern IntPtr OpenThread(uint access, bool inherit, uint id);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern uint SuspendThread(IntPtr thread);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern uint ResumeThread(IntPtr thread);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool GetThreadContext(IntPtr thread, IntPtr context);
        [DllImport("kernel32.dll", SetLastError=true)] internal static extern UIntPtr VirtualQueryEx(IntPtr process, IntPtr address, ref MemoryRegion region, UIntPtr size);

        [StructLayout(LayoutKind.Sequential)] internal struct MemoryRegion
        {
            internal IntPtr Base, AllocationBase;
            internal uint AllocationProtection;
            internal UIntPtr Size;
            internal uint State, Protection, Type;
        }

        [StructLayout(LayoutKind.Sequential)] internal struct ThreadEntry
        {
            internal uint Size, Usage, Id, Owner;
            internal int BasePriority, DeltaPriority;
            internal uint Flags;
        }

        internal static Exception Error(string action)
        {
            int code = Marshal.GetLastWin32Error();
            if (code == 5) return new InvalidOperationException("无法访问游戏。请关闭本工具，再右键选择“以管理员身份运行”。");
            return new Win32Exception(code, action);
        }
    }

    internal static class ThreadInstallGuard
    {
        // Native clip capture and the later scale read share a local stack slot.
        // A caller stopped before capture must never resume into the new reader.
        internal const uint SamplerRva = 0x954670U, SamplerLength = 0x139U;

        // Owned native function ranges for the eleven map-preview entries.
        // BaseMode includes the new aura call and its split failure epilogue.
        // A nested native call can retain
        // one of these returns even while its current instruction is elsewhere.
        internal static readonly MemorySpan[] MenuNativeFrames = new MemorySpan[] {
            new MemorySpan(0x8C5330,0x8C61F3),
            new MemorySpan(0x75FC80,0x761098), new MemorySpan(0x7C7EB0,0x7C9592),
            new MemorySpan(0x952F20,0x9533AD), new MemorySpan(0x70ECE0,0x710A0C),
            new MemorySpan(0x757206,0x757268), new MemorySpan(0x855250,0x8584A4),
            new MemorySpan(0x850A20,0x850B04),
            new MemorySpan(0xC448E0,0xC44907), new MemorySpan(0xC449A0,0xC453BA),
            new MemorySpan(0xC002C0,0xC002C3) };

        internal static bool InNativeSpan(long address, long moduleBase)
        {
            if (address >= moduleBase + SamplerRva && address < moduleBase + SamplerRva + SamplerLength)
                return true;
            foreach (MemorySpan span in MenuNativeFrames)
                if (address >= moduleBase + span.Start && address < moduleBase + span.End)
                    return true;
            foreach (HookSpec hook in Profile.Hooks)
                if (address >= moduleBase + hook.Rva && address < moduleBase + hook.Rva + hook.Original.Length)
                    return true;
            return false;
        }

        internal static void VerifySavedReturnBytes(byte[] bytes, long moduleBase)
        {
            if (bytes == null || bytes.Length == 0 || bytes.Length % 8 != 0)
                throw new InvalidOperationException("游戏线程堆栈未完整读取，停止接入。");
            for (int offset = 0; offset < bytes.Length; offset += 8)
                if (InNativeSpan(BitConverter.ToInt64(bytes, offset), moduleBase))
                    throw new InvalidOperationException("游戏正在载入或等待返回，请停在主菜单后重新检查。");
        }
    }

    internal sealed class GameThreads : IDisposable
    {
        private readonly List<IntPtr> handles = new List<IntPtr>();
        private readonly HashSet<uint> ids = new HashSet<uint>();

        private static List<uint> Find(int pid)
        {
            IntPtr snapshot = Native.CreateToolhelp32Snapshot(4, 0);
            if (snapshot == new IntPtr(-1)) throw Native.Error("无法检查游戏线程。");
            try
            {
                List<uint> found = new List<uint>();
                Native.ThreadEntry item = new Native.ThreadEntry();
                item.Size = (uint)Marshal.SizeOf(typeof(Native.ThreadEntry));
                bool next = Native.Thread32First(snapshot, ref item);
                while (next)
                {
                    if (item.Owner == (uint)pid) found.Add(item.Id);
                    next = Native.Thread32Next(snapshot, ref item);
                }
                if (Marshal.GetLastWin32Error() != 18) throw Native.Error("游戏线程列表读取失败。");
                return found;
            }
            finally { Native.CloseHandle(snapshot); }
        }

        internal GameThreads(int pid, long moduleBase)
            : this(pid, moduleBase, IntPtr.Zero, null) { }

        internal GameThreads(int pid, long moduleBase, IntPtr process, Func<long, int, byte[]> read)
        {
            try
            {
                bool stable = false;
                for (int pass = 0; pass < 4; pass++)
                {
                    bool added = false;
                    foreach (uint id in Find(pid))
                    {
                        if (ids.Contains(id)) continue;
                        IntPtr handle = Native.OpenThread(0x0002 | 0x0008, false, id);
                        if (handle == IntPtr.Zero) throw Native.Error("无法暂停游戏线程。");
                        if (Native.SuspendThread(handle) == uint.MaxValue)
                        {
                            Native.CloseHandle(handle);
                            throw Native.Error("无法暂停游戏线程。");
                        }
                        handles.Add(handle);
                        ids.Add(id);
                        added = true;
                    }
                    if (!added) { stable = true; break; }
                }
                if (!stable || handles.Count == 0) throw new InvalidOperationException("游戏正在切换状态，请停在主菜单后重新检查。");
                foreach (IntPtr handle in handles)
                {
                    long[] control = ControlPointers(handle);
                    if (ThreadInstallGuard.InNativeSpan(control[0], moduleBase))
                        throw new InvalidOperationException("游戏正在载入，请停在主菜单后重新检查。");
                    if (read != null) VerifySavedReturns(process, control[1], moduleBase, read);
                }
            }
            catch { Dispose(); throw; }
        }

        private static long[] ControlPointers(IntPtr thread)
        {
            // AMD64 CONTEXT is 1232 bytes, aligned to 16 bytes; control flags
            // are at offset 48, Rsp at 152 and Rip at 248 (WinNT.h layout).
            IntPtr raw = Marshal.AllocHGlobal(1232 + 15);
            IntPtr aligned = new IntPtr((raw.ToInt64() + 15) & ~15L);
            try
            {
                Marshal.Copy(new byte[1232], 0, aligned, 1232);
                Marshal.WriteInt32(aligned, 48, 0x100001);
                if (!Native.GetThreadContext(thread, aligned)) throw Native.Error("无法核对游戏线程位置。");
                return new long[] { Marshal.ReadInt64(aligned, 248), Marshal.ReadInt64(aligned, 152) };
            }
            finally { Marshal.FreeHGlobal(raw); }
        }

        private static void VerifySavedReturns(IntPtr process, long rsp, long moduleBase, Func<long, int, byte[]> read)
        {
            Native.MemoryRegion region = new Native.MemoryRegion();
            UIntPtr size = (UIntPtr)Marshal.SizeOf(typeof(Native.MemoryRegion));
            if (process == IntPtr.Zero || Native.VirtualQueryEx(process, new IntPtr(rsp), ref region, size) != size)
                throw new InvalidOperationException("无法核对游戏线程返回位置，停止接入。");
            long begin = region.Base.ToInt64();
            ulong regionSize = region.Size.ToUInt64();
            if (rsp < 0x10000 || rsp % 8 != 0 || regionSize > long.MaxValue || begin > long.MaxValue - (long)regionSize)
                throw new InvalidOperationException("游戏线程堆栈范围异常，停止接入。");
            long end = begin + (long)regionSize;
            if (region.State != 0x1000 || (region.Protection & (0x100U | 1U)) != 0 ||
                begin > rsp || end <= rsp || end - rsp > 0x100000)
                throw new InvalidOperationException("游戏线程堆栈不适合核对，停止接入。");
            long alignedEnd = end - (end - rsp) % 8;
            for (long at = rsp; at < alignedEnd; at += 0x1000)
            {
                int length = (int)Math.Min(0x1000L, alignedEnd - at);
                byte[] bytes = read(at, length);
                if (bytes == null || bytes.Length != length)
                    throw new InvalidOperationException("游戏线程堆栈未完整读取，停止接入。");
                ThreadInstallGuard.VerifySavedReturnBytes(bytes, moduleBase);
            }
        }

        public void Dispose()
        {
            for (int index = handles.Count - 1; index >= 0; index--)
            {
                Native.ResumeThread(handles[index]);
                Native.CloseHandle(handles[index]);
            }
            handles.Clear();
        }
    }
}
