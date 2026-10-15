"""CPU-only Soul Release views; real projectile/stock require live evidence."""
from pathlib import Path
import struct, sys, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import test_nine_talismans_portable as n
import hinoenma_soul_release as soul
from build_profile import load_beta612_plan as load_plan, assemble
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

SOUL=(64629,2,15,17,0x405,(0,0,0),0x5B260,42,111,194)
OWNER=b.ACTOR+0xC0000
GEAR=(OWNER+0x210+5*0xD0,OWNER+0x210+191*0xD0)
PROJECTILE=b.ACTOR+0xB0000
ATTACK=b.ACTOR+0xB1000
DESCRIPTOR=b.ACTOR+0xB2000

def equipment(m,selector=1,indices=(5,191),familiarity=(99900,99900)):
    m.page(m.module+m.plan['targets']['mission_temp_owner'])
    m.put64(m.module+m.plan['targets']['mission_temp_owner'],OWNER)
    m.page(m.module+m.plan['targets']['soul_familiarity_min'])
    m.put32(m.module+m.plan['targets']['soul_familiarity_min'],300)
    m.cpu.mem_write(b.COMP+0x9CC,bytes([selector]))
    for i in range(2):
        m.put32(OWNER+0xB52B4+4*i,indices[i])
        m.put32(GEAR[i],(19388,8311)[i])
        m.put32(GEAR[i]+0x14,familiarity[i])
        m.put64(GEAR[i]+0x30,0x100+i)
    m.put32(b.COMP+0x128,15347);m.put32(b.COMP+0x13C,0)
    m.put32(b.COMP+0x1F0,-1)
    m.events.clear();m.writes.clear()

class Cast(n.Machine):
    def __init__(self,p,layout=b.LAYOUTS[0]):
        with patch.object(n,'ITEMS',n.ITEMS+(SOUL,)):
            super().__init__(p,SOUL[0],layout)
        equipment(self)

class SoulTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=n.h.apply_nine_talismans(n.reuse.apply_dispersal_reuse(n.sticky.apply_sticky_dispersal_items(load_plan())))
        cls.plan=soul.apply_soul_release(cls.parent)

    def entry(self,m,ok):
        before=m.protected_snapshot();regs={}
        m.invoke(m.code+soul.spells.HELPER_OFFSET,lambda:regs.update({r:m.cpu.reg_read(r) for r in b.REGISTERS}))
        regs[UC_X86_REG_RSP]=b.STACK
        self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs)
        self.assertEqual(m.protected_snapshot(),before)
        self.assertEqual([e for e in m.events if e[0]=='dispatch'],[('dispatch',b.CONTROLLER,42)] if ok else [])

    def test_owned_equipment_threshold_both_slots_and_fallback(self):
        for layout in b.LAYOUTS:
            for selector,indices,slot in ((1,(5,191),0),(0,(5,191),1),(1,(700,191),1),(0,(5,700),0)):
                for value in (0,29999,30000,99900):
                    m=Cast(self.plan,layout);fam=[0,0];fam[slot]=value
                    equipment(m,selector,indices,tuple(fam));self.entry(m,value>=30000)
        for indices in ((700,700),(701,191),(5,701)):
            m=Cast(self.plan);equipment(m,0 if indices[1]==701 else 1,indices);self.entry(m,False)

    def test_exact_definition_ownership_and_dead_requests_rejected(self):
        for off in (0,4,0x104,0x10C,0x110,0x114,0x118,0x11C):
            m=Cast(self.plan);at=n.old.dung.DEF+off;m.put32(at,m.get32(at)^1);self.entry(m,False)
        for at,value,width in ((b.META+0xC,0,4),(b.ACTOR+0xEF0,1,4),(b.COMP+0x20,0,8),
                (b.COMP+0x108,b.ACTOR+8,8),(b.CONTROLLER+0x54C,9,4),(b.CONTROLLER+0x570,1,1),
                (GEAR[0]+0x30,0,8),(b.COMP+0x9CC,2,1)):
            m=Cast(self.plan);m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)

    def test_common3025_alias_and_common42_never_boss42(self):
        for phase,pending in (('idle',1),('entry',0),('cast',0)):
            for requested in (42,3025):
                m=Cast(self.plan);m.phase(phase,pending)
                result,regs=m.lookup(action=requested)
                self.assertEqual(result,m.lookup_results[42]);self.assertEqual(m.get32(n.old.lookup.GROUP),2)
                regs[UC_X86_REG_RAX]=result;regs[UC_X86_REG_RSP]=b.STACK
                self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs)
        m=n.Machine(self.plan,52306);result,_=m.lookup(action=3025);self.assertEqual(result,0)

    def test_native_gate_uses_saved_gear_and_preserves_abi(self):
        for slot in (0,1):
            m=Cast(self.plan);equipment(m,1-slot)
            hook=m.by_name['HE_SoulReleaseEligibility'];m.reset()
            for r,v in ((UC_X86_REG_RBP,b.ACTOR),(UC_X86_REG_R14,n.old.dung.DEF),
                        (UC_X86_REG_RCX,(0x128,0x1F0)[slot]),(UC_X86_REG_RAX,b.COMP)):
                m.cpu.reg_write(r,v)
            before=m.protected_snapshot();regs={r:m.cpu.reg_read(r) for r in b.REGISTERS}
            m.run(hook['target'],hook['site']+hook['length'])
            regs[UC_X86_REG_RCX]=GEAR[slot];regs[UC_X86_REG_EFLAGS]=m.cpu.reg_read(UC_X86_REG_EFLAGS)
            self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs)
            self.assertEqual(m.protected_snapshot(),before)

    def test_unrelated_gate_and_projectile_keep_native_register_views(self):
        for wrong in ('definition','actor','template','dead'):
            m=Cast(self.plan);h=m.by_name['HE_SoulReleaseEligibility'];m.reset()
            if wrong=='definition':m.put32(n.old.dung.DEF,64628)
            if wrong=='template':m.put32(b.META+0xC,0)
            if wrong=='dead':m.put32(b.ACTOR+0xEF0,1)
            for r,v in ((UC_X86_REG_RBP,b.ACTOR+8 if wrong=='actor' else b.ACTOR),
                (UC_X86_REG_R14,n.old.dung.DEF),(UC_X86_REG_RCX,0x128),(UC_X86_REG_RAX,b.COMP)):
                m.cpu.reg_write(r,v)
            m.run(h['target'],h['site']+h['length'])
            self.assertEqual(m.cpu.reg_read(UC_X86_REG_RCX),b.COMP+0x128)
        for wrong in ('owner','template','kind','descriptor'):
            m=Cast(self.plan);h=m.by_name['HE_SoulReleaseFamiliarity']
            m.put32(PROJECTILE,0x5B261 if wrong=='template' else 0x5B260)
            m.put32(PROJECTILE+4,5 if wrong=='kind' else 4)
            m.put64(PROJECTILE+0x200,b.ACTOR+8 if wrong=='owner' else b.ACTOR)
            m.put64(ATTACK+0x28,PROJECTILE);m.put64(ATTACK,DESCRIPTOR+8 if wrong=='descriptor' else DESCRIPTOR)
            m.reset()
            for r,v in ((UC_X86_REG_RAX,0x128),(UC_X86_REG_RCX,b.COMP),(UC_X86_REG_R8,1),
                (UC_X86_REG_RBX,b.ACTOR),(UC_X86_REG_R15,PROJECTILE),(UC_X86_REG_RDI,ATTACK),
                (UC_X86_REG_R12,DESCRIPTOR)):
                m.cpu.reg_write(r,v)
            m.run(h['target'],h['site']+h['length'])
            self.assertEqual(m.cpu.reg_read(UC_X86_REG_RCX),b.COMP)

    def test_cast_gap_recast_and_existing_injury_path(self):
        g=n.old.gap
        with patch.object(g,'NEW_H',assemble(self.plan,g.BASE,g.ALLOC)):
            f=n.Gap(42).item(SOUL)
            self.assertEqual(f.run(0,1),1)
            self.assertEqual(f.run(77,0),1)
            self.assertEqual(f.run(77,0),0)
        with patch.object(n,'ITEMS',n.ITEMS+(SOUL,)):
            m=n.Recast(self.plan,64629);equipment(m)
        n.old.recast.ItemRecastLookupTests().checked(m,True)
        for source,target,index,first,count,raw in n.old.hurt.h.ROUTES:
            m=n.old.hurt.ItemHurtMachine(self.plan,action=42);m.select(source,index)
            n.old.hurt.ItemHurtLookupTests().checked(m,True,target=target)

    def test_native_damage_view_keeps_selected_consumption_and_all_other_registers(self):
        for selector,indices,slot in ((1,(5,191),0),(0,(5,191),1),(1,(700,191),1)):
            m=Cast(self.plan);equipment(m,selector,indices)
            for at,v in ((PROJECTILE,0x5B260),(PROJECTILE+4,4)) :m.put32(at,v)
            m.put64(PROJECTILE+0x200,b.ACTOR);m.put64(ATTACK+0x28,PROJECTILE);m.put64(ATTACK,DESCRIPTOR)
            h=m.by_name['HE_SoulReleaseFamiliarity'];m.reset()
            offset=0x128 if selector else 0x1F0
            for r,v in ((UC_X86_REG_RAX,offset),(UC_X86_REG_RCX,b.COMP),(UC_X86_REG_R8,selector),
                (UC_X86_REG_RBX,b.ACTOR),(UC_X86_REG_R15,PROJECTILE),(UC_X86_REG_RDI,ATTACK),
                (UC_X86_REG_R12,DESCRIPTOR),(UC_X86_REG_R10,4),(UC_X86_REG_R11,0)):
                m.cpu.reg_write(r,v)
            before=m.protected_snapshot();regs={r:m.cpu.reg_read(r) for r in b.REGISTERS}
            m.run(h['target'],h['site']+h['length'])
            regs[UC_X86_REG_RCX]=GEAR[slot]-offset;regs[UC_X86_REG_R8]=1-slot
            regs[UC_X86_REG_EFLAGS]=m.cpu.reg_read(UC_X86_REG_EFLAGS)
            self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},regs)
            self.assertEqual(m.protected_snapshot(),before)
            native_slot=0 if m.cpu.reg_read(UC_X86_REG_R8) else 1
            self.assertEqual(native_slot,slot)

    def test_owned_slot_partition_and_unchanged_native_consumers(self):
        hooks=assemble(self.plan,0x140000000,0x144000000)
        spans=sorted((h['code_offset'],h['code_offset']+h['code_capacity']) for h in hooks)
        for a,b_ in zip(spans,spans[1:]):self.assertLessEqual(a[1],b_[0])
        self.assertEqual([h['rva'] for h in hooks[-2:]],[0x766455,0x7E28A9])
        self.assertEqual(self.plan['allocation_size'],self.parent['allocation_size'])
        for h in hooks:self.assertLessEqual(len(h['payload']),h['code_capacity'])

if __name__=='__main__':unittest.main()
