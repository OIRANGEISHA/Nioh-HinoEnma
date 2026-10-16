"""Execute family adapters against a separately captured native catalogue.

Native inventory, spawning and effects are stub boundaries, not gameplay tests.
"""
from copy import deepcopy
import base64
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import load_beta613_plan as load_plan, assemble, relocation_specs, validate_layout
import hinoenma_general_jutsu as h
import test_wind_weakness_dragon_portable as wind
import test_arrow_sloth_lookup_portable as lookup
import test_item_recast_lookup_portable as recast
import test_nine_talismans_portable as nine
import test_soul_release_portable as soul
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

FIXTURE = json.loads((ROOT/'tests/fixtures/general-jutsu-native.json').read_text('utf8'))
CATEGORY_ACTION = {4:165,5:166,6:982,7:41,9:42,11:986,16:605,18:606,19:607,20:608,22:610,23:611,25:1165}
SCHEDULES = {int(k):v['params_raw'][128:320] for k,v in FIXTURE['actions'].items()}
GUARDS = {}
for action, schedule in SCHEDULES.items():
    GUARDS[action] = []
    for ei in sorted({i for i,_,_ in struct.iter_unpack('<hHH', bytes.fromhex(schedule)) if i>=0}):
        e = bytes.fromhex(FIXTURE['events'][str(ei)])
        GUARDS[action].append((ei,e[0x17],struct.unpack_from('<i',e,0x18)[0],struct.unpack_from('<h',e,0x1C)[0],e[0x3F],e[0x2A],struct.unpack_from('<h',e,0x52)[0]))
ITEMS = tuple((r['id'],r['kind'],r['subtype'],r['category'],r['flags'],tuple(r['effects']),r['spawn'],CATEGORY_ACTION[r['category']],FIXTURE['actions'][str(CATEGORY_ACTION[r['category']])]['motion'],0) for r in FIXTURE['items'])
BY_ID = {r[0]:r for r in ITEMS}
REPRESENTATIVES = {row[3]:row[0] for row in ITEMS}
PRIVATE = {a:b.ACTOR+0x35000+i*0x200 for i,a in enumerate(sorted(SCHEDULES))}


class Machine(wind.SpellLookupMachine):
    def run(self,address,stop=None):
        # Both lookup and entry independently verify the two 1408-byte timing
        # resources. Keep a finite budget while executing both full loops.
        self.reached=False;self.stop=stop or self.module+0x1100800
        self.cpu.emu_start(address,0,count=20000)
        if not self.reached:raise AssertionError('Family payload exceeded its bounded continuation budget')

    def __init__(self, plan, item, layout=b.LAYOUTS[0]):
        with patch.multiple(wind, FIXTURE_ITEMS=ITEMS, FIXTURE_SCHEDULES=SCHEDULES, FIXTURE_GUARDS=GUARDS), patch.object(lookup, 'PRIVATE_RECORDS', PRIVATE):
            super().__init__(plan, item, layout)
        self.put32(b.OWN_BANK+0x130, len(PRIVATE))
        if self.action == 1165:
            self.put32(self.lookup_results[self.action]+0xB4,90111)
            self.install_auxiliary_resources()
        self.events.clear();self.writes.clear()

    def phase(self, name, pending=None):
        with patch.object(lookup, 'PRIVATE_RECORDS', PRIVATE):
            super().phase(name,pending)


class Recast(recast.RecastMachine):
    def __init__(self, plan, item):
        with patch.multiple(wind, FIXTURE_ITEMS=ITEMS, FIXTURE_SCHEDULES=SCHEDULES, FIXTURE_GUARDS=GUARDS), patch.object(lookup, 'PRIVATE_RECORDS', PRIVATE):
            super().__init__(plan,item)
        self.put32(b.OWN_BANK+0x130,len(PRIVATE))
        if self.action == 1165:
            self.put32(self.lookup_results[self.action]+0xB4,90111)
            self.install_auxiliary_resources()


class GeneralJutsuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load_plan();cls.plan=h.apply_general_jutsu(cls.parent)

    def entry(self,m,ok):
        wind.dung_tests.DungFanPortableTests().checked_entry(m,ok,h.spells.HELPER_OFFSET)

    def check_lookup(self,m,ok=True):
        with patch.object(lookup,'PRIVATE_RECORDS',PRIVATE):
            lookup.ArrowSlothLookupPortableTests().checked_lookup(m,ok)

    def test_complete_catalogue_preserves_native_effects_and_item_stock(self):
        self.assertEqual(len(ITEMS),132)
        for row in ITEMS:
            with self.subTest(item=row[0],category=row[3]):
                self.entry(Machine(self.plan,row[0]),True)

    def test_unlisted_item_ids_share_family_and_original_effect_parameters(self):
        for item in REPRESENTATIVES.values():
            m=Machine(self.plan,item)
            # These IDs were never in a whitelist or in the capture. They are
            # returned by the synthetic native definition table for this case.
            m.put32(b.CONTROLLER+0x548,0x10001)
            m.put32(wind.dung_tests.DEF,0x10001)
            m.put32(wind.dung_tests.DEF+0x11C,0x23456)
            self.entry(m,True)

    def test_all_families_resolve_common_bank_instead_of_colliding_boss_action(self):
        for layout in b.LAYOUTS:
            for item in REPRESENTATIVES.values():
                for phase,pending in (('idle',1),('entry',0),('cast',0)):
                    m=Machine(self.plan,item,layout);m.phase(phase,pending);self.check_lookup(m)
                for phase,pending in (('idle',0),('boss',0),('boss',1)):
                    m=Machine(self.plan,item,layout);m.phase(phase,pending);self.check_lookup(m,False)
                m=Recast(self.plan,item)
                with patch.object(lookup,'PRIVATE_RECORDS',PRIVATE):
                    recast.ItemRecastLookupTests().checked(m,True)

    def test_wrong_definition_request_and_owner_reject(self):
        for item in REPRESENTATIVES.values():
            changes=((wind.dung_tests.DEF,999,4),(wind.dung_tests.DEF+4,0,2),
                (wind.dung_tests.DEF+0x104,0,4),(wind.dung_tests.DEF+0x10C,99,4),
                (wind.dung_tests.DEF+0x110,0xffffffff,4),(wind.dung_tests.DEF+0x11C,0xffffffff,4),
                (b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,1,4),(b.META+0xC,0,4),
                (b.COMP+0x20,0,8),(b.PROXY+8,0,8),(b.CONTROLLER+0x548,999,4),
                (b.CONTROLLER+0x54C,99,4),(b.CONTROLLER+0x555,0,1),
                (b.CONTROLLER+0x556,1,1),(b.CONTROLLER+0x570,1,1),
                (b.CONTROLLER+0x728,1,8))
            for at,val,width in changes:
                with self.subTest(item=item,at=hex(at)):
                    m=Machine(self.plan,item);m.cpu.mem_write(at,val.to_bytes(width,'little'));self.entry(m,False)

    def test_definition_snapshot_rejects_same_family_mutation_during_callbacks(self):
        for item in REPRESENTATIVES.values():
            for offset in (0,4,0x104,0x108,0x10C,0x110,0x114,0x118,0x11C):
                m=Machine(self.plan,item)
                changed=[False]
                def mutate(m,name):
                    if name!='clip' or m.events[-1][1]!=6 or changed[0]:return
                    changed[0]=True
                    at=wind.dung_tests.DEF+offset;m.put32(at,m.get32(at)^1)
                m.mutate_on_call=mutate;m.invoke(m.code+h.spells.HELPER_OFFSET)
                self.assertTrue(changed[0],(item,offset))
                self.assertFalse(any(e[0]=='dispatch' for e in m.events),(item,offset))

    def test_schedules_descriptors_and_both_clip_banks_are_required(self):
        for cat,item in REPRESENTATIVES.items():
            for offset in range(96):
                m=Machine(self.plan,item);at=m.lookup_results[m.action]+0xC0+offset
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)
            for slot in (2,6):
                m=Machine(self.plan,item);m.put64(b.CLIPS[slot],0);self.entry(m,False)
            for ei,*_ in GUARDS[CATEGORY_ACTION[cat]]:
                if ei>=10000:continue
                m=Machine(self.plan,item);at=m.get64(b.EVENTS+ei*8)+0x17
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)

    def test_new_family_injury_and_input_remapping_protection(self):
        old=nine.old
        motions={a:r['motion'] for a0,r in FIXTURE['actions'].items() for a in [int(a0)]}
        with patch.object(old.hurt,'MOTIONS',{**old.hurt.MOTIONS,**motions}),patch.object(old.hurt.h,'SCHEDULES',{**old.hurt.h.SCHEDULES,**SCHEDULES}):
            for a in h.NEW_SCHEDULES:
                for source,target,index,first,count,raw in old.hurt.h.ROUTES:
                    m=old.hurt.ItemHurtMachine(self.plan,action=a);m.select(source,index)
                    old.hurt.ItemHurtLookupTests().checked(m,True,target=target)
        for name in ('HE_InputA','HE_InputB'):
            for a,motion in motions.items():
                for owner,ok in ((b.BANK,True),(b.OWN_BANK,False)):
                    m=PortableMachine(self.plan);m.put32(b.CURRENT,a);m.put64(b.CURRENT+0x38,owner);m.put32(b.PARAM+0x20,motion)
                    for off in (0xC,0xE):m.cpu.mem_write(b.INPUT+off,b'\1')
                    m.cpu.mem_write(m.data+0x29,b'\1');m.reset()
                    for reg,val in ((UC_X86_REG_RBX,b.CONTROLLER),(UC_X86_REG_RDI,b.INPUT),(UC_X86_REG_RDX,b.INPUT),(UC_X86_REG_R10,0),(UC_X86_REG_RCX,6)):m.cpu.reg_write(reg,val)
                    hook=m.by_name[name];m.run(hook['target'],hook['site']+hook['length'])
                    self.assertEqual(m.get32(m.data+0x24),int(not ok),(name,a,owner))

    def test_new_talisman_ids_get_one_native_catchup(self):
        g=nine.old.gap
        with patch.object(g,'NEW_H',assemble(self.plan,g.BASE,g.ALLOC)),patch.object(nine,'SCHEDULES',SCHEDULES):
            for row in ITEMS:
                if row[7] not in (42,611,1165):continue
                f=nine.Gap(42).item(row)
                self.assertEqual(f.run(0,1),1);self.assertEqual(f.marker(),2)
                self.assertEqual(f.run(77,0),1);self.assertEqual(f.marker(),0)
                self.assertEqual(f.run(77,0),0)

    def test_existing_special_cases_and_released_dispersal_stay_intact(self):
        soul.SoulTests.setUpClass()
        with patch.object(soul.SoulTests,'plan',self.plan):
            for name in ('test_owned_equipment_threshold_both_slots_and_fallback',
                         'test_exact_definition_ownership_and_dead_requests_rejected',
                         'test_common3025_alias_and_common42_never_boss42',
                         'test_cast_gap_recast_and_existing_injury_path'):
                getattr(soul.SoulTests(name),name)()
        m=nine.old.SpellLookup(self.plan);nine.reused.released(m.cpu,b.CONTROLLER,b.ACTOR,b.ACTOR+0x180000,4)
        self.entry(m,True)
        for item in (44220,44607):self.entry(wind.SpellMachine(self.plan,item),True)

    def test_all_relocations_and_pure_transform_preserve_native_sites(self):
        before=deepcopy(self.parent);self.assertEqual(h.apply_general_jutsu(self.parent),self.plan);self.assertEqual(before,self.parent)
        ranges=sorted((r['code_offset'],r['code_offset']+r['code_capacity']) for r in self.plan['hooks'])
        self.assertTrue(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])))
        self.assertLessEqual(ranges[-1][1],self.plan['allocation_size'])
        for a,b0 in ranges:
            for c,d in self.plan['protected_data_pages']:self.assertFalse(max(a,c)<min(b0,d))
        specs=relocation_specs(self.plan)
        for module,alloc in b.LAYOUTS:
            for orig,new,spec in zip(assemble(self.parent,module,alloc),assemble(self.plan,module,alloc),specs):
                for key in ('site','patched','original','target','code_offset','code_capacity'):self.assertEqual(orig[key],new[key])
                self.assertLessEqual(len(new['payload']),new['code_capacity'])
                raw=bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind']==0:value=struct.pack('<Q',alloc+self.plan['data_offset'])
                    elif fix['kind']==2:value=struct.pack('<Q',module+fix['target'])
                    else:value=struct.pack('<i',module+fix['target']-alloc-spec['code_offset']-fix['next'])
                    raw[fix['offset']:fix['offset']+len(value)]=value
                self.assertEqual(bytes(raw),new['payload'])


if __name__=='__main__':unittest.main()
