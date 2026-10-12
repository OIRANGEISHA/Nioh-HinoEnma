using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;

namespace HinoEnmaTool
{
    internal static class SelfTests
    {
        private sealed class FakeMemory
        {
            internal readonly Dictionary<long, byte[]> Blocks = new Dictionary<long, byte[]>();
            internal byte[] Read(long at, int size)
            {
                foreach (KeyValuePair<long, byte[]> block in Blocks)
                {
                    if (at < block.Key || at + size > block.Key + block.Value.Length) continue;
                    byte[] result = new byte[size];
                    Buffer.BlockCopy(block.Value, (int)(at - block.Key), result, 0, size);
                    return result;
                }
                throw new InvalidOperationException("Self-test requested an unmapped address.");
            }
            internal void Write(long at, byte[] bytes)
            {
                foreach (KeyValuePair<long, byte[]> block in Blocks)
                    if (at >= block.Key && at + bytes.Length <= block.Key + block.Value.Length)
                    { Buffer.BlockCopy(bytes, 0, block.Value, (int)(at - block.Key), bytes.Length); return; }
                throw new InvalidOperationException("Self-test write requested an unmapped address.");
            }
        }

        private const long Module = 0x140000000;
        private static long Allocation { get { return Checks.FirstAllocation(Module); } }

        private static FakeMemory Memory(bool patched)
        {
            FakeMemory memory = new FakeMemory();
            foreach (HookSpec hook in Profile.Hooks)
            {
                memory.Blocks[Module + hook.Rva] = patched ? hook.Jump(Module, Allocation) : (byte[])hook.Original.Clone();
                memory.Blocks[Allocation + hook.CodeOffset] = hook.Payload(Module, Allocation);
            }
            byte[] data = new byte[0x40];
            Buffer.BlockCopy(BitConverter.GetBytes((uint)0x58E5E), 0, data, 0, 4);
            data[0x2A] = 2;
            memory.Blocks[Allocation + Profile.DataOffset] = data;
            return memory;
        }

        private static FakeMemory LegacyMemory(LegacyProfile previous)
        {
            FakeMemory memory = new FakeMemory();
            foreach (HookSpec current in Profile.Hooks)
                memory.Blocks[Module + current.Rva] = (byte[])current.Original.Clone();
            foreach (HookSpec old in previous.Hooks)
            {
                memory.Blocks[Module + old.Rva] = old.Jump(Module, Allocation);
                memory.Blocks[Allocation + old.CodeOffset] = old.Payload(Module, Allocation);
            }
            byte[] data = new byte[0x40];
            Buffer.BlockCopy(BitConverter.GetBytes((uint)0x58E5E), 0, data, 0, 4);
            data[0x2A] = 2;
            memory.Blocks[Allocation + previous.DataOffset] = data;
            return memory;
        }

        private static void Require(bool value, string detail)
        { if (!value) throw new InvalidOperationException(detail); }

