"""Offline x64 lifetime, overlap, cancellation and relocation regression tests.

Native resource helpers and clip lookup are ABI-clobbering synthetic callees.
Real dependency traversal/arrival are covered by separate static/live records.
"""
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import build_profile as build
from hinoenma_abyss_lifetime import DATA_OFFSET, ROW_OFFSET, ROW_SIZE, SLOT_COUNT
from hinoenma_abyss_runtime import apply_abyss, CHANGED_INDICES
from hinoenma_abyss_resources import resources
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

P=json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf-8'))
PREVIOUS=json.loads((ROOT/'profiles/legacy-beta5.4.2.json').read_text('utf-8'))
PLAN=build.source_plan(P)
M,C,S,A=0x140000000,0x144000000,0x20008000,0x30000000
D=C+0xF000; LD=C+DATA_OFFSET; END=0x2000F000
CTL=A+0x1000; OBJ=A+0x2000; INFO=A+0x3000; IDLE=A+0x7000
BANK=A+0x10000; TABLE=A+0x20000; RECS=A+0x22000; PARAM=A+0x25000
TRANS=A+0x26000; DESCS=A+0x34000; EVENTS=A+0x38000
GPRS=(UC_X86_REG_RAX,UC_X86_REG_RBX,UC_X86_REG_RCX,UC_X86_REG_RDX,
      UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_RBP)+tuple(globals()['UC_X86_REG_R'+str(i)] for i in range(8,16))
REGS=GPRS+(UC_X86_REG_EFLAGS,UC_X86_REG_MXCSR)+tuple(globals()['UC_X86_REG_XMM'+str(i)] for i in range(16))

