"""Execute the repeat-cast path with synthetic owned movement and item banks."""
from copy import deepcopy
from pathlib import Path
import struct,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta61_plan as load_plan,assemble,relocation_specs
from hinoenma_spell_event_catchup import apply_spell_event_catchup
from hinoenma_item_hurt_lookup import apply_item_hurt_lookup,CALLERS
import hinoenma_item_recast_lookup as h
from test_wind_weakness_dragon_portable import SpellLookupMachine
import test_arrow_sloth_lookup_portable as lookup_tests
import test_item_hurt_lookup_portable as hurt_tests
from test_special_items_portable import DEFINITION
from portable_machine import b
from unicorn.x86_const import *

MOVE=b.ACTOR+0x38000
TABLE=b.ACTOR+0x39000

class RecastMachine(SpellLookupMachine):
    def __init__(self,plan,item=44930,layout=b.LAYOUTS[0]):
        super().__init__(plan,item,layout)
        self.motion_by_key.update({(slot,110):0 for slot in (2,6)})
        self.caller=CALLERS[1]
        for caller in (*CALLERS,0x1100800):self.page(self.module+caller)
        self.put32(MOVE,1003);self.put64(MOVE+0x20,MOVE+0x100)
        self.put64(MOVE+0x38,b.BANK);self.cpu.mem_write(MOVE+0x40,b'\1')
        self.put64(MOVE+0x78,TABLE);self.put32(MOVE+0x80,5897|(49<<16))
        self.put32(MOVE+0x120,20);self.put32(MOVE+0x134,-1)
        self.cpu.mem_write(MOVE+0x140,h.MOVEMENT_SCHEDULE)
        self.put64(b.BANK+0x50,TABLE);self.put64(b.VECTOR+16,MOVE);self.put32(b.BANK+0x130,3)
        self.put64(b.CONTROLLER+0x58,MOVE);self.put32(b.CONTROLLER+0x68,2)
        self.put32(b.CONTROLLER+0x554,0)
        self.mutation=None
    def invoke(self,address,setup=None):
        self.reset();self.cpu.reg_write(UC_X86_REG_RSP,b.STACK-8)
        self.put64(b.STACK-8,self.module+self.caller)
        if setup:setup()
        self.events.clear();self.writes.clear()
        self.run(address,stop=self.module+self.caller)
        return self.cpu.reg_read(UC_X86_REG_RAX)
    def trace(self,cpu,address,size,user):
        slot=None
        if self.callbacks.get(address)=='clip':
            ptr=cpu.reg_read(UC_X86_REG_RCX)
            slot=next((s for s,p in b.MAPS.items() if p==ptr),None)
        super().trace(cpu,address,size,user)
        if slot==6 and self.mutation:
            mutate=self.mutation;self.mutation=None;mutate(self)

class ItemRecastLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=apply_item_hurt_lookup(apply_spell_event_catchup(load_plan()))
        cls.plan=h.apply_item_recast_lookup(cls.parent)
    def checked(self,m,accepted):
        before=m.protected_snapshot()
        result,registers=m.lookup()
        expected=m.lookup_results[m.action] if accepted else lookup_tests.PRIVATE_RECORDS[m.action]
        self.assertEqual(result,expected)
        if accepted:
            registers[UC_X86_REG_RSP]=b.STACK
            registers[UC_X86_REG_RAX]=expected
            self.assertEqual({r:m.cpu.reg_read(r) for r in b.REGISTERS},registers)
            self.assertFalse(m.fallback_registers)
            self.assertEqual(m.native_search_count,0)
        else:
            self.assertTrue(m.fallback_registers)
            self.assertEqual(m.fallback_registers[0],registers)
            self.assertEqual(m.native_search_count,1)
        expected_snapshot=deepcopy(before)
        actor=bytearray(expected_snapshot[b.ACTOR])
        struct.pack_into('<I',actor,lookup_tests.GROUP-b.ACTOR,2 if accepted else 1)
        expected_snapshot[b.ACTOR]=bytes(actor)
        self.assertEqual(m.protected_snapshot(),expected_snapshot)
        # Retained Salt cleanup clears its own token on some fallback paths.
        # These exact instruction/write pairs are outside the new guard and
        # are compared against the installed parent below; no actor writes.
        cleanup={(0xC30D,0x13F00,8),(0xC30D,0x13F08,8),
                 (0xC312,0x13F10,8),(0xC312,0x13F18,8),
                 (0xC318,0x13F20,8),(0xC318,0x13F28,8),
                 (0xC31E,0x13F30,8),(0xC31E,0x13F38,8)}
        extras=[]
        for ip,at,size in m.writes:
            if 0x20000000<=at and at+size<=0x20010000:continue
            if at==lookup_tests.GROUP and size==4:continue
            extras.append((ip-m.code,at-m.code,size))
        self.assertTrue(not extras or (not accepted and set(extras)==cleanup),extras)
        return result
    def test_original_moving_recast_collision_and_new_path(self):
        for item in (44930,4998,64367):
            self.checked(RecastMachine(self.parent,item),False)
            self.checked(RecastMachine(self.plan,item),True)
    def test_native_callers_three_aslr_layouts_full_abi(self):
        for layout in b.LAYOUTS:
            for caller in CALLERS:
                for item in (44930,4998,64367):
                    m=RecastMachine(self.plan,item,layout);m.caller=caller;self.checked(m,True)
    def test_unrelated_caller_private_motion_and_missing_request_rejected(self):
        m=RecastMachine(self.plan);m.caller=0x1100800;self.checked(m,False)
        for at,val,width in ((MOVE,1002,4),(MOVE+0x120,21,4),(MOVE+0x134,0,4),
            (MOVE+0x78,0,8),(MOVE+0x80,0,4),(MOVE+0x38,b.OWN_BANK,8),(MOVE+0x40,0,1),
            (b.CONTROLLER+0x68,1,4),(b.CONTROLLER+0x548,0xffffffff,4),
            (b.CONTROLLER+0x550,0,4),(b.CONTROLLER+0x570,1,1),(DEFINITION+0x104,0,4),
            (b.BANK+0x50,0,8),(b.VECTOR+16,0,8)):
            m=RecastMachine(self.plan);m.cpu.mem_write(at,val.to_bytes(width,'little'));self.checked(m,False)
        m=RecastMachine(self.plan);m.put64(b.VECTOR+24,MOVE);m.put32(b.BANK+0x130,4);self.checked(m,False)
        for off in range(96):
            m=RecastMachine(self.plan);at=MOVE+0x140+off
            m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.checked(m,False)
    def test_after_callback_movement_guard_rechecked(self):
        for at,val in ((MOVE+0x80,0),(MOVE+0x120,21),(MOVE+0x140,0),(b.CONTROLLER+0x68,1)):
            m=RecastMachine(self.plan);m.mutation=lambda m,at=at,val=val:m.put32(at,val)
            # The fixture mutation itself is the only actor write here.
            result,_=m.lookup()
            self.assertEqual(result,lookup_tests.PRIVATE_RECORDS[42])
            self.assertTrue(m.fallback_registers)
    def test_fallback_cleanup_matches_installed_parent(self):
        for phase in ('moving','boss'):
            results=[]
            for plan in (self.parent,self.plan):
                m=RecastMachine(plan)
                if phase=='boss':m.phase('boss',0)
                else:m.put32(m.code+0xF000+0x1C,0) # Reject before either lookup.
                m.cpu.mem_write(m.code+0x13F00,b'\xA7'*0x40)
                result=self.checked(m,False)
                results.append((result,m.protected_snapshot(),
                    bytes(m.cpu.mem_read(m.code+0x13F00,0x40)),
                    {r:m.cpu.reg_read(r) for r in b.REGISTERS},
                    [(ip-m.code,at-m.code,size) for ip,at,size in m.writes
                     if m.code+0x13F00<=at<m.code+0x13F40]))
            self.assertEqual(*results)
    def test_common_item_injury_routes_still_resolve_in_combined_candidate(self):
        checker=hurt_tests.ItemHurtLookupTests()
        for action in hurt_tests.h.CAST_MOTIONS:
            for source,target,index,first,count,raw in hurt_tests.h.ROUTES:
                m=hurt_tests.ItemHurtMachine(self.plan,action=action)
                m.select(source,index)
                checker.checked(m,True,target=target)
    def test_other_lookup_phases_and_existing_interruption_prefix_unchanged(self):
        for phase,pending in (('idle',1),('entry',0),('entry',1),('cast',0)):
            m=RecastMachine(self.plan);m.phase(phase,pending);self.checked(m,True)
        for phase in ('boss',):
            m=RecastMachine(self.plan);m.phase(phase,0);self.checked(m,False)
        for layout in b.LAYOUTS:
            old,new=assemble(self.parent,*layout),assemble(self.plan,*layout)
            changed=[]
            for a,z in zip(old,new):
                self.assertEqual(a['patched'],z['patched'])
                if a['payload']!=z['payload']:changed.append(a['name'])
                if a['name']==h.GUARD_CARRIER:self.assertTrue(z['payload'].startswith(a['payload']))
                if a['name']==h.CARRIER:
                    self.assertEqual(a['payload'][:0x5800],z['payload'][:0x5800])
                    self.assertEqual(a['payload'][0x6C00:],z['payload'][0x6C00:])
            self.assertEqual(tuple(changed),h.CHANGED)
        self.assertEqual(len(relocation_specs(self.plan)),82)
        self.assertEqual(h.apply_item_recast_lookup(self.parent),self.plan)
        bad=deepcopy(self.parent);bad['tool_version']='other'
        with self.assertRaises(ValueError):h.apply_item_recast_lookup(bad)

if __name__=='__main__':unittest.main()
