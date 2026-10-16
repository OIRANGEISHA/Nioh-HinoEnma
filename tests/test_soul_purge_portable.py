"""Execute saved-weapon views with ABI and native-fallthrough assertions."""
from pathlib import Path
import sys, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from build_profile import load_beta614_plan as load_plan, assemble
import hinoenma_soul_purge as h
import test_soul_release_portable as soul
import test_general_jutsu_portable as general
from portable_machine import b
from unicorn.x86_const import *

PURGE=(51944,2,15,7,0x405,(12652,31711,0),0xC2626,41,110,0)
EFFECT=b.ACTOR+0xD0000

def definition(m):
    for off,value in h.DEFINITION:
        m.cpu.mem_write(soul.n.old.dung.DEF+off,value.to_bytes(2 if off==4 else 4,'little'))

class SoulPurgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load_plan();cls.plan=h.apply_soul_purge(cls.parent)

    def gate(self,m,slot,valid=True):
        hook=m.by_name['HE_SoulReleaseEligibility'];m.reset()
        for reg,value in ((UC_X86_REG_RBP,b.ACTOR),(UC_X86_REG_R14,soul.n.old.dung.DEF),
                          (UC_X86_REG_RCX,(0x128,0x1F0)[slot]),(UC_X86_REG_RAX,b.COMP)):
            m.cpu.reg_write(reg,value)
        before=m.protected_snapshot();regs={r:m.cpu.reg_read(r) for r in b.REGISTERS}
        m.run(hook['target'],hook['site']+hook['length'])
        regs[UC_X86_REG_RCX]=soul.GEAR[slot] if valid else b.COMP+(0x128,0x1F0)[slot]
        regs[UC_X86_REG_EFLAGS]=m.cpu.reg_read(UC_X86_REG_EFLAGS)
        self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs)
        self.assertEqual(m.protected_snapshot(),before)
        return m.cpu.reg_read(UC_X86_REG_RCX)

    def test_native_threshold_reads_selected_gear_without_changing_familiarity(self):
        for layout in b.LAYOUTS:
            for slot in (0,1):
                for familiarity in (0,29999,30000,99900):
                    m=soul.Cast(self.plan,layout);definition(m)
                    fam=[0,0];fam[slot]=familiarity;soul.equipment(m,1-slot,familiarity=tuple(fam))
                    pointer=self.gate(m,slot)
                    # Native continuation compares this exact raw value to
                    # the unchanged 30000 threshold, then accepts/rejects.
                    self.assertEqual(m.get32(pointer+0x14),familiarity)

    def test_gate_rejects_missing_selected_weapon_and_unrelated_definitions(self):
        for slot in (0,1):
            m=soul.Cast(self.plan);definition(m)
            indices=[5,191];indices[slot]=700;soul.equipment(m,1-slot,tuple(indices))
            self.gate(m,slot,False)
        for off,_ in h.DEFINITION:
            m=soul.Cast(self.plan);definition(m);at=soul.n.old.dung.DEF+off
            m.put32(at,m.get32(at)^1);self.gate(m,0,False)
        for at,val,width in ((b.COMP+0x20,0,8),(b.ACTOR+0xEF0,1,4),
                             (b.META+0xC,0,4),(b.COMP+0x108,b.ACTOR+8,8)):
            m=soul.Cast(self.plan);definition(m);m.cpu.mem_write(at,val.to_bytes(width,'little'))
            self.gate(m,0,False)

    def test_both_buff_views_keep_simd_parameters_native_cost_and_abi(self):
        for layout in b.LAYOUTS:
            for slot in (0,1):
                for name,effect,kind in (('HE_SoulPurgeAttackFamiliarity',12652,229),
                                         ('HE_SoulPurgeLuckFamiliarity',31711,230)):
                    for wrong in (None,'item','effect','type','target','dead','slot'):
                        m=soul.Cast(self.plan,layout);soul.equipment(m,1-slot)
                        if wrong=='slot':
                            indices=[5,191];indices[slot]=700;soul.equipment(m,1-slot,tuple(indices))
                        m.put32(EFFECT,effect+(wrong=='effect'));m.put32(EFFECT+4,kind+(wrong=='type'))
                        if wrong=='dead':m.put64(b.COMP+0x20,0)
                        m.reset();hook=m.by_name[name];m.page(hook['site'])
                        m.cpu.mem_write(hook['site']+hook['length'],b'\xCC')
                        # A83AD0 is a native body callsite with aligned RSP.
                        m.cpu.reg_write(UC_X86_REG_RSP,b.STACK-8)
                        m.put32(b.STACK-8+0x60,51945 if wrong=='item' else 51944)
                        for reg,value in ((UC_X86_REG_RDI,b.ACTOR),(UC_X86_REG_R14,b.ACTOR+8 if wrong=='target' else b.ACTOR),
                                          (UC_X86_REG_RSI,EFFECT),(UC_X86_REG_RCX,(0x128,0x1F0)[slot]),(UC_X86_REG_RAX,b.COMP)):
                            m.cpu.reg_write(reg,value)
                        before=m.protected_snapshot();regs={r:m.cpu.reg_read(r) for r in b.REGISTERS}
                        simd={r:m.cpu.reg_read(r) for r in range(UC_X86_REG_XMM0,UC_X86_REG_XMM15+1)}
                        m.run(hook['target'],hook['site']+hook['length'])
                        regs[UC_X86_REG_RCX]=soul.GEAR[slot] if wrong is None else b.COMP+(0x128,0x1F0)[slot]
                        regs[UC_X86_REG_EFLAGS]=m.cpu.reg_read(UC_X86_REG_EFLAGS)
                        self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs,(slot,name,wrong))
                        self.assertEqual({r:m.cpu.reg_read(r) for r in simd},simd)
                        self.assertEqual(m.protected_snapshot(),before)

    def test_normal_cast_resolves_common41_and_validates_native_definition(self):
        for layout in b.LAYOUTS:
            for phase,pending in (('idle',1),('entry',0),('cast',0)):
                with patch.object(general,'ITEMS',general.ITEMS+(PURGE,)):
                    m=general.Machine(self.plan,51944,layout)
                m.phase(phase,pending);general.GeneralJutsuTests().check_lookup(m)
            with patch.object(general,'ITEMS',general.ITEMS+(PURGE,)):
                m=general.Machine(self.plan,51944,layout)
            general.GeneralJutsuTests().entry(m,True)
        for off,_ in h.DEFINITION:
            with patch.object(general,'ITEMS',general.ITEMS+(PURGE,)):
                m=general.Machine(self.plan,51944)
            at=soul.n.old.dung.DEF+off;m.put32(at,m.get32(at)^1)
            general.GeneralJutsuTests().entry(m,False)

    def test_layout_exact_parent_and_native_consumers_remain_intact(self):
        for layout in b.LAYOUTS:
            rows=assemble(self.plan,*layout)
            spans=sorted((r['code_offset'],r['code_offset']+r['code_capacity']) for r in rows)
            for a,c in zip(spans,spans[1:]):self.assertLessEqual(a[1],c[0])
            for r in rows:self.assertLessEqual(len(r['payload']),r['code_capacity'])
        self.assertEqual(len(self.plan['hooks']),86)
        self.assertEqual(self.plan['allocation_size'],self.parent['allocation_size'])
        for before,after in zip(self.parent['hooks'],self.plan['hooks']):
            for key in ('rva','length','original','code_offset'):self.assertEqual(before[key],after[key])
        self.assertFalse(any(r['rva']<=0x7A775E<r['rva']+r['length'] for r in self.plan['hooks']))

if __name__=='__main__':unittest.main()