class CPU:
    def __init__(self):
        self.c=Uc(UC_ARCH_X86,UC_MODE_64)
        for at,size in ((M,0x1200000),(M+0x18A0000,0x1000),(C,0x60000),(0x20000000,0x10000),(A,0xC0000)):
            self.c.mem_map(at,size)
        for h in build.assemble(PLAN,M,C): self.c.mem_write(h['target'],h['payload'])
        for rva in (0x8CEA40,0x8CEC80,0x755160,0x706070,0x917500):self.c.mem_write(M+rva,b'\xC3')
        self.calls=[];self.action_calls=[];self.references={};self.stop=None
        self.stops={END,M+0x75361C,M+0x8A2906,C+0xE806};self.callback=None
        self.pending_callback=None;self.stack=S
        self.return_handle=0xFE000200;self.spawn_result=A
        self.c.hook_add(UC_HOOK_CODE,self.trace)
        for i,reg in enumerate(GPRS):self.c.reg_write(reg,0xABC000+i)
        for i in range(16):self.c.reg_write(globals()['UC_X86_REG_XMM'+str(i)],(i+1)*0x123456789ABCDEF0)
        self.c.reg_write(UC_X86_REG_EFLAGS,0x246);self.c.reg_write(UC_X86_REG_MXCSR,0x1F80)
        self.u(D,0x58E5E);self.u(D+4,0x58E5E);self.q(D+0x10,A);self.b(D+0x2A,2)
        self.actor(A,0x58E5E)
        self.q(M+0x18A0490,A)
        meta=A+0x6000;stats=A+0x5000;proxy=A+0x4000
        self.q(A+0xE90,meta);self.u(meta,0x58E5E);self.u(meta+0xC,1)
        self.q(A+0x240,stats);self.q(stats,A);self.q(stats+0x108,A);self.q(stats+0x20,100)
        self.q(A+0x230,proxy);self.q(proxy,A);self.q(proxy+8,CTL)
        self.q(CTL+0x50,A);self.q(CTL+0x58,IDLE);self.u(IDLE,0);self.b(IDLE+0x40,1)
        self.u(OBJ,0xEA6E);self.u(OBJ+4,2);self.q(INFO,OBJ);self.u(INFO+8,0x101);self.u(INFO+0x48,10)
        self.b(CTL+0x4E9,1);self.q(CTL+0x80,BANK);self.q(CTL+0x510,OBJ);self.q(CTL+0x528,INFO)
        self.q(BANK+0x128,TABLE);self.u(BANK+0x130,4);self.q(BANK+0x50,TRANS)
        self.c.mem_write(BANK+0x58,struct.pack('<HH',4096,4096));self.q(BANK+0x80,EVENTS)
        self.c.mem_write(BANK+0x88,struct.pack('<H',100));self.records={};ti=0
        for n,(ident,row) in enumerate(resources().items()):
            record=RECS+n*0x100;param=PARAM+n*0x100;self.records[ident]=record
            self.q(TABLE+n*8,record);self.u(record,ident);self.q(record+0x20,param)
            self.q(record+0x38,BANK);self.b(record+0x40,1)
            self.c.mem_write(param,bytes.fromhex(row['parameter_raw_00_a0']))
            self.c.mem_write(record+0x78,struct.pack('<QHH',TRANS,row['transition_first'],row['transition_count']))
            for t in row['transitions']:
                at=DESCS+ti*0x40;ti+=1;self.q(TRANS+t['index']*8,at);self.c.mem_write(at,bytes.fromhex(t['raw']))
        for event in resources()[73]['references']:
            at=A+0x39000+event['index']*0x80;self.q(EVENTS+event['index']*8,at)
            self.c.mem_write(at,bytes.fromhex(event['raw_00_80']))
        motion=A+0x8000;self.q(A+0x38,motion);self.u(motion+0x50,0)
        for n,slot in enumerate((2,6)):
            bank=A+0x50000+n*0x4000;mapping=bank+0x1000;keys=bank+0x1100;clips=bank+0x1200
            self.q(motion+8+slot*8,bank);self.q(bank+0x468,clips);self.q(bank+0x470,clips+24)
            self.q(bank+0x480,mapping);self.u(mapping+8,8);self.q(mapping+0x10,keys)
            self.c.mem_write(keys,b'\xFF'*64)
            for i,ident in enumerate((900,901,902)):
                self.c.mem_write(keys+i*8,struct.pack('<Ii',ident,i));self.q(clips+i*8,bank+0x1300+i*0x40)
        self.c.reg_write(UC_X86_REG_RDI,CTL);self.c.reg_write(UC_X86_REG_RAX,INFO);self.c.reg_write(UC_X86_REG_R8,OBJ)

    def q(self,at,v):self.c.mem_write(at,struct.pack('<Q',v))
    def u(self,at,v):self.c.mem_write(at,struct.pack('<I',v))
    def b(self,at,v):self.c.mem_write(at,bytes([v]))
    def value(self,at,size=8):return int.from_bytes(self.c.mem_read(at,size),'little')
    def header(self):return {n:self.value(LD+o) for n,o in (
        ('acquires',8),('duplicates',0x10),('releases',0x18),('conflicts',0x20),
        ('full',0x28),('uncertain',0x30),('generations',0x38),('outstanding',0x40),('deferred',0x48))}
    def rows(self):
        return [dict(state=self.value(LD+ROW_OFFSET+i*ROW_SIZE,4),
                     template=self.value(LD+ROW_OFFSET+i*ROW_SIZE+4,4),
                     actor=self.value(LD+ROW_OFFSET+i*ROW_SIZE+8),
                     generation=self.value(LD+ROW_OFFSET+i*ROW_SIZE+0x38)) for i in range(SLOT_COUNT)]
    def actor(self,at,template):self.c.mem_write(at,struct.pack('<IHH',template,0,1));self.q(D+0x10,at)
    def regs(self):return {r:self.c.reg_read(r) for r in REGS}
    def clobber(self,rax):
        rsp=self.c.reg_read(UC_X86_REG_RSP);self.c.mem_write(rsp+8,b'\xA5'*32)
        for reg in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11):self.c.reg_write(reg,0xFEED)
        for i in range(6):self.c.reg_write(globals()['UC_X86_REG_XMM'+str(i)],0xFEED)
        self.c.reg_write(UC_X86_REG_RAX,rax);self.c.reg_write(UC_X86_REG_EFLAGS,0x202);self.c.reg_write(UC_X86_REG_MXCSR,0x1FA0)
    def trace(self,c,at,size,_):
        if at in self.stops:self.stop=at;c.emu_stop();return
        if at not in (M+0x8CEA40,M+0x8CEC80,M+0x755160,M+0x706070,M+0x917500):return
        assert c.reg_read(UC_X86_REG_RSP)%16==8,'Synthetic Win64 callee alignment'
        if at==M+0x755160:self.clobber(self.spawn_result);return
        if at==M+0x706070:
            args=(c.reg_read(UC_X86_REG_RCX),c.reg_read(UC_X86_REG_RDX));self.action_calls.append(args)
            assert args==(CTL,170);self.q(CTL+0x58,self.records[170]);self.clobber(0);return
        if at==M+0x917500:
            count=self.value(c.reg_read(UC_X86_REG_RCX)+8,4);pairs=c.reg_read(UC_X86_REG_R10);key=c.reg_read(UC_X86_REG_RDX)&0xFFFFFFFF
            index=-1
            for i in range(count):
                if self.value(pairs+i*8,4)==key:index=self.value(pairs+i*8+4,4);break
            self.clobber(index&0xFFFFFFFF);return
        template=c.reg_read(UC_X86_REG_RCX)&0xFFFFFFFF
        assert template==c.reg_read(UC_X86_REG_RDX)&0xFFFFFFFF
        sign=1 if at==M+0x8CEA40 else -1
        assert self.value(LD,4)==0,'Native calls must execute outside the pool lock'
        self.calls.append((sign,template));self.references[template]=self.references.get(template,0)+sign
        if self.callback:
            callback,self.callback=self.callback,None
            self.pending_callback=(callback,self.return_handle if sign==1 else 0)
            c.emu_stop();return
        self.clobber(self.return_handle if sign==1 else 0)
    def run(self,at):
        while True:
            self.c.emu_start(at,0,count=120000)
            if self.pending_callback is None:return
            callback,returned=self.pending_callback;self.pending_callback=None
            context=self.c.context_save();oldstack=self.stack
            self.stack+=0x2000
            try:callback(self)
            finally:self.c.context_restore(context);self.stack=oldstack
            self.stop=None;self.clobber(returned)
            rsp=self.c.reg_read(UC_X86_REG_RSP);at=self.value(rsp)
            self.c.reg_write(UC_X86_REG_RSP,rsp+8)
    def call(self,offset,mode=None):
        self.stop=None;self.c.reg_write(UC_X86_REG_RSP,self.stack+8);self.q(self.stack+8,END)
        if mode is not None:self.q(self.stack+16,mode)
        self.run(C+offset)
        assert self.stop is not None,'Expected bounded continuation'
        return self.stop
    def acquire(self,actor=A):self.c.reg_write(UC_X86_REG_RCX,actor);self.call(0x51800);return self.c.reg_read(UC_X86_REG_RAX)
    def cleanup(self,actor=A,unmap=False):
        self.stop=None;self.c.reg_write(UC_X86_REG_RDI,actor);self.c.reg_write(UC_X86_REG_RSI,S+0x4000)
        self.q(S+0x4000,0x12345678);self.c.reg_write(UC_X86_REG_RSP,self.stack)
        if unmap:self.c.mem_unmap(A,0xC0000)
        before=self.regs();self.run(C+0x51000)
        assert self.stop==M+0x75361C and self.c.reg_read(UC_X86_REG_RSP)==self.stack
        for reg,v in before.items():
            expected=0x12345678 if reg==UC_X86_REG_RCX else actor if reg==UC_X86_REG_RDX else v
            assert self.c.reg_read(reg)==expected,('cleanup ABI',reg,v,self.c.reg_read(reg))

