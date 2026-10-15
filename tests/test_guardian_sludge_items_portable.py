"""Execute new item entry guards against observed definitions and ABI stubs."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta61_plan as load_plan,assemble,relocation_specs
from hinoenma_spell_event_catchup import apply_spell_event_catchup
from hinoenma_item_hurt_lookup import apply_item_hurt_lookup
from hinoenma_item_recast_lookup import apply_item_recast_lookup
import hinoenma_guardian_sludge_items as h
import hinoenma_special_item_actions as special
import test_dung_fan_portable as dung
from portable_machine import b

# Separate fixed observations; the native definition data was read on 2026-10-15.
OBSERVED=((62705,2,15,22,0x2005,(0,0,0),0xC2626,610,111,286),
          (20527,1,0,4,0x10005,(0,0,0),0xD890A,165,103,100))

class GuardianSludgeMachine(dung.DungFanMachine):
    def __init__(self,plan,item,layout=b.LAYOUTS[0]):
        with patch.multiple(dung,ITEM_SPECS=special.ITEM_SPECS+OBSERVED,
                SCHEDULE_HEX=special.SCHEDULE_HEX,EVENT_GUARDS=special.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class GuardianSludgeItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=apply_item_recast_lookup(apply_item_hurt_lookup(apply_spell_event_catchup(load_plan())))
        cls.plan=h.apply_guardian_sludge_items(cls.parent)
    def check(self,m,accepted):
        dung.DungFanPortableTests().checked_entry(m,accepted,special.HELPER_OFFSET)
    def test_old_rejects_and_new_accepts_observed_items_with_full_abi(self):
        self.assertEqual(h.ITEM_SPECS,OBSERVED)
        for row in OBSERVED:self.check(GuardianSludgeMachine(self.parent,row[0]),False)
        for layout in b.LAYOUTS:
            for template in (0x58E5E,0x51BE1):
                for item,*_,action,motion,query in OBSERVED:
                    m=GuardianSludgeMachine(self.plan,item,layout)
                    for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                    self.check(m,True)
                    self.assertEqual(m.events,[('definition',item),('lookup',172),('lookup',action),
                        ('clip',2,motion),('clip',6,motion),('dispatch',b.CONTROLLER,172)])
    def test_exact_definition_and_request_identity_required(self):
        for item,*_ in OBSERVED:
            for off,width in ((0,4),(4,1),(5,1),(0x104,4),(0x10C,4),(0x110,4),(0x114,4),(0x118,4),(0x11C,4)):
                m=GuardianSludgeMachine(self.plan,item);at=dung.DEF+off
                v=int.from_bytes(m.cpu.mem_read(at,width),'little')^1
                m.cpu.mem_write(at,v.to_bytes(width,'little'));self.check(m,False)
            for at,val,width in ((b.CONTROLLER+0x548,999,4),(b.CONTROLLER+0x54C,99,4),
                (b.CONTROLLER+0x550,2,4),(b.CONTROLLER+0x555,0,1),(b.CONTROLLER+0x556,1,1),
                (b.CONTROLLER+0x558,1,8),(b.CONTROLLER+0x570,1,1),(b.CONTROLLER+0x728,1,8),
                (b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,1,4),(b.META+0xC,0,4),
                (b.COMP+0x20,0,8),(b.PROXY+8,0,8),(b.CONTROLLER+0x50,0,8),(b.CURRENT,1,4)):
                m=GuardianSludgeMachine(self.plan,item);m.cpu.mem_write(at,val.to_bytes(width,'little'));self.check(m,False)
            m=GuardianSludgeMachine(self.plan,item);m.definition_result=0;self.check(m,False)
    def test_schedule_descriptors_and_both_native_motion_slots(self):
        for item,*_,action,motion,query in OBSERVED:
            for off in range(96):
                m=GuardianSludgeMachine(self.plan,item);at=m.lookup_results[action]+0xC0+off
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.check(m,False)
            for index,*_ in special.EVENT_GUARDS[action]:
                at=(dung.old_items.GLOBAL_EVENTS+(index-10000)*0x80 if index>=10000 else b.ACTOR+0xA1000+index*0x80)
                for off in (0x17,0x18,0x1C,0x3F,0x2A,0x52):
                    m=GuardianSludgeMachine(self.plan,item)
                    m.cpu.mem_write(at+off,bytes([m.cpu.mem_read(at+off,1)[0]^1]));self.check(m,False)
            for slot in (2,6):
                m=GuardianSludgeMachine(self.plan,item);m.put64(b.CLIPS[slot],0);self.check(m,False)
    def test_callback_changes_to_definition_records_or_dialog_reject(self):
        for item,*_,action,motion,query in OBSERVED:
            for kind in ('definition','schedule','motion','params','owner','disabled','duplicate','missing','dialog','epoch'):
                m=GuardianSludgeMachine(self.plan,item);target=m.lookup_results[action]
                def mutate(m,name):
                    if name!='clip' or m.events[-1][1]!=6:return
                    if kind=='definition':m.put32(dung.DEF+0x11C,0)
                    elif kind=='schedule':m.put32(target+0xC0,0)
                    elif kind=='motion':m.put32(target+0xA0,0)
                    elif kind=='params':m.put64(target+0x20,0)
                    elif kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                    elif kind=='disabled':m.cpu.mem_write(target+0x40,b'\0')
                    elif kind=='duplicate':m.put64(b.VECTOR+16,target);m.put32(b.BANK+0x130,3)
                    elif kind=='missing':m.put64(b.VECTOR+8,0)
                    elif kind=='dialog':m.cpu.mem_write(b.CONTROLLER+0x570,b'\1')
                    else:m.put32(m.data+0x1C,0)
                m.mutate_on_call=mutate;m.invoke(m.code+special.HELPER_OFFSET)
                self.assertFalse(any(e[0]=='dispatch' for e in m.events),(item,kind))
    def test_existing_six_items_still_dispatch_and_new_targets_are_unique(self):
        for row in special.ITEM_SPECS:self.check(GuardianSludgeMachine(self.plan,row[0]),True)
        for item,*_,action,motion,query in OBSERVED:
            for kind in ('owner','disabled','duplicate','missing','count'):
                m=GuardianSludgeMachine(self.plan,item);target=m.lookup_results[action]
                if kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                elif kind=='disabled':m.cpu.mem_write(target+0x40,b'\0')
                elif kind=='duplicate':m.put64(b.VECTOR+16,target);m.put32(b.BANK+0x130,3)
                elif kind=='missing':m.put64(b.VECTOR+8,0)
                else:m.put32(b.BANK+0x130,4097)
                self.check(m,False)
    def test_two_owned_payloads_fixed_entries_and_existing_repairs_preserved(self):
        before=deepcopy(self.parent);self.assertEqual(h.apply_guardian_sludge_items(self.parent),self.plan);self.assertEqual(before,self.parent)
        for layout in b.LAYOUTS:
            old,new=assemble(self.parent,*layout),assemble(self.plan,*layout);changed=[]
            for a,z in zip(old,new):
                for field in ('site','patched','original','target','code_offset','code_capacity'):
                    self.assertEqual(a[field],z[field])
                if a['payload']!=z['payload']:changed.append(a['name'])
                if a['name']==h.GUARD_CARRIER:self.assertTrue(z['payload'].startswith(a['payload']))
                if a['name']==h.ENTRY_CARRIER:
                    self.assertEqual(a['payload'][:0x200],z['payload'][:0x200])
                    self.assertEqual(a['payload'][0x1300:],z['payload'][0x1300:])
                self.assertLessEqual(len(z['payload']),z['code_capacity'])
            self.assertEqual(tuple(changed),h.CHANGED)
        self.assertEqual(len(relocation_specs(self.plan)),82)
        bad=deepcopy(self.parent);bad['tool_version']='other'
        with self.assertRaises(ValueError):h.apply_guardian_sludge_items(bad)

if __name__=='__main__':unittest.main()
