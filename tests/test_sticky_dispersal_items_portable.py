"""CPU contracts for exact native item entry, bank choice and event dispatch.

Native effect generation is not emulated; it requires a live gameplay check.
"""
from copy import deepcopy
from pathlib import Path
import sys, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta612_plan as load_plan, assemble, relocation_specs
import hinoenma_sticky_dispersal_items as h
import hinoenma_special_item_actions as special
import hinoenma_wind_weakness_dragon as spells
import hinoenma_guardian_sludge_items as jars
import test_dung_fan_portable as dung
import test_arrow_sloth_portable as arrow
import test_arrow_sloth_lookup_portable as lookup
import test_wind_weakness_dragon_portable as wind
import test_item_recast_lookup_portable as recast
import test_item_hurt_lookup_portable as hurt
import test_spell_event_catchup_portable as gap
import test_elemental_resistance_items_portable as resistance
from portable_machine import b

# Independent failed-request observations, not generated from the candidate.
OBSERVED=((57901,1,0,4,65541,(0,0,0),141722,165,103,100),
          (22722,2,15,9,5,(0,0,0),998485,42,111,194))
SPELL_ITEMS=spells.ALL_ITEM_SPECS+(OBSERVED[1],)

class JarMachine(dung.DungFanMachine):
    def __init__(self,plan,item=57901,layout=b.LAYOUTS[0]):
        with patch.multiple(dung,ITEM_SPECS=special.ITEM_SPECS+jars.ITEM_SPECS+(OBSERVED[0],),
                            SCHEDULE_HEX=special.SCHEDULE_HEX,EVENT_GUARDS=special.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class SpellMachine(dung.DungFanMachine):
    def __init__(self,plan,item=22722,layout=b.LAYOUTS[0]):
        with patch.multiple(dung,ITEM_SPECS=SPELL_ITEMS,SCHEDULE_HEX=spells.SCHEDULE_HEX,
                            EVENT_GUARDS=spells.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class SpellLookup(lookup.LookupMachine):
    def __init__(self,plan,item=22722,layout=b.LAYOUTS[0]):
        with patch.multiple(arrow,ALL_ITEM_SPECS=SPELL_ITEMS,SCHEDULE_HEX=spells.SCHEDULE_HEX,
                            EVENT_GUARDS=spells.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class SpellRecast(recast.RecastMachine):
    def __init__(self,plan,item=22722,layout=b.LAYOUTS[0]):
        with patch.object(wind,'FIXTURE_ITEMS',SPELL_ITEMS):super().__init__(plan,item,layout)

class StickyDispersalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load_plan();cls.plan=h.apply_sticky_dispersal_items(cls.parent)
    def entry(self,m,accepted):
        dung.DungFanPortableTests().checked_entry(m,accepted,
            special.HELPER_OFFSET if isinstance(m,JarMachine) else spells.HELPER_OFFSET)
    def lookup(self,m,accepted):lookup.ArrowSlothLookupPortableTests().checked_lookup(m,accepted)

    def test_observed_requests_before_reject_after_use_native172_with_abi(self):
        self.assertEqual(h.ITEM_SPECS,OBSERVED)
        for cls in (JarMachine,SpellLookup):self.entry(cls(self.parent),False)
        for layout in b.LAYOUTS:
            for template in (0x58E5E,0x51BE1):
                for cls in (JarMachine,SpellLookup):
                    m=cls(self.plan,layout=layout)
                    for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                    self.entry(m,True)
                    self.assertEqual(m.events[-1],('dispatch',b.CONTROLLER,172))

    def test_exact_definition_and_owned_request_required(self):
        for cls in (JarMachine,SpellMachine,SpellLookup):
            for off,width in ((0,4),(4,1),(5,1),(0x104,4),(0x10C,4),(0x110,4),(0x114,4),(0x118,4),(0x11C,4)):
                m=cls(self.plan);at=dung.DEF+off
                value=int.from_bytes(m.cpu.mem_read(at,width),'little')^1
                m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)
            for at,value,width in ((b.CONTROLLER+0x548,999,4),(b.CONTROLLER+0x54C,99,4),
                (b.CONTROLLER+0x550,2,4),(b.CONTROLLER+0x555,0,1),(b.CONTROLLER+0x556,1,1),
                (b.CONTROLLER+0x558,1,8),(b.CONTROLLER+0x570,1,1),(b.CONTROLLER+0x728,1,8),
                (b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,1,4),(b.META+0xC,0,4),
                (b.COMP+0x20,0,8),(b.PROXY+8,0,8),(b.CONTROLLER+0x50,0,8)):
                m=cls(self.plan);m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)

    def test_schedule_resources_and_callback_rechecks(self):
        for cls in (JarMachine,SpellMachine):
            for off in range(96):
                m=cls(self.plan);at=m.lookup_results[m.action]+0xC0+off
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)
            for slot in (2,6):
                m=cls(self.plan);m.put64(b.CLIPS[slot],0);self.entry(m,False)
            for kind in ('definition','request','dialog','epoch','schedule','params','owner','disabled','motion'):
                m=cls(self.plan);target=m.lookup_results[m.action]
                def mutate(m,name):
                    if name!='clip' or m.events[-1][1]!=6:return
                    if kind=='definition':m.put32(dung.DEF+0x11C,0)
                    elif kind=='request':m.put32(b.CONTROLLER+0x548,999)
                    elif kind=='dialog':m.cpu.mem_write(b.CONTROLLER+0x570,b'\1')
                    elif kind=='epoch':m.put32(m.data+0x1C,0)
                    elif kind=='schedule':m.put32(target+0xC0,0)
                    elif kind=='params':m.put64(target+0x20,0)
                    elif kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                    elif kind=='disabled':m.cpu.mem_write(target+0x40,b'\0')
                    else:m.put32(target+0xA0,1011)
                m.mutate_on_call=mutate
                m.invoke(m.code+(special.HELPER_OFFSET if m.action==165 else spells.HELPER_OFFSET))
                self.assertFalse(any(e[0]=='dispatch' for e in m.events),(cls.__name__,kind))

    def test_spell_lookup_and_moving_recast_never_choose_boss42(self):
        for phase,pending in (('idle',1),('entry',0),('entry',1),('cast',0)):
            m=SpellLookup(self.plan);m.phase(phase,pending);self.lookup(m,True)
        for phase,pending in (('idle',0),('boss',0),('boss',1)):
            m=SpellLookup(self.plan);m.phase(phase,pending);self.lookup(m,False)
        for layout in b.LAYOUTS:recast.ItemRecastLookupTests().checked(SpellRecast(self.plan,layout=layout),True)
        for off in (0,4,0x104,0x10C,0x110,0x114,0x118,0x11C):
            m=SpellLookup(self.plan);at=dung.DEF+off
            m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.lookup(m,False)

    def test_native_injury_routes_work_for_both_item_actions(self):
        for action in (165,42):
            for source,target,index,first,count,raw in hurt.h.ROUTES:
                m=hurt.ItemHurtMachine(self.plan,action=action);m.select(source,index)
                hurt.ItemHurtLookupTests().checked(m,True,target=target)

    def test_dispersal_catchup_once_then_native_progress_and_interrupt_reset(self):
        candidate=assemble(self.plan,gap.BASE,gap.ALLOC)
        with patch.object(gap,'NEW_H',candidate):
            for frame in (18,50,76,77,103):
                f=gap.Fixture(42);f.d(gap.CTL+0x548,22722)
                self.assertEqual(f.run(0,1),1);self.assertEqual(f.marker(),2)
                self.assertEqual(f.run(frame,0),1);self.assertEqual(f.marker(),0)
                self.assertEqual(f.run(frame,0),0)
            for frame in (0,1,17,104,150,-1,float('nan')):
                f=gap.Fixture(42);f.d(gap.CTL+0x548,22722);f.run(0,1)
                self.assertEqual(f.run(frame,0),0)
            for at,value in ((gap.CTL+0x548,999),(gap.CTL+0x54C,7),(gap.DATA+0x1C,4),
                (gap.REC,0),(gap.PARAM+0x40,0),(gap.D17+0x18,9),(gap.CTL+0x68,1)):
                f=gap.Fixture(42);f.d(gap.CTL+0x548,22722);f.run(0,1);f.d(at,value)
                self.assertEqual(f.run(77,0),0);self.assertEqual(f.marker(),0)

    def test_existing_items_and_resistance_remain_accepted(self):
        for row in special.ITEM_SPECS+jars.ITEM_SPECS:self.entry(JarMachine(self.plan,row[0]),True)
        for row in spells.ALL_ITEM_SPECS:self.entry(wind.SpellMachine(self.plan,row[0]),True)
        for row in resistance.OBSERVED:
            self.entry(resistance.ResistanceLookup(self.plan,row[0]),True)
            recast.ItemRecastLookupTests().checked(resistance.ResistanceRecast(self.plan,row[0]),True)
        with patch.object(gap,'NEW_H',assemble(self.plan,gap.BASE,gap.ALLOC)):
            for method in ('test_two_spells_once','test_salt_unchanged','test_interruption_disarms'):
                getattr(gap.Cases(),method)()

    def test_only_three_owned_carriers_change_all_fixed_entries_preserved(self):
        old=deepcopy(self.parent)
        self.assertEqual(h.apply_sticky_dispersal_items(self.parent),self.plan);self.assertEqual(old,self.parent)
        for layout in b.LAYOUTS:
            changed=[]
            for before,after in zip(assemble(self.parent,*layout),assemble(self.plan,*layout)):
                for key in ('site','patched','original','target','code_offset','code_capacity'):
                    self.assertEqual(before[key],after[key])
                if before['payload']!=after['payload']:changed.append(before['name'])
                self.assertLessEqual(len(after['payload']),after['code_capacity'])
                if before['name']==spells.CARRIER_NAME:
                    self.assertEqual(before['payload'][:0x4000],after['payload'][:0x4000])
                    self.assertEqual(before['payload'][0x6C00:],after['payload'][0x6C00:])
            self.assertEqual(tuple(changed),h.CHANGED)
        self.assertEqual(len(relocation_specs(self.plan)),82)
        old['tool_version']='other'
        with self.assertRaises(ValueError):h.apply_sticky_dispersal_items(old)

if __name__=='__main__':unittest.main()
