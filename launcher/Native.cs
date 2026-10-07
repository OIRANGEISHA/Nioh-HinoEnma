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
                    long rip = InstructionPointer(handle);
                    foreach (HookSpec hook in Profile.Hooks)
                        if (rip >= moduleBase + hook.Rva && rip < moduleBase + hook.Rva + hook.Original.Length)
                            throw new InvalidOperationException("游戏正在载入，请停在主菜单后重新检查。");
                }
            }
            catch { Dispose(); throw; }
        }

        private static long InstructionPointer(IntPtr thread)
        {
            // AMD64 CONTEXT is 1232 bytes, aligned to 16 bytes; control flags
            // are at offset 48 and Rip at offset 248 (WinNT.h layout).
            IntPtr raw = Marshal.AllocHGlobal(1232 + 15);
            IntPtr aligned = new IntPtr((raw.ToInt64() + 15) & ~15L);
            try
            {
                Marshal.Copy(new byte[1232], 0, aligned, 1232);
                Marshal.WriteInt32(aligned, 48, 0x100001);
                if (!Native.GetThreadContext(thread, aligned)) throw Native.Error("无法核对游戏线程位置。");
                return Marshal.ReadInt64(aligned, 248);
            }
            finally { Marshal.FreeHGlobal(raw); }
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
