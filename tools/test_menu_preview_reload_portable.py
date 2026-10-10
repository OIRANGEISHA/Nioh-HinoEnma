"""Offline Beta5.3.1 relocation and ABI checks with synthetic menu records.

No game files, game memory, captured resource banks, or process APIs are used.
Native lookup/queue/update are isolated ABI stubs; the real visible behavior
is covered by the separately recorded user tests.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src'),str(ROOT/'.devdeps')]
import menu_preview_reload_portable as integrated
import menu_preview_aura_source as aura
import test_menu_preview_portable_integration as old
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
import unicorn.x86_const as reg

TIMING,BANK,HASH,PLAYBACK,MANAGER=(0x31017000,0x31018000,0x31019000,0x3101A000,0x3101B000)
BLOB,PAIRS=0x32000000,0x32020000
REGISTERS=old.REGISTERS+(reg.UC_X86_REG_FPCW,reg.UC_X86_REG_FPSW,reg.UC_X86_REG_FPTAG)


class Machine(old.Machine):
    def __init__(self,plan,**kw):
        super().__init__(old.integrated.apply_menu_preview(old.portable.source_plan_beta52(plan)),**kw)
        self.plan=plan
        saved=bytes(self.cpu.mem_read(self.code,old.integrated.ALLOCATION_SIZE))
        self.cpu.mem_unmap(self.code,old.integrated.ALLOCATION_SIZE)
        self.cpu.mem_map(self.code,integrated.ALLOCATION_SIZE)
        self.cpu.mem_write(self.code,saved)
        self.hooks=old.portable.assemble(plan,self.module,self.code)[-11:]
        for h in self.hooks:self.cpu.mem_write(h['target'],h['payload'])
        self.distance=self.code+0x35000;self.height=self.distance+0x30;self.ledger=self.distance+0x80

    def capture(self):
        self.constructor();self.execute(4);self.complete();return self


class AuraMachine(Machine):
    def __init__(self,plan,**kw):
        super().__init__(plan,**kw);self.capture()
        self.cpu.mem_map(BLOB,0x40000)
        self.put64(BLOB,0x4B4341505F474D54)
        for off,value in ((0x10,0x14490),(0x14,81),(0x20,0x30),(0x28,0x2D0),(0x2D0,163)):
            self.put32(BLOB+off,value)
        # A deliberately synthetic hash array, copied to a distinct allocation.
        pairs=b''.join(struct.pack('<Q',0xABCD000000000000+i) for i in range(163))
        self.cpu.mem_write(BLOB+0x2D8,pairs);self.cpu.mem_write(PAIRS,pairs)
        self.cpu.mem_write(BLOB+aura.DESCRIPTOR_OFFSET,aura.CONTRACT_BYTES)
        self.put64(self.module+plan['targets']['effect_manager'],MANAGER)
        self.put64(old.ACTOR+0x68,TIMING);self.cpu.mem_write(old.ACTOR+0x430,b'\x01')
        self.put64(TIMING,self.module+plan['targets']['timing_vtable']);self.put64(TIMING+8,old.ACTOR)
        self.put64(TIMING+0x40,PLAYBACK);self.put64(TIMING+0x10,BANK)
        self.put64(PLAYBACK,self.module+plan['targets']['playback_vtable']);self.put64(PLAYBACK+8,old.ACTOR)
        self.put64(BANK,BLOB);self.put64(BANK+8,HASH)
        self.put32(HASH+8,163);self.put64(HASH+0x10,PAIRS)
        self.lookup_result=BLOB+aura.DESCRIPTOR_OFFSET;self.lookup_mutation=None
        self.original_entries=[];self.initialize()

    def initialize(self):
        self.reset();self.cpu.reg_write(reg.UC_X86_REG_RSI,self.owner)
        self.cpu.reg_write(reg.UC_X86_REG_RCX,MANAGER)
        self.cpu.reg_write(reg.UC_X86_REG_FPCW,0x37F)
        self.cpu.reg_write(reg.UC_X86_REG_FPSW,0);self.cpu.reg_write(reg.UC_X86_REG_FPTAG,0xFFFF)

    def registers(self):return {r:self.cpu.reg_read(r) for r in REGISTERS}

    def clobber(self,seed,result=None):
        for i,r in enumerate(old.GPRS[:-1]):self.cpu.reg_write(r,seed+i)
        for i,r in enumerate(old.XMMS):self.cpu.reg_write(r,(seed<<64)+seed+i)
        self.cpu.reg_write(reg.UC_X86_REG_EFLAGS,0x246)
        self.cpu.reg_write(reg.UC_X86_REG_MXCSR,0x3F80)
        self.cpu.reg_write(reg.UC_X86_REG_FPCW,0xB7F)
        if result is not None:self.cpu.reg_write(reg.UC_X86_REG_RAX,result)

    def return_stub(self):
        sp=self.cpu.reg_read(reg.UC_X86_REG_RSP)
        self.cpu.reg_write(reg.UC_X86_REG_RIP,self.get64(sp));self.cpu.reg_write(reg.UC_X86_REG_RSP,sp+8)

    def trace(self,cpu,address,size,_):
        if not hasattr(self,'lookup_result'):return super().trace(cpu,address,size,_)
        if address==self.stop:self.reached=True;cpu.emu_stop();return
        if address==self.injection_at and self.injection:
            fn,self.injection=self.injection,None;fn(self)
        for name in ('timing_lookup','timing_queue','original_update'):
            if address!=self.module+self.plan['targets'][name]:continue
            sp=cpu.reg_read(reg.UC_X86_REG_RSP)
            if name=='original_update':
                self.original_entries.append(self.registers());self.calls.append(('original',))
            else:
                if sp&15!=8:raise AssertionError('Win64 helper call must be aligned')
                args=tuple(cpu.reg_read(r) for r in (reg.UC_X86_REG_RCX,reg.UC_X86_REG_RDX,
                    reg.UC_X86_REG_R8,reg.UC_X86_REG_R9))
                self.calls.append((name,*args));cpu.mem_write(sp+8,b'\xA5'*0x20)
                if name=='timing_lookup':
                    if self.lookup_mutation:self.lookup_mutation(self)
                    self.clobber(0xBC00000000000000,self.lookup_result)
                else:self.clobber(0xBD00000000000000)
            self.return_stub();return

    def execute_aura(self):
        self.original_entries=[];return self.execute(10)


class ReloadTests(unittest.TestCase):
    byte_comparisons=0;cpu_comparisons=0
    @classmethod
    def setUpClass(cls):
        cls.base=old.baseline();cls.previous=old.integrated.apply_menu_preview(cls.base)
        cls.plan=integrated.apply_menu_preview(cls.base)
        cls.items=old.portable.relocation_specs(cls.plan)
        cls.ct=old.portable.aa_source(integrated.ct_compatible_plan(cls.plan))
        cls.ct_bodies=old.aa_hook_sources(cls.ct,cls.plan)

    def eq(self,a,b):self.assertEqual(a,b);type(self).byte_comparisons+=1
    def cpu_eq(self,a,b):self.assertEqual(a,b);type(self).cpu_comparisons+=1

    def camera(self,m,expected,raised=False,protect=True):
        m.reset();m.put64(old.STACK_TOP+0x38,m.module+self.plan['targets']['native_caller_return'])
        data=m.height if raised else m.distance
        counts=(m.get32(data+4),m.get32(data+8))
        saved=m.protected() if protect else {}
        before,after=m.execute(9 if raised else 8)
        output=reg.UC_X86_REG_XMM6 if raised else reg.UC_X86_REG_XMM2
        value=old.bits((-45.0 if expected else -55.0) if raised else (740.0 if expected else 580.0))
        for r in old.REGISTERS:self.cpu_eq(after[r],value if r==output else before[r])
        for at,raw in saved.items():self.cpu_eq(bytes(m.cpu.mem_read(at,len(raw))),raw)
        self.cpu_eq((m.get32(data+4)-counts[0],m.get32(data+8)-counts[1]),(int(expected),int(not expected)))
        for at,n in m.writes:
            self.assertTrue(old.STACK_TOP-0x70<=at and at+n<=old.STACK_TOP or data<=at and at+n<=data+12)

    def aura(self,m,expected,lookup=True,protect=True):
        m.initialize();saved=m.protected() if protect else {}
        if protect:saved[BLOB]=bytes(m.cpu.mem_read(BLOB,0x40000))
        before,after=m.execute_aura()
        self.cpu_eq(len(m.original_entries),1)
        for r in REGISTERS:
            self.cpu_eq(after[r],before[r])
            self.cpu_eq(m.original_entries[0][r],before[r]-8 if r==reg.UC_X86_REG_RSP else before[r])
        queries=[x for x in m.calls if x[0]=='timing_lookup'];queues=[x for x in m.calls if x[0]=='timing_queue']
        self.cpu_eq(len(queries),int(lookup));self.cpu_eq(len(queues),int(expected))
        if queries:self.cpu_eq(queries[0][1:3],(BANK,99048))
        if queues:self.cpu_eq(queues[0][1:],(TIMING,99048,0xFFFFFFFF,0))
        for at,raw in saved.items():self.cpu_eq(bytes(m.cpu.mem_read(at,len(raw))),raw)
        self.cpu_eq(m.get32(m.ledger+0x20),0)
        for at,n in m.writes:
            self.assertTrue(old.STACK_TOP-0x800<=at and at+n<=old.STACK_TOP or m.ledger<=at and at+n<=m.ledger+0x30)

    def test_exact71_inventory_protection_and_zero_scratch(self):
        self.eq(len(self.plan['hooks']),71);self.eq(self.plan['allocation_size'],0x36000)
        self.eq(len(self.plan['protected_data_pages']),7)
        m=Machine(self.plan);self.cpu_eq(bytes(m.cpu.mem_read(m.distance,0x1000)),bytes(0x1000))

    def test_preserve_all68_existing_sources_and_fixups(self):
        self.eq(self.plan['hooks'][:68],self.previous['hooks'][:68])
        self.eq(self.items[:68],old.portable.relocation_specs(self.previous)[:68])
        for name,value in self.base['targets'].items():self.eq(self.plan['targets'][name],value)

    def test_all71_ct_and_exe_payloads_match12_aslr_layouts(self):
        for base,allocation in old.LAYOUTS:
            for hook,item in zip(old.portable.assemble(self.plan,base,allocation),self.items):
                self.eq(hook['payload'],old.exe_payload(item,base,allocation))
                self.eq(hook['payload'],old.aa_payload(self.ct_bodies[hook['name']],base,allocation,hook['target']))
                self.assertLessEqual(len(hook['payload']),hook['code_capacity'])

    def test_invalid_source_targets_pages_and_capacity_rejected(self):
        mutations=(lambda p:p.update(allocation_size=0x35000),lambda p:p.update(menu_reload_data_offset=0x29000),
            lambda p:p['protected_data_pages'].pop(),lambda p:p['hooks'][-1].update(code_capacity=0x8000),
            lambda p:p['hooks'][-1].update(asm=p['hooks'][-1]['asm']+'\ninc rax'),
            lambda p:p['targets'].update(timing_queue=0x969080))
        for fn in mutations:
            p=deepcopy(self.plan);fn(p)
            with self.assertRaises(ValueError):integrated.validate_layout(p)

    def test_camera_current_capture_without_immutable_heap_pins(self):
        m=Machine(self.plan).capture();m.cpu.mem_write(m.scope+0x10,bytes(0x20))
        self.camera(m,True);self.camera(m,True,True)

    def test_camera_new_owner_body_after_reload_keeps_framing(self):
        m=Machine(self.plan).capture();owner,body=old.OWNER+0x8000,old.BODY+0x4000
        m.put64(owner,m.module+self.plan['targets']['base_mode_vtable']);m.put32(owner+0x1C,1)
        m.put64(m.visual,owner);m.put64(old.WRAPPER+0x188,body);m.put64(m.appearance+0x18,body)
        m.put32(m.visual+0x2C,2);m.put32(m.visual+0x30,2);m.put32(m.appearance+0x3C,2)
        self.camera(m,True);self.camera(m,True,True)

    def test_camera_foreign_loading_and_incomplete_fall_back(self):
        changes=(lambda m:m.put32(m.production,100),lambda m:m.put32(m.visual+0x14,6),
            lambda m:m.put32(m.visual+0x20,1),lambda m:m.put32(m.visual+0x38,0),
            lambda m:m.put32(m.visual+0x30,2),lambda m:m.put32(m.appearance+0x3C,0),
            lambda m:m.put64(old.CAMERA+0x208,old.ACTOR+0x1000),
            lambda m:m.put64(old.WRAPPER+0x188,old.BODY+0x1000))
        for raised in (False,True):
            for change in changes:
                m=Machine(self.plan).capture();change(m);self.camera(m,False,raised)

    def test_camera_generation_change_between_guards_falls_back(self):
        for raised in (False,True):
            for field in ('swap','capture'):
                m=Machine(self.plan).capture()
                def mutate(x):
                    if field=='swap':x.put32(x.visual+0x2C,2);x.put32(x.visual+0x30,2)
                    else:x.put32(x.appearance+0x3C,2)
                m.inject_second_guard(9 if raised else 8,mutate);self.camera(m,False,raised,False)

    def test_camera_both_scalars_all12_layouts(self):
        for layout in old.LAYOUTS:
            m=Machine(self.plan,layout=layout).capture();self.camera(m,True);self.camera(m,True,True)

    def test_aura_distinct_copied_array_once_per_generation(self):
        m=AuraMachine(self.plan);self.assertNotEqual(PAIRS,BLOB+0x2D8)
        self.aura(m,True);self.aura(m,False,False)
        for generation in (2,3,0xFFFFFFFF,1):
            m.put32(m.visual+0x2C,generation);m.put32(m.visual+0x30,generation);self.aura(m,True)
        self.cpu_eq(m.get32(m.ledger+0x24),5)

    def test_aura_all12_aslr_abi_and_owned_queue(self):
        for layout in old.LAYOUTS:self.aura(AuraMachine(self.plan,layout=layout),True)

    def test_aura_any_pair_content_mismatch_rejects(self):
        for index in (0,1,81,162):
            m=AuraMachine(self.plan);m.put64(PAIRS+8*index,m.get64(PAIRS+8*index)^1)
            self.aura(m,False,False)

    def test_aura_lookup_rechecks_copy_pointer_and_contents(self):
        for kind in ('pointer','content','generation'):
            m=AuraMachine(self.plan)
            def mutate(x):
                if kind=='pointer':
                    x.cpu.mem_write(PAIRS+0x1000,bytes(x.cpu.mem_read(PAIRS,163*8)))
                    x.put64(HASH+0x10,PAIRS+0x1000)
                elif kind=='content':x.put64(PAIRS+0x280,0)
                else:x.put32(x.visual+0x2C,2);x.put32(x.visual+0x30,2)
            m.lookup_mutation=mutate;self.aura(m,False,True,False)

    def test_aura_foreign_owner_player_timing_bank_and_state_rejected(self):
        changes=(lambda m:m.put32(m.production,100),lambda m:m.put32(m.visual+8,0x51BE1),
            lambda m:m.put64(m.visual,old.OWNER+0x1000),lambda m:m.put32(old.OWNER+0x1C,0),
            lambda m:m.put32(m.visual+0x38,0),lambda m:m.put32(m.visual+0x20,1),
            lambda m:m.put32(old.ACTOR,0x58E5E),lambda m:m.put32(old.ACTOR+0x460,1),
            lambda m:m.put32(old.ACTOR+0x434,1),lambda m:m.put32(m.appearance+0x3C,0),
            lambda m:m.put64(TIMING+8,old.ACTOR+0x1000),lambda m:m.put32(PLAYBACK+0x14,1),
            lambda m:m.put32(HASH+8,0),lambda m:m.put32(BLOB+0x2D0,0),
            lambda m:m.put64(m.module+self.plan['targets']['effect_manager'],MANAGER+0x1000))
        for change in changes:
            m=AuraMachine(self.plan);change(m);self.aura(m,False,False)

    def test_aura_descriptor_contract_mismatch_and_foreign_lookup_rejected(self):
        for offset in (0,4,0x3C,0xB8,0x130):
            m=AuraMachine(self.plan);m.put32(BLOB+aura.DESCRIPTOR_OFFSET+offset,1)
            self.aura(m,False)
        m=AuraMachine(self.plan);m.lookup_result=BLOB+aura.DESCRIPTOR_OFFSET+4;self.aura(m,False)

    def test_aura_reload_new_owner_and_body_is_new_generation(self):
        m=AuraMachine(self.plan);self.aura(m,True)
        owner,body=old.OWNER+0x8000,old.BODY+0x4000
        m.owner=owner;m.put64(owner,m.module+self.plan['targets']['base_mode_vtable']);m.put32(owner+0x1C,1)
        m.put64(m.visual,owner);m.put64(old.WRAPPER+0x188,body);m.put64(m.appearance+0x18,body)
        self.aura(m,True);self.cpu_eq(m.get32(m.ledger+0x24),2)


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReloadTests))
    if not result.wasSuccessful():return 1
    names=('tools/menu_preview_reload_portable.py','tools/menu_preview_reload_sources.py',
        'tools/menu_preview_aura_source.py','tools/test_menu_preview_reload_portable.py')
    report=dict(success=True,tests_run=result.testsRun,byte_comparisons=ReloadTests.byte_comparisons,
        cpu_comparisons=ReloadTests.cpu_comparisons,aslr_layouts=len(old.LAYOUTS),process_access=False,
        native_calls=False,synthetic_records=True,preserved_hooks=68,total_hooks=71,
        source_files={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names})
    path=ROOT/'artifacts/menu-preview-reload-validation.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(report));return 0


if __name__=='__main__':raise SystemExit(main())
