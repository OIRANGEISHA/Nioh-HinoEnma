"""Execute entry, lookup, catch-up and injury adapters; native effects are live-tested."""
from copy import deepcopy
from pathlib import Path
import sys,struct,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta612_plan as load_plan,assemble,relocation_specs
import hinoenma_sticky_dispersal_items as sticky
import hinoenma_dispersal_reuse as reuse
import hinoenma_nine_talismans as h
import test_wind_weakness_dragon_portable as wind
import test_sticky_dispersal_items_portable as old
import test_dispersal_reuse_portable as reused
from portable_machine import PortableMachine,b
from unicorn.x86_const import *

# IDs, spawning templates and native families from the failed request capture.
OBSERVED=((52306,2,15,9,5,(0,0,0),937435,42,111,194),
 (40718,2,15,23,5,(0,0,0),55783,611,110,287),
 (19803,2,15,9,5,(0,0,0),311181,42,111,194),
 (31267,2,15,25,5,(0,0,0),743069,1165,111,359),
 (3735,2,15,25,5,(0,0,0),592735,1165,111,359),
 (52147,2,15,25,5,(0,0,0),885960,1165,111,359),
 (3944,2,15,25,5,(0,0,0),778678,1165,111,359),
 (24932,2,15,25,5,(0,0,0),917110,1165,111,359),
 (35389,2,15,23,5,(0,0,0),790502,611,110,287))
ITEMS=wind.FIXTURE_ITEMS+OBSERVED
SCHEDULES={**wind.FIXTURE_SCHEDULES,611:h.AREA_SCHEDULE}
GUARDS={**wind.FIXTURE_GUARDS,611:h.EVENT_GUARDS[611]}

class Machine(wind.SpellLookupMachine):
    def __init__(self,plan,item=52306,layout=b.LAYOUTS[0]):
        with patch.multiple(wind,FIXTURE_ITEMS=ITEMS,FIXTURE_SCHEDULES=SCHEDULES,FIXTURE_GUARDS=GUARDS):
            super().__init__(plan,item,layout)
        if self.action==1165:
            self.put32(self.lookup_results[self.action]+0xB4,90111)
            self.install_auxiliary_resources()
        self.events.clear();self.writes.clear()

class Recast(old.recast.RecastMachine):
    def __init__(self,plan,item=52306):
        with patch.multiple(wind,FIXTURE_ITEMS=ITEMS,FIXTURE_SCHEDULES=SCHEDULES,FIXTURE_GUARDS=GUARDS):
            super().__init__(plan,item)

class Gap(reused.GapFixture):
    def trace(self,u,at,size,user):
        raw=bytes(u.mem_read(at,size))
        if raw[:1]==b'\xe8':
            target=at+5+struct.unpack_from('<i',raw,1)[0]
            if old.gap.ALLOC<=target<old.gap.ALLOC+0x69000:return
        super().trace(u,at,size,user)
    def item(self,row):
        g=old.gap
        self.d(g.REC,row[7]);self.d(g.PARAM+0x20,row[8]);self.d(g.PARAM+0x34,90111 if row[7]==1165 else -1)
        self.u.mem_write(g.PARAM+0x40,bytes.fromhex(SCHEDULES[row[7]]))
        self.d(g.CTL+0x548,row[0]);self.d(g.CTL+0x54C,row[3])
        return self

class NineTalismansTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=reuse.apply_dispersal_reuse(sticky.apply_sticky_dispersal_items(load_plan()))
        cls.plan=h.apply_nine_talismans(cls.parent)
    def entry(self,m,ok):old.dung.DungFanPortableTests().checked_entry(m,ok,h.spells.HELPER_OFFSET)

    def test_observed_nine_requests_dispatch_native172_preserve_abi(self):
        self.assertEqual(OBSERVED,h.ITEM_SPECS)
        for row in OBSERVED:self.entry(Machine(self.parent,row[0]),False)
        for layout in b.LAYOUTS:
            for row in OBSERVED:
                for template in (0x58E5E,0x51BE1):
                    m=Machine(self.plan,row[0],layout)
                    for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                    self.entry(m,True)

    def test_definition_request_and_schedule_fail_closed(self):
        for row in OBSERVED:
            for off,width in ((0,4),(4,1),(5,1),(0x104,4),(0x10C,4),(0x110,4),(0x114,4),(0x118,4),(0x11C,4)):
                m=Machine(self.plan,row[0]);at=old.dung.DEF+off
                value=int.from_bytes(m.cpu.mem_read(at,width),'little')^1
                m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)
            for at,value,width in ((b.CONTROLLER+0x54C,99,4),(b.CONTROLLER+0x555,0,1),
                (b.CONTROLLER+0x556,1,1),(b.CONTROLLER+0x570,1,1),(b.CONTROLLER+0x728,1,8),
                (b.ACTOR+0xEF0,1,4),(b.META+0xC,0,4),(b.COMP+0x20,0,8)):
                m=Machine(self.plan,row[0]);m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)
        for ident in (52306,40718,31267):
            for off in range(96):
                m=Machine(self.plan,ident);at=m.lookup_results[m.action]+0xC0+off
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)
            for slot in (2,6):
                m=Machine(self.plan,ident);m.put64(b.CLIPS[slot],0);self.entry(m,False)

    def test_post_callback_mutation_rejects(self):
        for ident in (52306,40718,31267):
            for kind in ('definition','request','epoch','schedule','params','owner','disabled','motion'):
                m=Machine(self.plan,ident);target=m.lookup_results[m.action]
                def mutate(m,name):
                    if name!='clip' or m.events[-1][1]!=6:return
                    if kind=='definition':m.put32(old.dung.DEF+0x11C,0)
                    elif kind=='request':m.put32(b.CONTROLLER+0x548,999)
                    elif kind=='epoch':m.put32(m.data+0x1C,0)
                    elif kind=='schedule':m.put32(target+0xC0,0)
                    elif kind=='params':m.put64(target+0x20,0)
                    elif kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                    elif kind=='disabled':m.cpu.mem_write(target+0x40,b'\0')
                    else:m.put32(target+0xA0,1011)
                m.mutate_on_call=mutate;m.invoke(m.code+h.spells.HELPER_OFFSET)
                self.assertFalse(any(e[0]=='dispatch' for e in m.events),(ident,kind))

    def test_common42_collision_and_movement_recast(self):
        for ident in (52306,19803):
            for phase,pending in (('idle',1),('entry',0),('entry',1),('cast',0)):
                m=Machine(self.plan,ident);m.phase(phase,pending)
                old.lookup.ArrowSlothLookupPortableTests().checked_lookup(m,True)
            for phase,pending in (('idle',0),('boss',0),('boss',1)):
                m=Machine(self.plan,ident);m.phase(phase,pending)
                old.lookup.ArrowSlothLookupPortableTests().checked_lookup(m,False)
            old.recast.ItemRecastLookupTests().checked(Recast(self.plan,ident),True)

    def test_all_families_one_native_catchup_and_exact_boundaries(self):
        g=old.gap
        with patch.object(g,'NEW_H',assemble(self.plan,g.BASE,g.ALLOC)):
            for row in OBSERVED:
                low,high=(24,100) if row[7]==611 else (17,104)
                for frame in (low+1,50,77,high-1):
                    f=Gap(42).item(row);self.assertEqual(f.run(0,1),1);self.assertEqual(f.marker(),2)
                    self.assertEqual(f.run(frame,0),1);self.assertEqual(f.marker(),0)
                    self.assertEqual(f.run(frame,0),0)
                for frame in (0,1,low,high,150,-1,float('nan')):
                    f=Gap(42).item(row);f.run(0,1);self.assertEqual(f.run(frame,0),0)
                for at,value in ((g.CTL+0x548,999),(g.CTL+0x54C,7),(g.DATA+0x1C,4),
                    (g.REC,0),(g.PARAM+0x40,0),(g.D17+0x18,9),(g.CTL+0x68,1)):
                    f=Gap(42).item(row);f.run(0,1);f.d(at,value)
                    self.assertEqual(f.run(77,0),0);self.assertEqual(f.marker(),0)

    def test_area_cast_injury_and_input_suppression(self):
        with patch.object(old.hurt,'MOTIONS',{**old.hurt.MOTIONS,611:110}),patch.object(old.hurt.h,'SCHEDULES',{**old.hurt.h.SCHEDULES,611:h.AREA_SCHEDULE}):
            for source,target,index,first,count,raw in old.hurt.h.ROUTES:
                m=old.hurt.ItemHurtMachine(self.plan,action=611);m.select(source,index)
                old.hurt.ItemHurtLookupTests().checked(m,True,target=target)
        for name in ('HE_InputA','HE_InputB'):
            for owner,motion,ok in ((b.BANK,110,True),(b.OWN_BANK,110,False),(b.BANK,111,False)):
                m=PortableMachine(self.plan);m.put32(b.CURRENT,611);m.put64(b.CURRENT+0x38,owner);m.put32(b.PARAM+0x20,motion)
                for off in (0xC,0xE):m.cpu.mem_write(b.INPUT+off,b'\1')
                m.cpu.mem_write(m.data+0x29,b'\1');m.reset()
                for reg,val in ((UC_X86_REG_RBX,b.CONTROLLER),(UC_X86_REG_RDI,b.INPUT),(UC_X86_REG_RDX,b.INPUT),(UC_X86_REG_R10,0),(UC_X86_REG_RCX,6)):m.cpu.reg_write(reg,val)
                hook=m.by_name[name];m.run(hook['target'],hook['site']+hook['length'])
                self.assertEqual(m.get32(m.data+0x24),int(not ok))
                self.assertEqual(m.cpu.reg_read(UC_X86_REG_RCX),6 if ok else 11)

    def test_prior_items_and_released_dispersal_remain_supported(self):
        case=old.StickyDispersalTests();case.parent=load_plan();case.plan=self.plan
        with patch.object(old.gap,'Fixture',Gap):
            for name in ('test_schedule_resources_and_callback_rechecks','test_spell_lookup_and_moving_recast_never_choose_boss42',
                         'test_existing_items_and_resistance_remain_accepted'):
                getattr(case,name)()
        m=old.SpellLookup(self.plan);reused.released(m.cpu,b.CONTROLLER,b.ACTOR,b.ACTOR+0x180000,4)
        self.entry(m,True)

    def test_native_sites_and_owned_capacity_unchanged(self):
        original=deepcopy(self.parent);self.assertEqual(h.apply_nine_talismans(self.parent),self.plan);self.assertEqual(original,self.parent)
        for layout in b.LAYOUTS:
            changes=[]
            for a,c in zip(assemble(self.parent,*layout),assemble(self.plan,*layout)):
                for key in ('site','patched','original','target','code_offset','code_capacity'):self.assertEqual(a[key],c[key])
                if a['payload']!=c['payload']:changes.append(a['name'])
                self.assertLessEqual(len(c['payload']),c['code_capacity'])
            self.assertEqual(changes,self.plan['nine_talismans_candidate']['changed_hooks'])
        self.assertEqual(len(relocation_specs(self.plan)),82)
        with self.assertRaises(ValueError):h.apply_nine_talismans(load_plan())

if __name__=='__main__':unittest.main()