class Tests(unittest.TestCase):
    def test_actual_spawn_and_duplicate_capture_preserve_native_result(self):
        m=CPU();m.q(M+0x18A0490,0);m.u(A+0xEF0,0xFFFFFFFF)
        for _ in range(5):
            m.c.reg_write(UC_X86_REG_RSP,S);m.stop=None;m.c.emu_start(C+0x400,0,count=120000)
            self.assertEqual(m.stop,M+0x8A2906);self.assertEqual(m.c.reg_read(UC_X86_REG_RAX),A)
            self.assertEqual(m.c.reg_read(UC_X86_REG_RSP),S)
        self.assertEqual(m.header()['acquires'],1);self.assertEqual(m.header()['duplicates'],4)
        self.assertEqual(m.header()['outstanding'],1);self.assertEqual(m.value(D+0x1C,4),5)
    def test_acquire_clobbering_callee_preserves_full_abi(self):
        m=CPU();m.c.reg_write(UC_X86_REG_RCX,A);before=m.regs();self.assertEqual(m.acquire(),1)
        for reg,v in before.items():self.assertEqual(m.c.reg_read(reg),1 if reg==UC_X86_REG_RAX else v)
        self.assertEqual(m.value(LD,4),0)
    def test_cleanup_uses_frozen_owner_after_actor_and_selection_are_gone(self):
        m=CPU();m.acquire();m.q(D+0x10,0);m.u(D,0);m.u(D+4,0);m.q(M+0x18A0490,0)
        m.cleanup(unmap=True);m.cleanup()
        self.assertEqual(m.header()['releases'],1);self.assertEqual(m.header()['outstanding'],0)
        self.assertEqual(m.references,{0x58E5E:0});self.assertEqual(m.rows()[0]['state'],5)
    def test_overlapping_actors_keep_separate_actual_template_tickets(self):
        m=CPU();m.acquire();b=A+0xA0000;m.actor(b,0x51BE1);m.u(D+0x1C,2);m.acquire(b)
        m.u(D+4,0);m.q(D+0x10,0);m.cleanup(A)
        self.assertEqual(m.header()['outstanding'],1);self.assertEqual(m.references,{0x58E5E:0,0x51BE1:1})
        m.cleanup(b);self.assertEqual(m.header()['outstanding'],0)
        self.assertEqual(m.calls,[(1,0x58E5E),(1,0x51BE1),(-1,0x58E5E),(-1,0x51BE1)])
    def test_cleanup_during_acquire_defers_release_until_full_return(self):
        m=CPU();m.callback=lambda machine:machine.cleanup(A)
        self.assertEqual(m.acquire(),0);self.assertEqual(m.header()['deferred'],1)
        self.assertEqual(m.header()['outstanding'],0);self.assertEqual(m.calls,[(1,0x58E5E),(-1,0x58E5E)])
        self.assertEqual(m.rows()[0]['state'],5)
    def test_native_reentry_duplicate_never_deadlocks_or_retains_again(self):
        m=CPU();m.callback=lambda machine:self.assertEqual(machine.acquire(),0)
        self.assertEqual(m.acquire(),1);self.assertEqual(m.header()['conflicts'],1);self.assertEqual(len(m.calls),1)
    def test_uncertain_return_is_never_retried_and_is_released_once(self):
        m=CPU();m.return_handle=0;self.assertEqual(m.acquire(),0);self.assertEqual(m.acquire(),0)
        self.assertEqual(m.header()['uncertain'],1);self.assertEqual(m.rows()[0]['state'],3)
        m.cleanup();self.assertEqual(len(m.calls),2);self.assertEqual(m.header()['outstanding'],0)
    def test_full_pool_refuses_overwrite_and_consumed_slot_can_be_reused(self):
        m=CPU();owners=[A+i*0x100 for i in range(65)]
        for owner in owners[:64]:m.actor(owner,0x58E5E);self.assertEqual(m.acquire(owner),1)
        previous=deepcopy(m.rows());m.actor(owners[64],0x58E5E);self.assertEqual(m.acquire(owners[64]),0)
        self.assertEqual(m.rows(),previous);self.assertEqual(m.header()['full'],1)
        m.cleanup(owners[0]);self.assertEqual(m.acquire(owners[64]),1)
        self.assertEqual(m.rows()[0]['actor'],owners[64]);self.assertEqual(m.rows()[0]['generation'],65)
    def test_foreign_header_capture_cleanup_and_address_reuse(self):
        m=CPU();m.q(D+0x10,0);self.assertEqual(m.acquire(),0)
        m.actor(A,0);self.assertEqual(m.acquire(),0)
        m.actor(A,0x58E5E);m.acquire();m.cleanup(A+16);self.assertEqual(m.header()['releases'],0)
        m.cleanup(A);m.actor(A,0x51BE1);self.assertEqual(m.acquire(),1);m.cleanup(A)
        self.assertEqual(m.header()['acquires'],2);self.assertEqual(m.header()['releases'],2)
    def test_common_queue_and_repeated_floor_do_not_add_resource_holds(self):
        m=CPU();m.acquire();m.c.reg_write(UC_X86_REG_RDI,CTL)
        for _ in range(4):
            m.q(CTL+0x58,IDLE);m.call(0x2F400,1)
        self.assertEqual(m.header()['acquires'],1);self.assertEqual(m.header()['duplicates'],4)
        self.assertEqual(m.action_calls,[(CTL,170)]*4)
    def test_cancel_available_zero_only_allows_owned_73_74_75_continuation(self):
        for current,wanted in ((73,74),(73,75),(74,75),(75,75)):
            m=CPU();m.q(CTL+0x58,m.records[current]);m.b(INFO+9,0)
            m.c.reg_write(UC_X86_REG_RCX,CTL+0x70);m.c.reg_write(UC_X86_REG_RDX,wanted);m.c.reg_write(UC_X86_REG_R8,A+0x9000)
            self.assertEqual(m.call(0x2F080),END);self.assertEqual(m.c.reg_read(UC_X86_REG_RAX),m.records[wanted])
        for current in (IDLE,):
            m=CPU();m.b(INFO+9,0);m.q(CTL+0x58,current);m.c.reg_write(UC_X86_REG_RDI,CTL)
            m.call(0x2F400,1);self.assertFalse(m.c.reg_read(UC_X86_REG_EFLAGS)&1)
            self.assertEqual(m.action_calls,[]);self.assertEqual(m.header()['acquires'],0)
        m=CPU();m.b(INFO+9,0);m.q(CTL+0x58,m.records[73]);m.q(m.records[73]+0x38,BANK+16)
        m.c.reg_write(UC_X86_REG_RCX,CTL+0x70);m.c.reg_write(UC_X86_REG_RDX,75);m.c.reg_write(UC_X86_REG_R8,A+0x9000)
        self.assertEqual(m.call(0x2F080),C+0xE806)
    def test_only_five_prior_payloads_changed_and_all_native_entries_preserved(self):
        for module,allocation in ((M,C),(0x7FF709EB0000,0x7FF70CF20000)):
            old,new=build.assemble(PREVIOUS,module,allocation),build.assemble(PLAN,module,allocation)
            self.assertEqual(tuple(i for i,(a,b) in enumerate(zip(old,new)) if a['payload']!=b['payload']),CHANGED_INDICES)
            for a,b in zip(old,new):self.assertEqual(a['patched'],b['patched'])
            for h in new:self.assertLessEqual(len(h['payload']),h['code_capacity'])
    def test_compiled_fixups_match_independent_assembler_in_all_aslr_positions(self):
        specs=build.relocation_specs(PLAN)
        for module in (M,0x7FF709EB0000,0x7FFA01000000):
            for delta in (0x4000000,0x5110000,0x7FD0000):
                allocation=module+delta
                for spec,actual in zip(specs,build.assemble(PLAN,module,allocation)):
                    import base64
                    blob=bytearray(base64.b64decode(spec['template']))
                    for fix in spec['fixups']:
                        if fix['kind']==0:value=struct.pack('<Q',allocation+PLAN['data_offset'])
                        elif fix['kind']==2:value=struct.pack('<Q',module+fix['target'])
                        else:value=struct.pack('<i',module+fix['target']-(allocation+spec['code_offset']+fix['next']))
                        blob[fix['offset']:fix['offset']+len(value)]=value
                    self.assertEqual(bytes(blob),actual['payload'],(actual['name'],hex(module),hex(allocation)))
    def test_ct_number_conversion_and_all_declared_labels_preserve_source(self):
        from hinoenma_abyss_runtime import ct_compatible_plan
        converted=ct_compatible_plan(PLAN)
        raw,ct=build.assemble(PLAN,M,C),build.assemble(converted,M,C)
        self.assertEqual([h['payload'] for h in raw],[h['payload'] for h in ct])
        source=build.aa_source(PLAN)
        self.assertNotIn('.byte',source)
        self.assertIn('资源寿命版不支持游戏运行中卸载',source)
        names=build.LABEL_DEFINITION.findall(source)
        self.assertEqual(len(names),len(set(n.casefold() for n in names)))

if __name__=='__main__':unittest.main()
