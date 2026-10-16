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

        // These exact identities cover the confirmed Beta6 through Beta6.2 item delta. Historical
        // equality checks may exempt one only after its full template, fixup
        // sequence and relocated payload/site bytes pass independent hashes.
        private static bool VerifiedCurrentItem(int index)
        {
            int[] indices={6,7,11,13,36,39,42,48,49,51,52,53,54,59,60,61,62,63,65,68,69,78,79,82,83,84,85};
            int selected=Array.IndexOf(indices,index);
            if(selected<0) return false;
            string[] names={"HE_InputA","HE_InputB","HE_HimorogiFragment","HE_Consumables","HE_LivingWeaponDigitNine","HE_LadderCommonLookup","HE_ProjectileElementInheritance","HE_SameTemplateUnloadResources","HE_SaltEventCatchup","HE_PostDefeatDamage","HE_PostDefeatRestore","HE_PostDefeatHealEvent","HE_PostDefeatHealScript","HE_InherentDirectElement","HE_MapVisualReadyPrivate","HE_MapVisualSpawnPrivate","HE_MapVisualResourcePrivate","HE_MapVisualRestorePrivate","HE_MapNativeIdlePrivate","HE_MapPreviewCameraDistancePrivate","HE_MapPreviewCameraHeightPrivate","HE_OrochiZeroLengthRay","HE_OrochiStalledInvalidRayExit","HE_SoulReleaseEligibility","HE_SoulReleaseFamiliarity","HE_SoulPurgeAttackFamiliarity","HE_SoulPurgeLuckFamiliarity"};
            uint[] rvas={0x721044U,0x721099U,0x75185dU,0x751862U,0x715d4bU,0x73fa40U,0x7e2959U,0x8b1a10U,0x718950U,0x717caeU,0x70ece0U,0x70b180U,0x6ef439U,0x717f06U,0x8c536fU,0x8c5407U,0x7604e7U,0x760778U,0x9530baU,0x856565U,0x850a85U,0x7dcf10U,0x216ac7U,0x766455U,0x7e28a9U,0xa8aee0U,0xa8afebU};
            int[] offsets={6144,7168,11264,13312,397312,59392,114688,71680,4160,86016,90112,94208,98304,122880,131072,135168,139264,143360,155648,172032,176128,262144,266240,93184,97280,95232,96256};
            int[] capacities={1024,1024,1024,1024,32768,2048,4096,6144,960,4096,3072,1024,4096,4096,4096,4096,4096,4096,4096,4096,4096,4096,4096,1024,1024,1024,1024};
            int[] lengths={734,734,971,1001,32458,1899,3192,5837,5,3150,1359,800,3789,1703,2931,3480,3920,3280,2973,3742,2943,2967,1370,276,117,112,112};
            string[] original={"440fbe420c","440fbe470e","4584f6752d","83bf4c050000007424","498b7338410f2873f0","48895c2408","0f104d070f114f18","e80bff6d00","e8fbc4feff","4c8bb6b0050000","488bc4574154","e8fb5f0200","e872560c00","0f104c24300f114d88","8b461c4533e4","e854fde8ff","4885c00f8450030000","498b85c0000000","488b472048894328","f30f101517809900","f30f103517db9900","48895c2408","4d85c07566","4803c88339ff","833c08ff0f8490000000","4803c88339ff","4803c88339ff"};
            string[] templates={"1aad459c3bbc7eaad1b5bf1b71997a0db306b23d139f8e30ef9a5d376ae182fa","75b1d388ffed4a55d7e1b8f35059c02e4e3664caeb997af7829302c701cb311a","a39bd07e5a12f76d8513d765ceb04013225ac3538fd0f9732b3402232e0b3e94","b61ccfde922a42e29706d0a7e782d923edbbd1e07283cb45df2b1a8a52245cb2","f74120f90430a500e0960a8daf8d967350a06f95878f2388e21264723b959ffe","bac1eef3a530116968962dd8ee12a3fa637a8c5c58e3cbe574b2b1cf7f38f742","8a6435503f2618f4afbaf7b1ebe8f73951e6eb039347438bde6e6f7d128959e7","5254effa7be5ccf6dafcf289d47a10dff0d84278b4cef6fe6c79f61304fd07a6","962dfa2976eac6776ef96c64ed943e5436206f78ca8112be72033601b540615d","3036fab63f6425883c59ff1a3539a8588c2b6328c7549fd585990817163153fc","51c06abbc7396d72194ce789d56b452293aed6fedb0fdd51cb3e6d06dca2ad92","d8aaab0f6a75df6d2322e4f3a328ca308a3eaf8b3fdd374d6f48b7a565d8cfbb","e8c58dc3e475b7688e005a37760cd7541c8d517e0098381442e17546063aab9a","a29254be3839c5f03ffcd4573ebc32fede64c26bfe34c18cd69ba3da92e21391","3c8d9bb28a1f373d0e2b5553616a46c5eb437a4aa1b1fc30c36382e954ecb79a","1963b4a7c601a6a41361fd6eb3cb6a33b2f1a96bdc6ebd61e2e9809206a4b38f","3981335e108180b4c1dffe31521ae1769285504bcb37a0db629edd2006cbb530","a7160e50fb21e381fdee84d4b3cde0bb83f9e1ae91b34801bba39d2275ac9bd0","4d456efc9336f3a162f2a6095688d1df9e4340cdccba939b462e37c49359b215","bc1beb18f69aec1dff11868bfa05e9e16abf00b93a476a2c547fbc919a9ccfab","ea1aeda3186d308c398f1b00dce42ef5849ab0dc9079283515fcbec0e7e1d40e","88df81c56f7457a3969ff045fc9b291740263c31b621fa549262fbfca852c9d6","5d92e5a517da359179c6e239bab7bf78cd6061ee15985650e1f2224a5829f8fb","d3f37e6fea993c610b975a1ab6397e01dc610112a000d99591ba6c80446b6b7c","e45d61b4a53e6450e58a9dc78f03731efa00407693dddb3dc6a1a0f0a623d6b1","eadfaf0bdfe94245430cc12cc434fc727a1698415b7e1dcafa2497cce20cf646","73926cf16b17e7a8b41beef58d5dbf07c0d07ab01aaf39b559b8f8771ff62a45"};
            string[] fixups={"ae037cf84acf88c0f47fad71bfb81b51b53d166fbbcea6be91a61c0062d38b7a","b7f8cae83a973a7d19002f202d431c6fc11be2f1b6948a4bbd707c67df1c920f","ccc4899cff026b16e0c4143c1449502f6c5465b992a8068a829f8f08fc2ba14e","cf1035ca88cc901263ccf1b1c0f18202ccb9cc8c476a36dff01eae9d7c81e8e2","7ecb644865392d0a68c26c63d20ed0c18b8eafa1833aa2da3b5b08444ab06b6a","7987c1442ba07b4fd5801a987709564240f7cc0332c12cd8555483297d3b9415","85bd2643459e19693d5bf502450b54fa28fee1587c2ac4f76f6981e3d8b10dff","a98bb04d41bbbd63de08a57315766ce09f32a7a6bae65933bb28a51ce6d47a9b","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","777883705f9546e4574539973769d8f1330a9201f1476156ee2878980af38581","8395e2b699f742078c4fc41b23b48f53b780604c4334b136c22d91956f04b061","d6bdede0a86e34067ba1ab9fa7bbadb25e132ea1783e3114e8f48a7d09bb2c86","274b83735d3c9eefeb429b49cdf06b36babe10b39285da767c1d581c0f1a2eeb","87790ad5b5a43c3353fc9ab9dd276f2421eb86743d84bfe43cf21db50bde2737","9bdafaa1e2b0be3c48e16228f07a6dd103ecde3262ff05c48ea05887c3fcb2a5","37ba7ab33a1aad42d0522d95e2e9361b1b4a5467517a78e96959690e6e90ae4a","003a72fbeac452cdc38bd3d52335a769f02ddbcb5c29922e0110174ea8b95918","6a187659a3861944b58534fbc26d6f907a80efc3ad271d92b4de186dca54da5e","f446c82add38658de2d3e5d2191e8db2f7023477bbfbdad85daeb4b003de7729","1715cba227657b8b8f058e1f47950cf35fabc9a309cda39e2b2da7a48b10cbdf","060acd0ee8100f169ae2dbbe08fcd50c088161d07535011468dfaf748c5262a8","7534c34945f2ab8cb70ac079afc0253efd8934d6c351489beb342e70aa2d8e4f","38e289a176a69a9c9efa2c88bb6aca6d981186689e88cfe4518140f70b923669","39faa7a75100f9bcc0e497cdb2301ada3a0ccf8f1aaf11a1688eaff44773adb3","158bae6d0bfb0aea144246f96a3e2c52734f7d43a886ad0ec9e2420ea515e54b","9d179b2f61c51101057f02e585104deec10725de8da855fff85208929f0ec266","de074791463474a6d55c89e056289547b1c034bda3994b5799db6f5a93da5b66"};
            string[] relocated={"f9f6273ace5e3a601b1ad79d274ea7fa4b408baed4c61b7485ba7a9ccfb185f8","4ffba4e9f3ce0b871028c4a7c492802ca698058c105c607e3e94f0005ce6fb67","8a543b6c15d920740c74099caf9a39f1ed0536e10b1f7cc8ff0a03797686d2f5","b277fa0be53248d603173b8a2a9a76b3983ff0fedc6a882fa1b332ad23ca38b0","597da05cb5a4e263529774a5e4688a84e45f45733a81c7e533d442a51999991b","c19e4e3f575d124a6ed8ed3344525986e0f331171cf1ae08ffabea0f1f1421bc","be5ac97a82d500fd3deb4bb2141d7954ba3d06bf3371d0040bc425b3e1959556","1296c3a7ca127f5fae2e9482069ff5d540971f6153761103c5002d521c957479","158351988f41f9d16d4460c1b01318fef594e4929345d510bd0e120fe97b98a1","326e70840d5c2dc204a521b1992222035e220b11c5b16773dc86e9a4663459b4","64abb841941e4d6fe18f16de43eb9f3048ae35b91686a63a01957330df136773","96a320a96a04438cdb2f4e68e3d9f6304b6ee90dba4a59c187312a947b8c42df","aa6f5966983bfdffbf6e8af0da2a44a21f562fb89d9547356820de908538dc24","0f43bd32405c34a73e3c29b8f28d5cdac53bdf9c368aca282559a177778aab04","fb3e75e5077aa064acac57275ac871d5328a249cf7cee71e8a33b36e41cee6d6","f146791f508dc1f6f989311e6965667e5bf58c0f757c61330d8d7defacdea860","822a83b72e90eac28b2e0b44bf9ef3de6b7b82efed9abdcb72ccd22653f82e74","9014891a78798ab222383ca1003783da0bc8ff31bc45f8d0a0a49bc9c9be7cf5","91e136093eaabd605d634fd34dc8d176d1865a67aebeec9cee63b6d632a009f3","5c1942ddc4ec1dcf1cf9d7cc0cc05f5b7d4c3b975f51dd76a354e7f7da40f1e4","7784fc893dc557a7382289b368cefb8ed621efed8d3122dda0f6c89bfc373e60","7ba1fa462a1c951be0f9c231ee733db2d21873f30d9f4d943ed70a7a03de3fac","6b6e5f1d063da485bf4317a831ba21631c9cdbc098c8990092a6950b6caa1a1e","68c7283c8d434389abbc49e7f362cc91e07309e7ca0df7b342ae3ed062e92c56","0e4830df4951256209bb08d1baf2d784ef322b6a8954ca4fd1ae885203dc00c2","344e5a69383df952ab8f7ea6f3fbd69ec6ce5fad6827d2a58782d2e8ebaa26db","61e70f99daaba35b8fc3284c8dadebaaf30f201e96ff34b28cf4ee6248973e2a"};
            HookSpec hook=Profile.Hooks[index];
            Require(Profile.Version=="1.0.0-beta.6.2" && hook.Name==names[selected] &&
                hook.Rva==rvas[selected] && hook.CodeOffset==offsets[selected] &&
                hook.CodeCapacity==capacities[selected] && hook.Template.Length==lengths[selected] &&
                BitConverter.ToString(hook.Original).Replace("-", "").ToLowerInvariant()==original[selected],
                "Exact confirmed Beta6.2 item hook geometry: "+hook.Name);
            Require(Sha256(hook.Template)==templates[selected],"Exact confirmed Beta6.2 item template: "+hook.Name);
            using(MemoryStream bytes=new MemoryStream())
            using(BinaryWriter writer=new BinaryWriter(bytes))
            {
                foreach(Fixup fixup in hook.Fixups)
                {
                    writer.Write(fixup.Offset); writer.Write(fixup.Kind);
                    writer.Write(fixup.Target); writer.Write(fixup.Next);
                }
                writer.Flush();
                Require(Sha256(bytes.ToArray())==fixups[selected],"Exact Beta6.2 item relocation specification: "+hook.Name);
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
                Require(Sha256(bytes.ToArray())==relocated[selected],"Exact Beta6.2 item payload and entry at twelve layouts: "+hook.Name);
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
                    Require(Profile.Hooks.Length==86 && Profile.LegacyProfiles.Length==9,"Complete local and prior release identities");
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
                    Require(Profile.Hooks.Length==86,"Exact total execution build inventory");
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
                    Require(Profile.Hooks.Length==86,"Exact complete execution inventory");
                    Require(VerifiedCurrentItem(82) && VerifiedCurrentItem(83) && VerifiedCurrentItem(84) && VerifiedCurrentItem(85),"All owned Soul Release/Purge native views match their tested identities");
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
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==(i==53 ? 0x400 : 0xC00) && old.CodeCapacity==0x1000 : current.CodeCapacity==old.CodeCapacity)),"Previous hook slot identity");
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
                        Require(current.Name==old.Name && current.Rva==old.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==old.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==(i==53 ? 0x400 : 0xC00) && old.CodeCapacity==0x1000 : current.CodeCapacity==old.CodeCapacity)),"Original slot identity");
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
                        Require(current.Name==prior.Name && current.Rva==prior.Rva && (i==36 ? current.CodeOffset==0x61000 && current.CodeCapacity==0x8000 : current.CodeOffset==prior.CodeOffset && (i==52 || i==53 ? current.CodeCapacity==(i==53 ? 0x400 : 0xC00) && prior.CodeCapacity==0x1000 : current.CodeCapacity==prior.CodeCapacity)) && Checks.Equal(current.Original,prior.Original),"Every previous native and scoped private slot identity");
                        bool changed=(VerifiedCurrentItem(i) && i!=53) || i==1 || i==8 || i==9 || i==15 || i==36 || i==37 || i==38 || i==39 || i==70 || (i>=72 && i<=77);
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
