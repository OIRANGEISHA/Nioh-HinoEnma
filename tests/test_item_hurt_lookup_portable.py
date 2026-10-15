"""CPU checks for item interruption bank resolution, without a game process.

Action records and the bank-search fallback are synthetic. The new wrapper,
native-clip guard and selected-record checks execute as actual assembly.
Native damage, queries, visuals and item effects do not execute in this suite.
"""
from copy import deepcopy
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import load_beta61_plan as load_plan, assemble, relocation_specs
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_spell_event_catchup import apply_spell_event_catchup
import hinoenma_item_hurt_lookup as h
from portable_machine import PortableMachine, b
from test_arrow_sloth_lookup_portable import NATIVE_BANK_SEARCH
from unicorn.x86_const import *

TABLE, UNIQUE, ENTRIES, OUTPUT = (b.ACTOR+x for x in (0xF0000,0xE0000,0xE1000,0xD8000))
PRIVATE_VECTOR = b.ACTOR+0xD9000
EXTRA = b.ACTOR+0xDA000
MOTIONS = {0:0, **h.INJURY_MOTIONS, **h.CAST_MOTIONS}


class ItemHurtMachine(PortableMachine):
    def __init__(self, plan, layout=b.LAYOUTS[0], action=1165):
        super().__init__(plan, layout)
        self.records, self.entries, self.private = {}, {}, {}
        headers = {s:(f,c) for s,t,i,f,c,raw in h.ROUTES}
        for i,(ident,motion) in enumerate(MOTIONS.items()):
            at = b.ACTOR+0xC0000+i*0x200
            self.records[ident]=at
            self.put64(b.VECTOR+i*8,at)
            self.put32(at,ident); self.put64(at+0x20,at+0x100)
            self.put64(at+0x38,b.BANK); self.cpu.mem_write(at+0x40,b'\1')
            self.put64(at+0x78,TABLE)
            self.cpu.mem_write(at+0x80,struct.pack('<HH',*headers.get(ident,(0,1))))
            self.put32(at+0x120,motion)
            if ident in h.SCHEDULES:
                self.cpu.mem_write(at+0x140,bytes.fromhex(h.SCHEDULES[ident]))
        self.put32(b.BANK+0x130,len(self.records))
        self.put64(b.BANK+0x50,TABLE)
        self.cpu.mem_write(b.BANK+0x58,struct.pack('<HH',0x4000,0x3FFF))
        self.put64(b.BANK+0x60,UNIQUE)
        aliases={}
        for source,target,index,first,count,raw in h.ROUTES:
            if raw not in aliases:
                aliases[raw]=ENTRIES+len(aliases)*48
                self.cpu.mem_write(aliases[raw],raw)
            at=aliases[raw]; self.entries[source,index]=at
            self.put64(TABLE+index*8,at)
        for i,at in enumerate(aliases.values()): self.put64(UNIQUE+i*8,at)
        self.cpu.mem_write(b.BANK+0x68,struct.pack('<HH',len(aliases),len(aliases)))
        for i,ident in enumerate(sorted(set(row[1] for row in h.ROUTES))):
            at=b.ACTOR+0xD0000+i*0x100
            self.private[ident]=at; self.put64(PRIVATE_VECTOR+i*8,at)
            self.put32(at,ident); self.cpu.mem_write(at+0x40,b'\1')
            self.put64(at+0x38,b.OWN_BANK)
        self.put64(b.OWN_BANK+0x128,PRIVATE_VECTOR)
        self.put32(b.OWN_BANK+0x130,len(self.private))
        self.put32(b.CONTROLLER+0x68,2)
        for slot in (2,6): self.put64(b.RES[slot]+0x470,b.CLIPS[slot]+8)
        raw,_=Ks(KS_ARCH_X86,KS_MODE_64).asm(NATIVE_BANK_SEARCH,self.code+h.FALLBACK_OFFSET)
        self.cpu.mem_write(self.code+h.FALLBACK_OFFSET,bytes(raw))
        for caller in (*h.CALLERS,0x1100800): self.page(self.module+caller)
        self.current(action); self.select(151,2604)
        self.fallback_registers=[]

    def current(self, action): self.put64(b.CONTROLLER+0x58,self.records[action])
    def select(self, source, index): self.put64(b.CONTROLLER+0x90,self.entries[source,index])

    def trace(self,cpu,address,size,user):
        if address==self.code+h.FALLBACK_OFFSET:
            self.fallback_registers.append({r:cpu.reg_read(r) for r in b.REGISTERS})
        super().trace(cpu,address,size,user)

    def lookup(self, target=89, caller=h.CALLERS[1], output=True, foreign=False):
        self.reset(); self.fallback_registers=[]; self.events.clear(); self.writes.clear()
        self.cpu.reg_write(UC_X86_REG_RSP,b.STACK-8)
        self.put64(b.STACK-8,self.module+caller)
        self.cpu.reg_write(UC_X86_REG_RCX,b.CONTROLLER+(0x1070 if foreign else 0x70))
        self.cpu.reg_write(UC_X86_REG_EDX,target)
        self.cpu.reg_write(UC_X86_REG_R8,OUTPUT if output else 0)
        self.put32(OUTPUT,0xA5A5A5A5)
        before=self.protected_snapshot()
        private=bytes(self.cpu.mem_read(self.code+0x13000,0x1000))
        registers={r:self.cpu.reg_read(r) for r in b.REGISTERS}
        self.run(self.by_name[h.ENTRY]['target'],stop=self.module+caller)
        expected=deepcopy(before)
        actor=bytearray(expected[b.ACTOR])
        actor[OUTPUT-b.ACTOR:OUTPUT-b.ACTOR+4]=self.cpu.mem_read(OUTPUT,4)
        expected[b.ACTOR]=bytes(actor)
        if self.protected_snapshot()!=expected or private!=bytes(self.cpu.mem_read(self.code+0x13000,0x1000)):
            raise AssertionError('Unexpected actor/item/input/shared-state write')
        if not all(0x20000000<=at<at+size<=0x20010000 or output and at==OUTPUT and size==4
                   for pc,at,size in self.writes):
            raise AssertionError('Unexpected non-stack/non-bank-result write')
        return self.cpu.reg_read(UC_X86_REG_RAX), registers


class ItemHurtLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=apply_spell_event_catchup(load_plan())
        cls.plan=h.apply_item_hurt_lookup(cls.parent)

    def checked(self,m,accepted,**args):
        target=args.get('target',89); output=args.get('output',True)
        result,registers=m.lookup(**args)
        expected=m.records[target] if accepted else m.private.get(target,0)
        if args.get('foreign'): expected=0
        self.assertEqual(result,expected)
        if accepted:
            self.assertEqual(m.fallback_registers,[])
            registers[UC_X86_REG_RSP]=b.STACK
            registers[UC_X86_REG_RAX]=expected
            self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},registers)
            self.assertEqual([e for e in m.events if e[0]=='clip'],
                [('clip',2,h.INJURY_MOTIONS[target]),('clip',6,h.INJURY_MOTIONS[target])])
        else:
            self.assertEqual(m.fallback_registers,[registers])
        if output:
            self.assertEqual(m.get32(OUTPUT),2 if accepted else 1 if expected else 0xA5A5A5A5)
        else: self.assertEqual(m.get32(OUTPUT),0xA5A5A5A5)

    def test_each_supported_item_cast_uses_all_selected_native_leaves(self):
        for action in h.CAST_MOTIONS:
            for source,target,index,first,count,raw in h.ROUTES:
                with self.subTest(action=action,target=target,index=index):
                    m=ItemHurtMachine(self.plan,action=action); m.select(source,index)
                    self.checked(m,True,target=target)

    def test_callers_templates_aslr_and_null_bank_output_preserve_abi(self):
        for layout in b.LAYOUTS:
            for caller in h.CALLERS:
                for template in (0x58E5E,0x51BE1):
                    for output in (False,True):
                        m=ItemHurtMachine(self.plan,layout)
                        for at in (b.ACTOR,b.META,m.data+4): m.put32(at,template)
                        self.checked(m,True,caller=caller,output=output)

    def test_consecutive_native_injury_can_continue_without_persistent_token(self):
        for action in h.INJURY_MOTIONS:
            m=ItemHurtMachine(self.plan,action=action)
            self.checked(m,True)
            m.current(89); m.select(151,2602)
            self.checked(m,True,target=87)

    def test_normal_skills_idle_unrelated_callers_and_role_mismatches_fall_through(self):
        m=ItemHurtMachine(self.plan,action=0); self.checked(m,False)
        m=ItemHurtMachine(self.plan); self.checked(m,False,caller=0x1100800)
        m=ItemHurtMachine(self.plan); self.checked(m,False,foreign=True)
        for action in (87,88,89):
            m=ItemHurtMachine(self.plan)
            m.put64(b.CONTROLLER+0x58,m.private[action]); m.put32(b.CONTROLLER+0x68,1)
            self.checked(m,False)
        for at,value,width in ((b.ACTOR,1,4),(b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,1,4),
            (b.META+0xC,0,4),(b.META,1,4),(b.COMP+0x20,0,8),(b.COMP,0,8),
            (b.COMP+0x108,0,8),(b.PROXY,0,8),(b.PROXY+8,0,8),(b.CONTROLLER+0x50,0,8),
            (b.CONTROLLER+0x68,1,4),(b.MOTION+0x50,2,4)):
            m=ItemHurtMachine(self.plan); m.cpu.mem_write(at,value.to_bytes(width,'little'))
            self.checked(m,False)
        for which in ('slot','recorded','epoch','template'):
            m=ItemHurtMachine(self.plan)
            at={'slot':m.module+self.plan['targets']['player_slot'],'recorded':m.data+0x10,
                'epoch':m.data+0x1C,'template':m.data+4}[which]
            m.cpu.mem_write(at,bytes(8 if which in ('slot','recorded') else 4))
            self.checked(m,False)

    def test_complete_selected_descriptor_and_full_cast_schedule_checked(self):
        for off in range(48):
            m=ItemHurtMachine(self.plan); at=m.entries[151,2604]+off
            m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1])); self.checked(m,False)
        for off in range(96):
            m=ItemHurtMachine(self.plan); at=m.records[1165]+0x140+off
            m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1])); self.checked(m,False)
        for action in h.CAST_MOTIONS:
            m=ItemHurtMachine(self.plan,action=action); m.put32(m.records[action]+0x120,999)
            self.checked(m,False)

    def test_unique_membership_ranges_owned_records_and_clips_required(self):
        for kind in ('source-range','source-array','source-motion','source-disabled','source-owner',
            'target-motion','target-disabled','target-owner','current-disabled','current-owner',
            'current-missing','current-duplicate','source-duplicate','target-duplicate',
            'selected-null','selected-unowned','selected-wrong-index','unique-empty',
            'bad-count','bad-transition-count','bad-unique-count','slot2','slot6'):
            with self.subTest(kind=kind):
                m=ItemHurtMachine(self.plan); source=m.records[151]; target=m.records[89]; current=m.records[1165]
                if kind=='source-range': m.put32(source+0x80,0x10001)
                elif kind=='source-array': m.put64(source+0x78,0)
                elif kind=='source-motion': m.put32(source+0x120,0)
                elif kind=='source-disabled': m.cpu.mem_write(source+0x40,b'\0')
                elif kind=='source-owner': m.put64(source+0x38,b.OWN_BANK)
                elif kind=='target-motion': m.put32(target+0x120,0)
                elif kind=='target-disabled': m.cpu.mem_write(target+0x40,b'\0')
                elif kind=='target-owner': m.put64(target+0x38,b.OWN_BANK)
                elif kind=='current-disabled': m.cpu.mem_write(current+0x40,b'\0')
                elif kind=='current-owner': m.put64(current+0x38,b.OWN_BANK)
                elif kind=='current-missing': m.put64(b.VECTOR+list(m.records).index(1165)*8,0)
                elif kind.endswith('duplicate'):
                    pointer={'current-duplicate':current,'source-duplicate':source,'target-duplicate':target}[kind]
                    m.put64(b.VECTOR+len(m.records)*8,pointer); m.put32(b.BANK+0x130,len(m.records)+1)
                elif kind=='selected-null': m.put64(b.CONTROLLER+0x90,0)
                elif kind=='selected-unowned': m.put64(b.BANK+0x60,EXTRA)
                elif kind=='selected-wrong-index': m.put64(TABLE+2604*8,0)
                elif kind=='unique-empty': m.cpu.mem_write(b.BANK+0x6A,b'\0\0')
                elif kind=='bad-count': m.put32(b.BANK+0x130,4097)
                elif kind=='bad-transition-count': m.cpu.mem_write(b.BANK+0x58,b'\0\0')
                elif kind=='bad-unique-count': m.cpu.mem_write(b.BANK+0x68,b'\0\0')
                else: m.put64(b.CLIPS[2 if kind=='slot2' else 6],0)
                self.checked(m,False)

    def test_exact_parent_geometry_other_hooks_and_existing_projectile_fix_preserved(self):
        saved=deepcopy(self.parent); self.assertEqual(h.apply_item_hurt_lookup(self.parent),self.plan)
        self.assertEqual(saved,self.parent)
        self.assertEqual(len(self.plan['hooks']),82)
        self.assertEqual(self.plan['allocation_size'],self.parent['allocation_size'])
        for layout in b.LAYOUTS:
            old,new=assemble(self.parent,*layout),assemble(self.plan,*layout)
            changed=[]
            for a,z in zip(old,new):
                self.assertEqual(a['patched'],z['patched'])
                self.assertLessEqual(len(z['payload']),z['code_capacity'])
                if a['payload']!=z['payload']: changed.append(a['name'])
                if a['name'] in (h.DATA_CARRIER,h.CODE_CARRIER):
                    self.assertEqual(z['payload'][:len(a['payload'])],a['payload'])
            self.assertEqual(set(changed),set(h.CHANGED))
            raw=next(x['payload'] for x in new if x['name']==h.DATA_CARRIER)
            self.assertEqual(raw[0x200:],h.TABLE_BYTES)
        bad=deepcopy(self.parent); bad['tool_version']='other'
        with self.assertRaises(ValueError): h.apply_item_hurt_lookup(bad)
        specs=relocation_specs(self.plan)
        # Runtime relocation must not disassemble the native descriptor data.
        self.assertIsInstance(specs,list)


if __name__=='__main__': unittest.main()