        internal static int Run(string path)
        {
            List<string> passed = new List<string>();
            Action<string, Action> test = delegate(string name, Action body) { body(); passed.Add(name); };
            try
            {
                test("installation checks complete sampler and menu native frames and saved returns", delegate
                {
                    long begin = Module + ThreadInstallGuard.SamplerRva;
                    long end = begin + ThreadInstallGuard.SamplerLength;
                    Require(!ThreadInstallGuard.InNativeSpan(begin-1,Module) &&
                        ThreadInstallGuard.InNativeSpan(begin,Module) &&
                        ThreadInstallGuard.InNativeSpan(Module+0x9547A8,Module) &&
                        !ThreadInstallGuard.InNativeSpan(end,Module),"Whole sampler frame boundaries");
                    byte[] harmless = new byte[16];
                    Buffer.BlockCopy(BitConverter.GetBytes(begin-1),0,harmless,0,8);
                    Buffer.BlockCopy(BitConverter.GetBytes(end),0,harmless,8,8);
                    ThreadInstallGuard.VerifySavedReturnBytes(harmless,Module);
                    Require(ThreadInstallGuard.MenuNativeFrames.Length==11,"Exact menu frame inventory including aura and cold-start loading dependencies");
                    Require(ThreadInstallGuard.InNativeSpan(Module+0x8C59B4,Module),"Saved return after the displaced aura update must reject installation");
                    foreach(MemorySpan span in ThreadInstallGuard.MenuNativeFrames)
                    {
                        long first=Module+span.Start,last=Module+span.End;
                        Require(first<last && ThreadInstallGuard.InNativeSpan(first,Module) &&
                            ThreadInstallGuard.InNativeSpan(last-1,Module),"Complete menu native frame");
                        Require(!ThreadInstallGuard.InNativeSpan(first-1,Module) &&
                            !ThreadInstallGuard.InNativeSpan(last,Module),"Exact menu frame boundaries");
                        foreach(long address in new long[] {first,first+(last-first)/2,last-1})
                        {
                            bool rejected=false;
                            try { ThreadInstallGuard.VerifySavedReturnBytes(BitConverter.GetBytes(address),Module); }
                            catch(InvalidOperationException) { rejected=true; }
                            Require(rejected,"Nested menu return into changed native function rejected");
                        }
                    }
                    Require(ThreadInstallGuard.ExecutionNativeFrames.Length==10,"Exact execution native frame inventory");
                    foreach(MemorySpan span in ThreadInstallGuard.ExecutionNativeFrames)
                    {
                        long first=Module+span.Start,last=Module+span.End;
                        Require(first<last && ThreadInstallGuard.InNativeSpan(first,Module) &&
                            ThreadInstallGuard.InNativeSpan(last-1,Module),"Complete execution native frame");
                        foreach(long address in new long[] {first,first+(last-first)/2,last-1})
                        {
                            bool rejected=false;
                            try { ThreadInstallGuard.VerifySavedReturnBytes(BitConverter.GetBytes(address),Module); }
                            catch(InvalidOperationException) { rejected=true; }
                            Require(rejected,"Nested execution return into changed native function rejected");
                        }
                    }
                    Require(ThreadInstallGuard.InNativeSpan(Module+0x216ADD,Module) &&
                        ThreadInstallGuard.InNativeSpan(Module+0x7DED33,Module),"Late geometry exit and original nested return guarded");
                    MemorySpan queryFrame=ThreadInstallGuard.ExecutionNativeFrames[9];
                    Require(queryFrame.Start==0x736CB0 && queryFrame.End==0x73AB00,
                        "Complete query dispatch frame including chained unwind fragments");
                    Require(!ThreadInstallGuard.InNativeSpan(Module+queryFrame.Start-1,Module) &&
                        !ThreadInstallGuard.InNativeSpan(Module+queryFrame.End,Module),
                        "Exact query dispatch frame boundaries");
                    foreach(long address in new long[] {begin, Module+0x95470C, end-1, Module+Profile.Hooks[0].Rva})
                    {
                        bool rejected=false;
                        try { ThreadInstallGuard.VerifySavedReturnBytes(BitConverter.GetBytes(address),Module); }
                        catch(InvalidOperationException) { rejected=true; }
                        Require(rejected,"Saved return into modified code rejected");
                    }
                    foreach(byte[] malformed in new byte[][] {null,new byte[0],new byte[7]})
                    {
                        bool rejected=false;
                        try { ThreadInstallGuard.VerifySavedReturnBytes(malformed,Module); }
                        catch(InvalidOperationException) { rejected=true; }
                        Require(rejected,"Incomplete stack scan rejected");
                    }
                });
                test("large payload recognition reads bounded complete chunks", delegate
                {
                    byte[] source = Profile.Hooks[38].Payload(Module, Allocation);
                    foreach(HookSpec hook in Profile.Hooks)
                        if(hook.Payload(Module, Allocation).Length > source.Length)
                            source = hook.Payload(Module, Allocation);
                    Require(source.Length > 0x4000 && source.Length <= 0x7000,"Complete common-action carrier payload");
                    int calls = 0, total = 0;
                    byte[] actual = MemoryReader.Read(Allocation, source.Length, delegate(long at, int size)
                    {
                        Require(at == Allocation + total && size > 0 && size <= 0x1000,"Sequential bounded read");
                        byte[] chunk = new byte[size]; Buffer.BlockCopy(source,total,chunk,0,size);
                        total += size; calls++; return chunk;
                    });
                    Require(calls == (source.Length+0xFFF)/0x1000 && total == source.Length && Checks.Equal(actual,source),"Every payload byte preserved");
                });
                test("memory reader rejects invalid ranges and incomplete later chunks", delegate
                {
                    foreach(long at in new long[]{0xFFFF,0x0000800000000000L-3,long.MaxValue})
                    {
                        bool rejected=false;
                        try { MemoryReader.Read(at,4,delegate(long a,int n){throw new Exception("Unvalidated native read");}); }
                        catch(InvalidOperationException){rejected=true;}
                        Require(rejected,"Address boundary guard");
                    }
                    foreach(int length in new int[]{0,-1,0x7001})
                    {
                        bool rejected=false;
                        try { MemoryReader.Read(Allocation,length,delegate(long a,int n){throw new Exception("Unvalidated native read");}); }
                        catch(InvalidOperationException){rejected=true;}
                        Require(rejected,"Length guard");
                    }
                    int calls=0; bool partial=false;
                    try { MemoryReader.Read(Allocation,0x16CD,delegate(long a,int n){calls++;return new byte[calls==2?n-1:n];}); }
                    catch(IOException){partial=true;}
                    Require(partial && calls==2,"Later partial chunk refused");
                });
                test("pristine instructions recognized", delegate
                { long a; Require(Checks.Inspect(Memory(false).Read, Module, out a) == HookState.Original, "Original state"); });
                test("current profile recognized without reinjection", delegate
                { long a; Require(Checks.Inspect(Memory(true).Read, Module, out a) == HookState.Ours && a == Allocation, "Own state"); });
                test("complete Beta 5.1 and Hotfix 1 remain read-only restart identities", delegate
                {
                    Require(Profile.Hooks.Length==82 && Profile.LegacyProfiles.Length==9,"Complete local and prior release identities");
                    int index=0; int[] counts={55,59,60,70,71,71,80,81,81}; int[] allocations={0x19000,0x1B000,0x20000,0x2D000,0x36000,0x36000,0x43000,0x43000,0x51000};
                    foreach(LegacyProfile previous in Profile.LegacyProfiles)
                    {
                        Require(previous.Hooks.Length==counts[index],"Complete prior hook list");
                        Require(previous.DataOffset==0xF000 && previous.AllocationSize==allocations[index++],"Prior allocation preserved");
                        FakeMemory memory=LegacyMemory(previous); long allocation;
                        Require(Checks.Inspect(memory.Read,Module,out allocation)==HookState.Legacy && allocation==Allocation,"Exact prior identity");
                        bool wrote=false,rejected=false;
                        try { CharacterSelection.Apply(memory.Read,delegate(long at,byte[] bytes){wrote=true;},Module,Allocation,0); }
                        catch(InvalidOperationException){rejected=true;}
                        Require(rejected && !wrote,"Prior process never receives character writes");
                    }
                });
                test("every historical payload and site is required and mixed new entries are refused", delegate
                {
                    foreach(LegacyProfile previous in Profile.LegacyProfiles)
                    {
                        foreach(HookSpec old in previous.Hooks)
                        {
                            FakeMemory changedPayload=LegacyMemory(previous),changedSite=LegacyMemory(previous); long allocation;
                            changedPayload.Blocks[Allocation+old.CodeOffset][0]^=1;
                            changedSite.Blocks[Module+old.Rva][old.Original.Length-1]^=1;
                            Require(Checks.Inspect(changedPayload.Read,Module,out allocation)==HookState.Other,"Changed prior payload: "+old.Name);
                            Require(Checks.Inspect(changedSite.Read,Module,out allocation)==HookState.Other,"Changed prior site: "+old.Name);
                        }
                        foreach(HookSpec current in Profile.Hooks)
                        {
                            bool existed=false;
                            foreach(HookSpec old in previous.Hooks) existed|=old.Rva==current.Rva;
                            if(existed) continue;
                            FakeMemory mixed=LegacyMemory(previous); long allocation;
                            mixed.Write(Module+current.Rva,current.Jump(Module,Allocation));
                            Require(Checks.Inspect(mixed.Read,Module,out allocation)==HookState.Other,"Mixed native entry: "+current.Name);
                        }
                    }
                });
                test("code protection excludes every gameplay and menu writable page", delegate
                {
                    Require(Profile.AllocationSize==0x69000 && Profile.DataOffset==0xF000 && Profile.ProtectedDataPages.Length==23,"Complete player lifetime protected layout");
                    int[] starts={0xF000,0x13000,0x1F000,0x24000,0x29000,0x2C000,0x35000,0x42000,0x44000,0x53000,0x54000,0x55000,0x56000,0x57000,0x58000,0x59000,0x5A000,0x5B000,0x5C000,0x5D000,0x5E000,0x5F000,0x60000};
                    List<MemorySpan> spans=Checks.CodePages(Profile.Hooks,Profile.AllocationSize,Profile.ProtectedDataPages);
                    foreach(HookSpec hook in Profile.Hooks)
                    {
                        bool covered=false;
                        foreach(MemorySpan span in spans)
                            covered|=span.Start<=hook.CodeOffset && span.End>=hook.CodeOffset+hook.CodeCapacity;
                        Require(covered,"Every code capacity receives RX protection");
                    }
                    for(int index=0;index<starts.Length;index++)
                    {
                        MemorySpan data=Profile.ProtectedDataPages[index];
                        Require(data.Start==starts[index] && data.End==starts[index]+0x1000,"Exact protected data page");
                        foreach(MemorySpan span in spans)
                            Require(Math.Max(span.Start,data.Start)>=Math.Min(span.End,data.End),"Data page never becomes RX");
                        HookSpec invalid=new HookSpec("data-overlap",0,starts[index],0x400,"kA==","kA==",new Fixup[0]);
                        bool rejected=false;
                        try { Checks.CodePages(new HookSpec[]{invalid},Profile.AllocationSize,Profile.ProtectedDataPages); }
                        catch(InvalidOperationException){rejected=true;}
                        Require(rejected,"Code capacity in protected data rejected");
                    }
                });
                test("post-defeat hooks reject altered payloads and mixed Beta 5 installations", delegate
                {
                    int count = 0;
                    FakeMemory mixed = Memory(true);
                    foreach(HookSpec hook in Profile.Hooks)
                    {
                        if(!hook.Name.StartsWith("HE_PostDefeat", StringComparison.Ordinal)) continue;
                        count++;
                        mixed.Write(Module+hook.Rva,hook.Original);
                        FakeMemory altered = Memory(true);
                        altered.Blocks[Allocation+hook.CodeOffset][0] ^= 1;
                        long observed;
                        Require(Checks.Inspect(altered.Read,Module,out observed)==HookState.Other,
                            "Altered post-defeat payload refused: "+hook.Name);
                    }
                    Require(count==5,"Complete post-defeat hook inventory");
                    long allocation;
                    Require(Checks.Inspect(mixed.Read,Module,out allocation)==HookState.Other,
                        "Prior 50-hook Beta 5 process requires a restart");
                    Require(Checks.Inspect(Memory(true).Read,Module,out allocation)==HookState.Ours,
                        "Complete70-hook local profile recognized");
                });
                test("all eleven menu entries require complete payloads and native sites", delegate
                {
                    string[] names={"HE_MapVisualReadyPrivate","HE_MapVisualSpawnPrivate","HE_MapVisualResourcePrivate","HE_MapVisualRestorePrivate","HE_MapAppearancePrivate","HE_MapNativeIdlePrivate","HE_MapIdleSelectionPrivate","HE_MapLoadoutAppearancePrivate","HE_MapPreviewCameraDistancePrivate","HE_MapPreviewCameraHeightPrivate","HE_MapPreviewAuraCopiedHash"};
                    Require(Profile.Hooks.Length==82,"Exact total execution build inventory");
                    for(int i=60;i<71;i++)
                    {
                        HookSpec hook=Profile.Hooks[i];
                        Require(hook.Name==names[i-60],"Exact scoped menu entry name");
                        foreach(bool payload in new bool[]{true,false})
                        {
                            FakeMemory memory=Memory(true); long observed;
                            byte[] bytes=memory.Blocks[(payload?Allocation+hook.CodeOffset:Module+hook.Rva)];
                            bytes[bytes.Length-1]^=1;
                            Require(Checks.Inspect(memory.Read,Module,out observed)==HookState.Other,"Changed menu code refused");
                        }
                    }
                });
                test("all ten execution entries are required and preserve the previous71 profile", delegate
                {
                    string[] names={"HE_OrochiHeavyTransition","HE_OrochiWeaponBankRead","HE_OrochiWeaponMotionRead","HE_OrochiWeaponMotionPresence","HE_OrochiWeaponEventRead","HE_OrochiWeaponBlendPresence","HE_OrochiWeaponBlendRead","HE_OrochiZeroLengthRay","HE_OrochiStalledInvalidRayExit","HE_OrochiPendingLivingWeaponGuard"};
                    Require(Profile.Hooks.Length==82,"Exact complete execution inventory");
                    for(int i=71;i<81;i++)
                    {
                        HookSpec hook=Profile.Hooks[i];
                        Require(hook.Name==names[i-71],"Exact execution entry identity");
                        foreach(bool payload in new bool[]{true,false})
                        {
                            FakeMemory memory=Memory(true); long observed;
                            byte[] bytes=memory.Blocks[(payload?Allocation+hook.CodeOffset:Module+hook.Rva)];
                            bytes[bytes.Length-1]^=1;
                            Require(Checks.Inspect(memory.Read,Module,out observed)==HookState.Other,"Changed execution code refused");
                        }
                    }
                    Require(Profile.Hooks[71].CodeOffset==0x46000 && Profile.Hooks[71].CodeCapacity==0x4000,
                        "Dual heavy binding payload has its exact bounded code capacity");
                    HookSpec weaponGuard=Profile.Hooks[80];
                    Require(weaponGuard.CodeOffset==0x50000 && weaponGuard.CodeCapacity==0x1000 &&
                        weaponGuard.Rva==0x737769U &&
                        Checks.Equal(weaponGuard.Original,new byte[]{0x48,0x8B,0x41,0x58,0x48,0x8B,0x48,0x20}),
                        "Dual pending Living Weapon guard has exact native entry and bounded code slot");
                    LegacyProfile beta532=Profile.LegacyProfiles[5];
                    Require(beta532.Version=="1.0.0-beta.5.3.2" && beta532.Hooks.Length==71,"Exact previous71 identity");
                    LegacyProfile beta54=Profile.LegacyProfiles[6];
                    Require(beta54.Version=="1.0.0-beta.5.4" && beta54.Hooks.Length==80,"Exact delivered80 identity");
                    Require(!Checks.Equal(Profile.Hooks[71].Template,beta54.Hooks[71].Template),"Restart binding repair differs from delivered Beta5.4");
                    LegacyProfile beta541=Profile.LegacyProfiles[7];
                    Require(beta541.Version=="1.0.0-beta.5.4.1" && beta541.Hooks.Length==81,"Exact published Beta5.4.1 identity");
                    for(int i=0;i<81;i++)
                    {
                        if((i>=71 && i<=77) || i==80 || i==1 || i==8 || i==9 || i==36 || i==37 || i==38 || i==39 || i==70) continue;
                        Require(Checks.Equal(Profile.Hooks[i].Template,beta541.Hooks[i].Template),"Other73 templates preserved from Beta5.4.1");
                    }
                    for(int i=0;i<71;i++)
                    {
                        HookSpec current=Profile.Hooks[i],old=beta532.Hooks[i];
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && current.CodeCapacity==old.CodeCapacity),"Previous hook slot identity");
                        if(i==1 || i==8 || i==9 || i==36 || i==37 || i==38 || i==39 || i==70) continue;
                        Require(Checks.Equal(current.Template,old.Template) && Checks.Equal(current.Original,old.Original) && current.Fixups.Length==old.Fixups.Length,"Previous encoded template");
                        for(int f=0;f<current.Fixups.Length;f++)
                            Require(current.Fixups[f].Offset==old.Fixups[f].Offset && current.Fixups[f].Kind==old.Fixups[f].Kind && current.Fixups[f].Target==old.Fixups[f].Target && current.Fixups[f].Next==old.Fixups[f].Next,"Previous relocation encoding");
                        foreach(long module in new long[]{0x140000000,0x7FF83AA00000,0x7FFA01000000})
                            foreach(int slot in new int[]{0,1,37,511})
                            {
                                long at=Checks.FirstAllocation(module)+slot*0x10000L;
                                Require(Checks.Equal(current.Payload(module,at),old.Payload(module,at)) && Checks.Equal(current.Jump(module,at),old.Jump(module,at)),"Previous relocated payload and site bytes");
                            }
                    }
                });
                test("all original sixty templates fixups and relocated payloads remain identical", delegate
                {
                    LegacyProfile beta52=Profile.LegacyProfiles[2];
                    Require(beta52.Version=="1.0.0-beta.5.2" && beta52.Hooks.Length==60,"Exact published baseline");
                    for(int i=0;i<60;i++)
                    {
                        HookSpec current=Profile.Hooks[i],old=beta52.Hooks[i];
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && current.CodeCapacity==old.CodeCapacity),"Original slot identity");
                        if(i==1 || i==8 || i==9 || i==36 || i==37 || i==38 || i==39) continue;
                        Require(Checks.Equal(current.Template,old.Template) && Checks.Equal(current.Original,old.Original) && current.Fixups.Length==old.Fixups.Length,"Original encoded template");
                        for(int f=0;f<current.Fixups.Length;f++)
                            Require(current.Fixups[f].Offset==old.Fixups[f].Offset && current.Fixups[f].Kind==old.Fixups[f].Kind && current.Fixups[f].Target==old.Fixups[f].Target && current.Fixups[f].Next==old.Fixups[f].Next,"Original relocation encoding");
                        foreach(long module in new long[]{0x140000000,0x7FF83AA00000,0x7FFA01000000})
                            foreach(int slot in new int[]{0,1,37,511})
                            {
                                long at=Checks.FirstAllocation(module)+slot*0x10000L;
                                Require(Checks.Equal(current.Payload(module,at),old.Payload(module,at)) && Checks.Equal(current.Jump(module,at),old.Jump(module,at)),"Original relocated bytes");
                            }
                    }
                });
                test("player lifetime and scoped LW bodies preserve complete Beta542 identity", delegate
                {
                    LegacyProfile old=Profile.LegacyProfiles[8];
                    Require(old.Version=="1.0.0-beta.5.4.2" && old.Hooks.Length==81,"Exact released Beta542 basis");
                    for(int i=0;i<81;i++)
                    {
                        HookSpec current=Profile.Hooks[i],prior=old.Hooks[i];
                        Require(current.Name==prior.Name && current.Rva==prior.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==prior.CodeOffset && current.CodeCapacity==prior.CodeCapacity) && Checks.Equal(current.Original,prior.Original),"Every previous native and scoped private slot identity");
                        bool changed=i==1 || i==8 || i==9 || i==36 || i==37 || i==38 || i==39 || i==70 || (i>=72 && i<=77);
                        Require(Checks.Equal(current.Template,prior.Template)!=changed,"Only scoped fourteen bodies differ");
                        foreach(long module in new long[]{Module,0x7FF83AA00000})
                            foreach(int slot in new int[]{0,37,511})
                            {
                                long at=Checks.FirstAllocation(module)+slot*0x10000L;
                                Require(Checks.Equal(current.Jump(module,at),prior.Jump(module,at))==(i!=36),"Only h36 previous native jump moves");
                                if(!changed) Require(Checks.Equal(current.Payload(module,at),prior.Payload(module,at)),"Other67 relocated payloads preserved");
                            }
                    }
                    HookSpec release=Profile.Hooks[81];
                    Require(release.Name=="HE_PlayerResourceLifetimeCleanup" && release.Rva==0x753616U && release.CodeOffset==0x51000 && release.CodeCapacity==0x2000 && Checks.Equal(release.Original,new byte[]{0x48,0x8B,0x0E,0x48,0x8B,0xD7}),"Exact post-cleanup boundary");
                    foreach(bool payload in new bool[]{true,false})
                    {
                        FakeMemory memory=Memory(true);long at;
                        byte[] bytes=memory.Blocks[payload?Allocation+release.CodeOffset:Module+release.Rva];
                        bytes[bytes.Length-1]^=1;
                        Require(Checks.Inspect(memory.Read,Module,out at)==HookState.Other,"Incomplete lifetime code refused");
                    }
                    Require(ThreadInstallGuard.AbyssNativeFrames.Length==5,"Complete owned lifetime native frames");
                    foreach(MemorySpan span in ThreadInstallGuard.AbyssNativeFrames)
                        foreach(long address in new long[]{Module+span.Start,Module+(span.Start+span.End)/2,Module+span.End-1})
                        {
                            bool rejected=false;
                            try { ThreadInstallGuard.VerifySavedReturnBytes(BitConverter.GetBytes(address),Module); }
                            catch(InvalidOperationException) { rejected=true; }
                            Require(rejected,"Nested return into lifetime/native interaction frame refused");
                        }
                });
                test("unrelated modification rejected", delegate
                { FakeMemory m=Memory(false); m.Blocks[Module+Profile.Hooks[0].Rva][0]=0xCC; long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Other modification"); });
                test("modified private payload rejected", delegate
                { FakeMemory m=Memory(true); m.Blocks[Allocation+Profile.Hooks[2].CodeOffset][1]^=1; long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Altered payload"); });
                test("modified site padding rejected", delegate
                { FakeMemory m=Memory(true); m.Blocks[Module+Profile.Hooks[0].Rva][7]=0xCC; long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Altered padding"); });
                test("unrecognized selected template rejected", delegate
                { FakeMemory m=Memory(true); m.Blocks[Allocation+Profile.DataOffset][0]=0; long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Unknown template"); });
                test("William selection recognized before and after native preload", delegate
                {
                    FakeMemory m=Memory(true);
                    m.Write(Allocation+Profile.DataOffset,BitConverter.GetBytes((uint)0));
                    foreach(uint loaded in new uint[]{0,0x58E5E,0x51BE1})
                    { m.Write(Allocation+Profile.DataOffset+4,BitConverter.GetBytes(loaded)); long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Ours,"William selection state"); }
                });
                test("character selection writes only next-load word and leaves current state", delegate
                {
                    FakeMemory m=Memory(true); byte[] settings=m.Blocks[Allocation+Profile.DataOffset];
                    m.Write(Allocation+Profile.DataOffset+4,BitConverter.GetBytes((uint)0x51BE1));
                    byte[] before=(byte[])settings.Clone(); int writes=0;
                    Require(CharacterSelection.Apply(m.Read,delegate(long at,byte[] value)
                    { Require(at==Allocation+Profile.DataOffset && value.Length==4,"Only selector write"); writes++; m.Write(at,value); },Module,Allocation,0),"Selection changed");
                    Require(writes==1 && BitConverter.ToUInt32(settings,0)==0,"William selected");
                    for(int i=4;i<before.Length;i++) Require(before[i]==settings[i],"Current loaded state preserved");
                    foreach(HookSpec h in Profile.Hooks) Require(Checks.Equal(m.Blocks[Allocation+h.CodeOffset],h.Payload(Module,Allocation)),"Payload unchanged");
                    Require(CharacterSelection.Apply(m.Read,m.Write,Module,Allocation,0x58E5E),"Switch back");
                    Require(Checks.Equal(before,settings),"Round trip preserves settings");
                });
                test("same character selection does not write", delegate
                { FakeMemory m=Memory(true); Require(!CharacterSelection.Apply(m.Read,delegate(long at,byte[] b){throw new IOException("Unexpected write");},Module,Allocation,0x58E5E),"Idempotent selection"); });
                test("unknown character and changed payload rejected before selection write", delegate
                {
                    foreach(bool badTemplate in new bool[]{true,false})
                    {
                        FakeMemory m=Memory(true); if(!badTemplate)m.Blocks[Allocation+Profile.Hooks[1].CodeOffset][0]^=1;
                        bool rejected=false,wrote=false;
                        try { CharacterSelection.Apply(m.Read,delegate(long at,byte[] b){wrote=true;},Module,Allocation,badTemplate?0x64U:0U); }
                        catch(InvalidOperationException){rejected=true;}
                        Require(rejected && !wrote,"No unchecked selection writes");
                    }
                });
                test("partial character write restores previous selection", delegate
                {
                    FakeMemory m=Memory(true); byte[] before=(byte[])m.Blocks[Allocation+Profile.DataOffset].Clone(); bool failed=false,rejected=false;
                    try { CharacterSelection.Apply(m.Read,delegate(long at,byte[] b)
                    { if(!failed){failed=true;m.Blocks[at][0]=0;throw new IOException("Partial selection failure");} m.Write(at,b); },Module,Allocation,0); }
                    catch(IOException){rejected=true;}
                    Require(rejected && Checks.Equal(before,m.Blocks[Allocation+Profile.DataOffset]),"Selection rollback");
                });
                test("character selection readback mismatch is rolled back", delegate
                {
                    FakeMemory m=Memory(true); byte[] before=(byte[])m.Blocks[Allocation+Profile.DataOffset].Clone(); int writes=0; bool rejected=false;
                    try { CharacterSelection.Apply(m.Read,delegate(long at,byte[] b){if(++writes>1)m.Write(at,b);},Module,Allocation,0); }
                    catch(IOException){rejected=true;}
                    Require(rejected && writes==2 && Checks.Equal(before,m.Blocks[Allocation+Profile.DataOffset]),"Readback rollback");
                });
                test("character selection rollback failure is reported", delegate
                {
                    FakeMemory m=Memory(true); bool reported=false;
                    try { CharacterSelection.Apply(m.Read,delegate(long at,byte[] b){throw new IOException("Write failure");},Module,Allocation,0); }
                    catch(InvalidOperationException e){reported=e.Message.Contains("角色选择未能恢复");}
                    Require(reported,"Selection rollback reporting");
                });
                test("invalid mode rejected", delegate
                { FakeMemory m=Memory(true); m.Blocks[Allocation+Profile.DataOffset][0x2A]=3; long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Unknown mode"); });
                test("allocation alignment checked before private read", delegate
                { FakeMemory m=Memory(true); m.Blocks[Module+Profile.Hooks[0].Rva]=Profile.Hooks[0].Jump(Module,Allocation+1); long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Other,"Misaligned allocation"); });
                test("out-of-range jumps rejected", delegate
                { bool rejected=false; try { Profile.Hooks[0].Jump(Module,Module+0x100000000L); } catch(InvalidOperationException) {rejected=true;} Require(rejected,"Jump range"); });
                test("all patch sites installed", delegate
                {
                    FakeMemory m=Memory(false);
                    PatchTransaction.Install(Module,Allocation,delegate(HookSpec h,byte[] b) {m.Blocks[Module+h.Rva]=(byte[])b.Clone();});
                    long a; Require(Checks.Inspect(m.Read,Module,out a)==HookState.Ours,"Transaction installation");
                });
                test("partial write failure rolls back failed site and previous sites", delegate
                {
                    FakeMemory m=Memory(false); bool failed=false, rejected=false;
                    try
                    {
                        PatchTransaction.Install(Module,Allocation,delegate(HookSpec h,byte[] b)
                        {
                            if(!failed && h==Profile.Hooks[1] && b[0]==0xE9)
                            { m.Blocks[Module+h.Rva][0]=0xE9; failed=true; throw new IOException("Injected partial failure"); }
                            m.Blocks[Module+h.Rva]=(byte[])b.Clone();
                        });
                    }
                    catch(IOException) { rejected=true; }
                    long a; Require(rejected && Checks.Inspect(m.Read,Module,out a)==HookState.Original,"Partial rollback");
                });
                test("rollback failure is reported", delegate
                {
                    bool failed=false, reported=false;
                    try
                    {
                        PatchTransaction.Install(Module,Allocation,delegate(HookSpec h,byte[] b)
                        {
                            if(h==Profile.Hooks[1]) { failed=true; throw new IOException("Injected failure"); }
                            if(failed) throw new IOException("Injected rollback failure");
                        });
                    }
                    catch(InvalidOperationException e) {reported=e.Message.Contains("部分代码未能恢复");}
                    Require(reported,"Rollback reporting");
                });
                File.WriteAllText(path,new JavaScriptSerializer().Serialize(new {success=true,count=passed.Count,checks=passed,game_access=false}),new System.Text.UTF8Encoding(false));
                return 0;
            }
            catch(Exception error)
            {
                File.WriteAllText(path,new JavaScriptSerializer().Serialize(new {success=false,checks=passed,error=error.ToString(),game_access=false}),new System.Text.UTF8Encoding(false));
                return 1;
            }
        }

        internal static int ExportPayloads(string path)
        {
            long[] modules={0x140000000,0x7FF83AA00000,0x7FFA01000000};
            List<object> result=new List<object>();
            foreach(long module in modules)
                foreach(int slot in new int[]{0,1,37,511})
                {
                    long allocation=Checks.FirstAllocation(module)+slot*0x10000L;
                    foreach(HookSpec hook in Profile.Hooks)
                        result.Add(new {module=module,allocation=allocation,name=hook.Name,payload=Convert.ToBase64String(hook.Payload(module,allocation)),patch=Convert.ToBase64String(hook.Jump(module,allocation))});
                }
            File.WriteAllText(path,new JavaScriptSerializer { MaxJsonLength = 16 * 1024 * 1024 }.Serialize(result),new System.Text.UTF8Encoding(false));
            return 0;
        }

        internal static int ExportLegacyPayloads(string path)
        {
            long[] modules={0x140000000,0x7FF83AA00000,0x7FFA01000000};
            List<object> result=new List<object>();
            foreach(LegacyProfile previous in Profile.LegacyProfiles)
                foreach(long module in modules)
                    foreach(int slot in new int[]{0,1,37,511})
                    {
                        long allocation=Checks.FirstAllocation(module)+slot*0x10000L;
                        foreach(HookSpec hook in previous.Hooks)
                            result.Add(new {version=previous.Version,module=module,allocation=allocation,
                                name=hook.Name,payload=Convert.ToBase64String(hook.Payload(module,allocation)),
                                patch=Convert.ToBase64String(hook.Jump(module,allocation))});
                    }
            File.WriteAllText(path,new JavaScriptSerializer { MaxJsonLength = 16 * 1024 * 1024 }.Serialize(result),new System.Text.UTF8Encoding(false));
            return 0;
        }
    }
}
