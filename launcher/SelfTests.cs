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

        private static string Sha256(byte[] bytes)
        {
            using(System.Security.Cryptography.SHA256 hash=System.Security.Cryptography.SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }

        // These thirteen exact identities cover the confirmed Beta6 through Beta6.1.3 item delta. Historical
        // equality checks may exempt one only after its full template, fixup
        // sequence and relocated payload/site bytes pass independent hashes.
        private static bool VerifiedCurrentItem(int index)
        {
            int[] indices={6,7,11,13,36,39,42,48,49,51,52,59,61,62,63,65,82,83};
            int selected=Array.IndexOf(indices,index);
            if(selected<0) return false;
            string[] names={"HE_InputA","HE_InputB","HE_HimorogiFragment","HE_Consumables","HE_LivingWeaponDigitNine","HE_LadderCommonLookup","HE_ProjectileElementInheritance","HE_SameTemplateUnloadResources","HE_SaltEventCatchup","HE_PostDefeatDamage","HE_PostDefeatRestore","HE_InherentDirectElement","HE_MapVisualSpawnPrivate","HE_MapVisualResourcePrivate","HE_MapVisualRestorePrivate","HE_MapNativeIdlePrivate","HE_SoulReleaseEligibility","HE_SoulReleaseFamiliarity"};
            uint[] rvas={0x721044U,0x721099U,0x75185dU,0x751862U,0x715d4bU,0x73fa40U,0x7e2959U,0x8b1a10U,0x718950U,0x717caeU,0x70ece0U,0x717f06U,0x8c5407U,0x7604e7U,0x760778U,0x9530baU,0x766455U,0x7e28a9U};
            int[] offsets={6144,7168,11264,13312,397312,59392,114688,71680,4160,86016,90112,122880,135168,139264,143360,155648,93184,97280};
            int[] capacities={1024,1024,1024,1024,32768,2048,4096,6144,960,4096,3072,4096,4096,4096,4096,4096,1024,1024};
            int[] lengths={560,560,971,1001,32458,1899,3192,5837,5,3150,1359,1703,3480,3296,3039,2907,135,117};
            string[] original={"440fbe420c","440fbe470e","4584f6752d","83bf4c050000007424","498b7338410f2873f0","48895c2408","0f104d070f114f18","e80bff6d00","e8fbc4feff","4c8bb6b0050000","488bc4574154","0f104c24300f114d88","e854fde8ff","4885c00f8450030000","498b85c0000000","488b472048894328","4803c88339ff","833c08ff0f8490000000"};
            string[] templates={"d5c0091d7aa744137a90a031e3ab0451cf047f82c8ca60c54fb47b9a5f2073c4","efaf98657a68a9f4b5f72b09c4c2f00d5fa699f6ff1962b837b2c177af983b89","a39bd07e5a12f76d8513d765ceb04013225ac3538fd0f9732b3402232e0b3e94","b61ccfde922a42e29706d0a7e782d923edbbd1e07283cb45df2b1a8a52245cb2","a08217f091b5067206b94463ae920570114a93d980bbf1a58b8082c0c77bc6ff","bac1eef3a530116968962dd8ee12a3fa637a8c5c58e3cbe574b2b1cf7f38f742","8a6435503f2618f4afbaf7b1ebe8f73951e6eb039347438bde6e6f7d128959e7","5254effa7be5ccf6dafcf289d47a10dff0d84278b4cef6fe6c79f61304fd07a6","0a315b2859baf393decc7e79cd488b3b763ed2359e59b744dac205a8eef690da","3036fab63f6425883c59ff1a3539a8588c2b6328c7549fd585990817163153fc","51c06abbc7396d72194ce789d56b452293aed6fedb0fdd51cb3e6d06dca2ad92","a29254be3839c5f03ffcd4573ebc32fede64c26bfe34c18cd69ba3da92e21391","1963b4a7c601a6a41361fd6eb3cb6a33b2f1a96bdc6ebd61e2e9809206a4b38f","9b0fb259d3abc0831c6a5d9e696bc1e4fc3aa42ca4d8fc53b0880dcf50364bbb","d96405cb3fdc828dfd73766a60bd18e256ebdaf963f6b13f9148d9de1846de6f","6e12c712c106456250e0cdadc15c167f5896fe906f7e035cf4808af5ab736c89","69f79f40d3355eb3399397c0cd5c8eec2e3c5daa06b67648fe7b34fae00aecb1","e45d61b4a53e6450e58a9dc78f03731efa00407693dddb3dc6a1a0f0a623d6b1"};
            string[] fixups={"7ca4aa022235971dc357d1bf3f2acab362898e7f85c33d65fa17233c8e8d247f","c3025821ba3bd3ecddeaa4459a234f428fb8f1d2403906e936414a36b4a97898","ccc4899cff026b16e0c4143c1449502f6c5465b992a8068a829f8f08fc2ba14e","cf1035ca88cc901263ccf1b1c0f18202ccb9cc8c476a36dff01eae9d7c81e8e2","98bbc051aa80e4ccc7dc569bc299f5e29b2a0f62470db4da13119b71a433cd5f","7987c1442ba07b4fd5801a987709564240f7cc0332c12cd8555483297d3b9415","85bd2643459e19693d5bf502450b54fa28fee1587c2ac4f76f6981e3d8b10dff","a98bb04d41bbbd63de08a57315766ce09f32a7a6bae65933bb28a51ce6d47a9b","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","777883705f9546e4574539973769d8f1330a9201f1476156ee2878980af38581","8395e2b699f742078c4fc41b23b48f53b780604c4334b136c22d91956f04b061","87790ad5b5a43c3353fc9ab9dd276f2421eb86743d84bfe43cf21db50bde2737","37ba7ab33a1aad42d0522d95e2e9361b1b4a5467517a78e96959690e6e90ae4a","003a72fbeac452cdc38bd3d52335a769f02ddbcb5c29922e0110174ea8b95918","6a187659a3861944b58534fbc26d6f907a80efc3ad271d92b4de186dca54da5e","f446c82add38658de2d3e5d2191e8db2f7023477bbfbdad85daeb4b003de7729","a9dbc2fd0cc34c912562c9cbe5050898057cdf278a429ecde6ae23ed1526642d","158bae6d0bfb0aea144246f96a3e2c52734f7d43a886ad0ec9e2420ea515e54b"};
            string[] relocated={"0429a8c4356a67ef8b6563f55c2f6b213ae0a557e0858656c5c0213ecf4c29e1","e5700fa64cc3333f2fa6bff4732727e1300ae02ffb8d1c316e13d967125994b0","8a543b6c15d920740c74099caf9a39f1ed0536e10b1f7cc8ff0a03797686d2f5","b277fa0be53248d603173b8a2a9a76b3983ff0fedc6a882fa1b332ad23ca38b0","057481b8d71669b7fb9634f74843adb1551929af2f1b0dcfcaa947b698a14db2","c19e4e3f575d124a6ed8ed3344525986e0f331171cf1ae08ffabea0f1f1421bc","be5ac97a82d500fd3deb4bb2141d7954ba3d06bf3371d0040bc425b3e1959556","1296c3a7ca127f5fae2e9482069ff5d540971f6153761103c5002d521c957479","a63a486cade98be7cd1093701365953f27d4f7bb3da07cb92470762781b9687c","326e70840d5c2dc204a521b1992222035e220b11c5b16773dc86e9a4663459b4","64abb841941e4d6fe18f16de43eb9f3048ae35b91686a63a01957330df136773","0f43bd32405c34a73e3c29b8f28d5cdac53bdf9c368aca282559a177778aab04","f146791f508dc1f6f989311e6965667e5bf58c0f757c61330d8d7defacdea860","ff1ff7e0a28cec1732d35686787d4323c6074771c9c7077667a842571431289b","f3f298a82a27a32c1438f475ce5d5cd0f5bf64a117b8f5a1e6004c35f8234dee","63d85d6c5875e39ba79312b919cb24702bfca509a720447f5bc1350f239f2585","080869cb08b9e0418b1f0995545b249e04ddf340e229eaf2aa5d3509b747e9a4","0e4830df4951256209bb08d1baf2d784ef322b6a8954ca4fd1ae885203dc00c2"};
            HookSpec hook=Profile.Hooks[index];
            Require(Profile.Version=="1.0.0-beta.6.1.3" && hook.Name==names[selected] &&
                hook.Rva==rvas[selected] && hook.CodeOffset==offsets[selected] &&
                hook.CodeCapacity==capacities[selected] && hook.Template.Length==lengths[selected] &&
                BitConverter.ToString(hook.Original).Replace("-", "").ToLowerInvariant()==original[selected],
                "Exact confirmed Beta6.1.3 item hook geometry: "+hook.Name);
            Require(Sha256(hook.Template)==templates[selected],"Exact confirmed Beta6.1.3 item template: "+hook.Name);
            using(MemoryStream bytes=new MemoryStream())
            using(BinaryWriter writer=new BinaryWriter(bytes))
            {
                foreach(Fixup fixup in hook.Fixups)
                {
                    writer.Write(fixup.Offset); writer.Write(fixup.Kind);
                    writer.Write(fixup.Target); writer.Write(fixup.Next);
                }
                writer.Flush();
                Require(Sha256(bytes.ToArray())==fixups[selected],"Exact Beta6.1.3 item relocation specification: "+hook.Name);
            }
            using(MemoryStream bytes=new MemoryStream())
            {
                foreach(long module in new long[]{0x140000000,0x7FF83AA00000,0x7FFA01000000})
                    foreach(int slot in new int[]{0,1,37,511})
                    {
                        long at=Checks.FirstAllocation(module)+slot*0x10000L;
                        byte[] payload=hook.Payload(module,at),jump=hook.Jump(module,at);
                        bytes.Write(payload,0,payload.Length); bytes.Write(jump,0,jump.Length);
                    }
                Require(Sha256(bytes.ToArray())==relocated[selected],"Exact Beta6.1.3 item payload and entry at twelve layouts: "+hook.Name);
            }
            return true;
        }

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
                    Require(source.Length > 0x7000 && source.Length <= MemoryReader.MaximumLength,
                        "Complete expanded common-action carrier payload");
                    int maximumSlot=0;
                    foreach(HookSpec hook in Profile.Hooks)
                        maximumSlot=Math.Max(maximumSlot,hook.CodeCapacity);
                    Require(MemoryReader.MaximumLength==0x8000 && maximumSlot==MemoryReader.MaximumLength &&
                        MemoryReader.ChunkLength==0x1000,"Reader limit matches largest owned slot; page reads remain bounded");
                    int calls = 0, total = 0;
                    byte[] actual = MemoryReader.Read(Allocation, source.Length, delegate(long at, int size)
                    {
                        Require(at == Allocation + total && size > 0 && size <= 0x1000,"Sequential bounded read");
                        byte[] chunk = new byte[size]; Buffer.BlockCopy(source,total,chunk,0,size);
                        total += size; calls++; return chunk;
                    });
                    Require(calls == (source.Length+0xFFF)/0x1000 && total == source.Length && Checks.Equal(actual,source),"Every payload byte preserved");
                    // Exercise the inclusive size and canonical-address limits,
                    // including the eighth page that the former cap rejected.
                    byte[] boundary=new byte[0x8000];
                    for(int i=0;i<boundary.Length;i++) boundary[i]=(byte)(i*31+17);
                    long endOfUserRange=0x0000800000000000L-boundary.Length;
                    calls=0; total=0;
                    actual=MemoryReader.Read(endOfUserRange,boundary.Length,delegate(long at,int size)
                    {
                        Require(at==endOfUserRange+total && size==0x1000,"Eight sequential page-sized boundary reads");
                        byte[] chunk=new byte[size]; Buffer.BlockCopy(boundary,total,chunk,0,size);
                        total+=size; calls++; return chunk;
                    });
                    Require(calls==8 && total==boundary.Length && Checks.Equal(actual,boundary),
                        "Full maximum-size payload including last byte is returned");
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
                    foreach(int length in new int[]{0,-1,0x8001,int.MaxValue})
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
                    foreach(int missing in new int[]{0,1})
                    {
                        calls=0; partial=false;
                        try
                        {
                            MemoryReader.Read(Allocation,0x8000,delegate(long a,int n)
                            {
                                calls++;
                                if(calls==8) return missing==0 ? null : new byte[n-1];
                                return new byte[n];
                            });
                        }
                        catch(IOException){partial=true;}
                        Require(partial && calls==8,"Missing or short eighth chunk never returns a partial payload");
                    }
                    bool overEnd=false;
                    try
                    {
                        MemoryReader.Read(0x0000800000000000L-0x8000+1,0x8000,
                            delegate(long a,int n){throw new Exception("Unvalidated native read");});
                    }
                    catch(InvalidOperationException){overEnd=true;}
                    Require(overEnd,"Maximum-size read crossing canonical user range rejected before callbacks");
                });
                test("pristine instructions recognized", delegate
                { long a; Require(Checks.Inspect(Memory(false).Read, Module, out a) == HookState.Original, "Original state"); });
                test("current profile recognized without reinjection", delegate
                { long a; Require(Checks.Inspect(Memory(true).Read, Module, out a) == HookState.Ours && a == Allocation, "Own state"); });
                test("complete Beta 5.1 and Hotfix 1 remain read-only restart identities", delegate
                {
                    Require(Profile.Hooks.Length==84 && Profile.LegacyProfiles.Length==9,"Complete local and prior release identities");
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
                    Require(Profile.Hooks.Length==84,"Exact total execution build inventory");
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
                    Require(Profile.Hooks.Length==84,"Exact complete execution inventory");
                    Require(VerifiedCurrentItem(82) && VerifiedCurrentItem(83),"Both owned Soul Release native views match their tested identities");
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
                        if(VerifiedCurrentItem(i) || (i>=71 && i<=77) || i==80 || i==1 || i==8 || i==9 || i==15 || i==36 || i==37 || i==38 || i==39 || i==70) continue;
                        Require(Checks.Equal(Profile.Hooks[i].Template,beta541.Hooks[i].Template),"Unchanged templates preserved from Beta5.4.1");
                    }
                    for(int i=0;i<71;i++)
                    {
                        HookSpec current=Profile.Hooks[i],old=beta532.Hooks[i];
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==0xC00 && old.CodeCapacity==0x1000 : current.CodeCapacity==old.CodeCapacity)),"Previous hook slot identity");
                        if(VerifiedCurrentItem(i) || i==1 || i==8 || i==9 || i==15 || i==36 || i==37 || i==38 || i==39 || i==70) continue;
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
                test("reviewed growth payload and unchanged original templates match their exact identities", delegate
                {
                    LegacyProfile beta52=Profile.LegacyProfiles[2];
                    Require(beta52.Version=="1.0.0-beta.5.2" && beta52.Hooks.Length==60,"Exact published baseline");
                    HookSpec growth=Profile.Hooks[15];
                    Require(growth.Name=="HE_AttributeOverlay" && growth.Rva==0x7C82DBU &&
                        growth.CodeOffset==0x1B000 && growth.CodeCapacity==0x1000 && growth.Template.Length==3188,
                        "Exact Growth750 native entry and bounded payload");
                    using(System.Security.Cryptography.SHA256 hash=System.Security.Cryptography.SHA256.Create())
                        Require(BitConverter.ToString(hash.ComputeHash(growth.Template)).Replace("-","").ToLowerInvariant()==
                            "7c023e2a968862a78371cf511a567d19d1ad5637ead02eb2600bae5e95e4bc10",
                            "Growth750 template matches the live-confirmed source bytes");
                    Require(!Checks.Equal(growth.Template,beta52.Hooks[15].Template),"Growth750 revision replaces the old attribute calculation");
                    for(int i=0;i<60;i++)
                    {
                        HookSpec current=Profile.Hooks[i],old=beta52.Hooks[i];
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==0xC00 && old.CodeCapacity==0x1000 : current.CodeCapacity==old.CodeCapacity)),"Original slot identity");
                        if(VerifiedCurrentItem(i) || i==1 || i==8 || i==9 || i==15 || i==36 || i==37 || i==38 || i==39) continue;
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
                        Require(current.Name==prior.Name && current.Rva==prior.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==prior.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==0xC00 && prior.CodeCapacity==0x1000 : current.CodeCapacity==prior.CodeCapacity)) && Checks.Equal(current.Original,prior.Original),"Every previous native and scoped private slot identity");
                        bool changed=VerifiedCurrentItem(i) || i==1 || i==8 || i==9 || i==15 || i==36 || i==37 || i==38 || i==39 || i==70 || (i>=72 && i<=77);
                        Require(Checks.Equal(current.Template,prior.Template)!=changed,"Only reviewed lifetime, LW and growth bodies differ");
                        foreach(long module in new long[]{Module,0x7FF83AA00000})
                            foreach(int slot in new int[]{0,37,511})
                            {
                                long at=Checks.FirstAllocation(module)+slot*0x10000L;
                                Require(Checks.Equal(current.Jump(module,at),prior.Jump(module,at))==(i!=36),"Only h36 previous native jump moves");
                                if(!changed) Require(Checks.Equal(current.Payload(module,at),prior.Payload(module,at)),"Other relocated payloads preserved");
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
