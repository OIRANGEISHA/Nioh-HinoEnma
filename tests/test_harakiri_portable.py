"""Synthetic native lookup stubs: predicate/ABI tests, not gameplay proof."""
from pathlib import Path
import sys,struct,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta563_plan as load_plan,assemble
from hinoenma_harakiri import apply_harakiri,HELPER_OFFSET,CARRIER_NAME,CHANGED_HOOKS
from portable_machine import PortableMachine,b
from unicorn.x86_const import *
DEF,FX,ASSETS,ITEMS,EFFECTS,ITABLE,FTABLE=(b.ACTOR+x for x in (0x90000,0x90400,0x91000,0x92000,0x93000,0x94000,0x95000))

class GateMachine(PortableMachine):
    def __init__(self,plan,layout=b.LAYOUTS[0]):
        super().__init__(plan,layout)
        self.put32(b.CONTROLLER+0x548,34209);self.put32(b.CONTROLLER+0x54C,10)
        self.put32(b.CONTROLLER+0x550,1);self.put32(b.CONTROLLER+0x554,0x100)
        for off,value in ((0,34209),(4,3),(0x104,0x4047),(0x10C,10),(0x110,29595),(0x11C,0x8A25D)):
            self.put32(DEF+off,value)
        for off,value in ((0,29595),(4,15),(0x10,100),(0x1C,100)):self.put32(FX+off,value)
        slot=self.module+plan['targets']['item_assets'];self.page(slot);self.put64(slot,ASSETS)
        for at,val in ((ASSETS+0x20,ITEMS),(ASSETS+0x148,EFFECTS),(ITEMS+0x428,ITABLE),(EFFECTS+0x428,FTABLE)):self.put64(at,val)
        for key in ('item_lookup','effect_lookup'):
            at=self.module+plan['targets'][key];self.page(at);self.cpu.mem_write(at,b'\xC3');self.callbacks[at]=key
        self.item_result=DEF;self.effect_result=FX;self.mutate_on_lookup=None
        self.gate=self.by_name['HE_Consumables'];self.destination=None
        self.ends={self.module+plan['targets']['item_use_ready']:'ready',self.gate['site']+self.gate['length']:'original'}
    def trace(self,cpu,address,size,user):
        if address in self.ends:
            self.destination=self.ends[address];self.reached=True;cpu.emu_stop();return
        name=self.callbacks.get(address)
        if name in ('item_lookup','effect_lookup'):
            rsp=cpu.reg_read(UC_X86_REG_RSP)
            if rsp%16!=8:raise AssertionError('Unaligned native lookup')
            effect=name=='effect_lookup';expected=self.get32(FX if effect else DEF)
            # Definition-ID mutation tests intentionally request a different ID.
            request=self.get32(DEF+0x110) if effect else self.get32(b.CONTROLLER+0x548)
            if cpu.reg_read(UC_X86_REG_EDX)!=request:raise AssertionError('Wrong native lookup ID')
            if cpu.reg_read(UC_X86_REG_RCX)!=(FTABLE if effect else ITABLE):raise AssertionError('Wrong table')
            self.events.append((name,request))
            if self.mutate_on_lookup:self.mutate_on_lookup(self,name)
            cpu.mem_write(rsp+8,b'\xA5'*32)
            for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11,*b.XMMS[:6]):cpu.reg_write(r,0xDEADBEEF)
            cpu.reg_write(UC_X86_REG_EFLAGS,0x202)
            cpu.reg_write(UC_X86_REG_RAX,self.effect_result if effect else self.item_result)
            return
        super().trace(cpu,address,size,user)

class HarakiriTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=load_plan();cls.plan=apply_harakiri(cls.old)
    def check(self,m,wanted):
        m.reset();m.cpu.reg_write(UC_X86_REG_EFLAGS,0x247)
        regs={r:m.cpu.reg_read(r) for r in b.REGISTERS if r!=UC_X86_REG_EFLAGS}
        before=m.protected_snapshot();m.events.clear();m.writes.clear()
        m.run(m.gate['target'])
        self.assertEqual(m.destination,'ready' if wanted else 'original')
        self.assertEqual({r:m.cpu.reg_read(r) for r in regs},regs)
        if self.get_category(m)==10:self.assertEqual(m.cpu.reg_read(UC_X86_REG_EFLAGS),0x206)
        after=m.protected_snapshot()
        if wanted and self.get_category(m)!=0:
            data=bytearray(before[m.data]);struct.pack_into('<II',data,0x50,1,self.get_item(m));before[m.data]=bytes(data)
        self.assertEqual(after,before)
        self.assertTrue(all(0x20000000<=at<0x20010000 or at in (m.data+0x50,m.data+0x54) for _,at,_ in m.writes))
    @staticmethod
    def get_category(m):return m.get32(b.CONTROLLER+0x54C)
    @staticmethod
    def get_item(m):return m.get32(b.CONTROLLER+0x548)
    def test_confirmed_exact_item_both_player_templates_three_layouts(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E,0x51BE1):
                m=GateMachine(self.plan,layout)
                for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                self.check(m,True)
    def test_original_bug_is_reproduced(self):self.check(GateMachine(self.old),False)
    def test_reject_unconfirmed_cancelled_foreign_dead_and_mixed_effects(self):
        changes=((b.CONTROLLER+0x548,34210,4),(b.CONTROLLER+0x550,2,4),
            (b.CONTROLLER+0x555,0,1),(b.CONTROLLER+0x555,2,1),(b.CONTROLLER+0x554,1,1),
            (b.CONTROLLER+0x556,1,1),(b.CONTROLLER+0x557,1,1),(b.CONTROLLER+0x570,1,1),
            (b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,-1,4),(b.META+0xC,0,4),
            (b.PROXY+8,b.CONTROLLER+0x100,8),(b.COMP+0x108,b.ACTOR+0x100,8),(b.COMP+0x20,0,8),
            (DEF,34210,4),(DEF+4,1,2),(DEF+0x104,0,4),(DEF+0x10C,1,4),
            (DEF+0x114,1234,4),(DEF+0x118,1234,4),(DEF+0x11C,0,4),
            (FX,29596,4),(FX+4,14,4),(FX+8,1,4),(FX+0x10,99,4),(FX+0x14,1,4),
            (FX+0x1C,99,4),(FX+0x20,1,4),(FX+0x28,1,4))
        for at,value,width in changes:
            with self.subTest(address=hex(at),value=value):
                m=GateMachine(self.plan);m.cpu.mem_write(at,(value%(1<<(width*8))).to_bytes(width,'little'));self.check(m,False)
        for kind in ('item_result','effect_result'):
            m=GateMachine(self.plan);setattr(m,kind,0);self.check(m,False)
        m=GateMachine(self.plan);m.put64(m.module+self.plan['targets']['player_slot'],b.ACTOR+0x100);self.check(m,False)
        m=GateMachine(self.plan);m.put64(m.data+0x10,b.ACTOR+0x100);self.check(m,False)
    def test_owner_or_request_change_during_native_lookup_rejects(self):
        for what in ('owner','request'):
            m=GateMachine(self.plan)
            def mutation(m,name):
                if name=='effect_lookup':
                    if what=='owner':m.put64(m.module+self.plan['targets']['player_slot'],b.ACTOR+0x100)
                    else:m.put32(b.CONTROLLER+0x555,0)
            m.mutate_on_lookup=mutation;m.reset();m.run(m.gate['target'])
            self.assertEqual(m.destination,'original');self.assertEqual(m.get32(m.data+0x50),0)
    def test_existing_talismans_and_unrelated_categories_preserve_routing(self):
        for category in (0,1,2,3,4,6,7,8,9,11,13,22,27,0xFFFFFFFF):
            destinations=[]
            for plan in (self.old,self.plan):
                m=GateMachine(plan);m.put32(b.CONTROLLER+0x54C,category);m.put32(DEF+0x10C,category)
                if category in (7,8):
                    ident,effect,typ=(52207,8969,14) if category==7 else (44216,22914,3)
                    m.put32(DEF,ident);m.put32(b.CONTROLLER+0x548,ident);m.put32(DEF+4,0xF01)
                    m.put32(DEF+0x110,effect);m.put32(FX,effect);m.put32(FX+4,typ)
                m.reset();m.run(m.gate['target']);destinations.append((m.destination,m.events,m.get32(m.data+0x50)))
            self.assertEqual(*destinations)
    def test_only_two_private_payloads_change_all_native_sites_preserved(self):
        for layout in b.LAYOUTS:
            old,new=assemble(self.old,*layout),assemble(self.plan,*layout)
            self.assertEqual(tuple(a['name'] for a,c in zip(old,new) if a['payload']!=c['payload']),CHANGED_HOOKS)
            for a,c in zip(old,new):
                for key in ('site','target','original','patched','code_offset','code_capacity'):self.assertEqual(a[key],c[key])
                if a['name']==CARRIER_NAME:self.assertEqual(c['payload'][:len(a['payload'])],a['payload'])
            self.assertEqual(len(new),82)
        with self.assertRaises(ValueError):apply_harakiri(self.plan)

if __name__=='__main__':unittest.main()
