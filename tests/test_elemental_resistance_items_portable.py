"""CPU-only native-entry/lookup contracts; actual buff effects require gameplay."""
from copy import deepcopy
from pathlib import Path
import struct,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta611_plan as load_plan,assemble,relocation_specs
import hinoenma_elemental_resistance_items as h
import hinoenma_wind_weakness_dragon as spell
import test_arrow_sloth_portable as arrow
import test_arrow_sloth_lookup_portable as lookup
import test_dung_fan_portable as dung
import test_wind_weakness_dragon_portable as wind_tests
import test_item_recast_lookup_portable as recast
import test_item_hurt_lookup_portable as hurt
from portable_machine import b

# Independent fixed observations from the failed five-item native requests.
OBSERVED=(
    (7785,3,0,7,7,(63190,0,0),796198,41,110,192),
    (805,3,0,7,7,(62930,0,0),796198,41,110,192),
    (64630,3,0,7,7,(45181,0,0),796198,41,110,192),
    (35156,3,0,7,7,(51630,0,0),796198,41,110,192),
    (10101,3,0,7,7,(21144,0,0),796198,41,110,192),
)
FIXTURE_ITEMS=spell.ALL_ITEM_SPECS+OBSERVED

class ResistanceMachine(dung.DungFanMachine):
    def __init__(self,plan,item=7785,layout=b.LAYOUTS[0]):
        with patch.multiple(dung,ITEM_SPECS=FIXTURE_ITEMS,SCHEDULE_HEX=spell.SCHEDULE_HEX,
                            EVENT_GUARDS=spell.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class ResistanceLookup(lookup.LookupMachine):
    def __init__(self,plan,item=7785,layout=b.LAYOUTS[0]):
        with patch.multiple(arrow,ALL_ITEM_SPECS=FIXTURE_ITEMS,SCHEDULE_HEX=spell.SCHEDULE_HEX,
                            EVENT_GUARDS=spell.EVENT_GUARDS):
            super().__init__(plan,item,layout)

class ResistanceRecast(recast.RecastMachine):
    def __init__(self,plan,item=7785,layout=b.LAYOUTS[0]):
        with patch.object(wind_tests,'FIXTURE_ITEMS',FIXTURE_ITEMS):
            super().__init__(plan,item,layout)

class ElementalResistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=load_plan();cls.plan=h.apply_elemental_resistance_items(cls.parent)
    def entry(self,m,accepted):dung.DungFanPortableTests().checked_entry(m,accepted,spell.HELPER_OFFSET)
    def lookup(self,m,accepted):lookup.ArrowSlothLookupPortableTests().checked_lookup(m,accepted)

    def test_before_rejects_after_dispatches_native172_and_common41_full_abi(self):
        self.assertEqual(OBSERVED,h.ITEM_SPECS)
        for row in OBSERVED:self.entry(ResistanceLookup(self.parent,row[0]),False)
        for layout in b.LAYOUTS:
            for template in (0x58E5E,0x51BE1):
                for row in OBSERVED:
                    m=ResistanceLookup(self.plan,row[0],layout)
                    for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                    self.entry(m,True)
                    self.assertIn(m.code+spell.LOOKUP_OFFSET,m.visited)
                    self.assertEqual(m.lookup_results[41],m.get64(b.VECTOR+8))

    def test_lookup_idle_entry_cast_and_moving_recast_keep_correct_bank(self):
        for row in OBSERVED:
            for phase,pending in (('idle',1),('entry',0),('entry',1),('cast',0)):
                m=ResistanceLookup(self.plan,row[0]);m.phase(phase,pending);self.lookup(m,True)
            for layout in b.LAYOUTS:
                m=ResistanceRecast(self.plan,row[0],layout)
                recast.ItemRecastLookupTests().checked(m,True)
            for phase,pending in (('boss',0),('boss',1),('idle',0)):
                m=ResistanceLookup(self.plan,row[0]);m.phase(phase,pending);self.lookup(m,False)

    def test_exact_definition_item_family_effect_and_request_guards(self):
        for row in OBSERVED:
            for off,width in ((0,4),(4,1),(5,1),(0x104,4),(0x10C,4),(0x110,4),(0x114,4),(0x118,4),(0x11C,4)):
                for cls,check in ((ResistanceMachine,self.entry),(ResistanceLookup,self.lookup)):
                    m=cls(self.plan,row[0]);at=dung.DEF+off
                    value=int.from_bytes(m.cpu.mem_read(at,width),'little')^1
                    m.cpu.mem_write(at,value.to_bytes(width,'little'));check(m,False)
            for at,value,width in ((b.CONTROLLER+0x548,999,4),(b.CONTROLLER+0x54C,99,4),
                (b.CONTROLLER+0x550,2,4),(b.CONTROLLER+0x555,0,1),(b.CONTROLLER+0x570,1,1),
                (b.COMP+0x20,0,8),(b.META+0xC,0,4),(b.ACTOR+0xEF0,1,4),
                (b.PROXY+8,0,8),(b.ACTOR+4,0x20000,4)):
                m=ResistanceMachine(self.plan,row[0]);m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)

    def test_native_schedule_descriptors_and_resources_are_required(self):
        for off in range(96):
            m=ResistanceLookup(self.plan);at=m.lookup_results[41]+0xC0+off
            m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)
        for index,*_ in spell.EVENT_GUARDS[41]:
            for off in (0x17,0x18,0x1C,0x3F,0x2A,0x52):
                m=ResistanceLookup(self.plan);at=b.ACTOR+0xA1000+index*0x80+off
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.entry(m,False)
        for row in OBSERVED:
            for kind in ('missing','owner','duplicate','disabled','motion','alternate','slot2','slot6'):
                m=ResistanceLookup(self.plan,row[0]);target=m.lookup_results[41]
                if kind=='missing':m.put64(b.VECTOR+8,0)
                elif kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                elif kind=='duplicate':m.put64(b.VECTOR+16,target);m.put32(b.BANK+0x130,3)
                elif kind=='disabled':m.cpu.mem_write(target+0x40,b'\0')
                elif kind=='motion':m.put32(target+0xA0,1010)
                elif kind=='alternate':m.put32(target+0xB4,0)
                else:m.put64(b.CLIPS[2 if kind=='slot2' else 6],0)
                self.entry(m,False)

    def test_resource_callbacks_revalidate_exact_item_and_cast(self):
        for row in OBSERVED:
            for kind in ('effect','spawn','kind','request','dialog','epoch','schedule','params','owner','motion'):
                m=ResistanceMachine(self.plan,row[0]);target=m.lookup_results[41]
                def mutate(m,name):
                    if name!='clip' or m.events[-1][1]!=6:return
                    if kind=='effect':m.put32(dung.DEF+0x110,0)
                    elif kind=='spawn':m.put32(dung.DEF+0x11C,0)
                    elif kind=='kind':m.cpu.mem_write(dung.DEF+4,b'\x01')
                    elif kind=='request':m.put32(b.CONTROLLER+0x548,64367)
                    elif kind=='dialog':m.cpu.mem_write(b.CONTROLLER+0x570,b'\1')
                    elif kind=='epoch':m.put32(m.data+0x1C,0)
                    elif kind=='schedule':m.put32(target+0xC0,0)
                    elif kind=='params':m.put64(target+0x20,0)
                    elif kind=='owner':m.put64(target+0x38,b.OWN_BANK)
                    else:m.put32(target+0xA0,1010)
                m.mutate_on_call=mutate;m.invoke(m.code+spell.HELPER_OFFSET)
                self.assertFalse(any(e[0]=='dispatch' for e in m.events),(row[0],kind))

    def test_existing_items_spells_and_common41_hurt_routes_preserved(self):
        for row in spell.ALL_ITEM_SPECS:
            self.entry(wind_tests.SpellMachine(self.plan,row[0]),True)
        for item in (64367,4998,44930):
            m=recast.RecastMachine(self.plan,item);recast.ItemRecastLookupTests().checked(m,True)
        for source,target,index,first,count,raw in hurt.h.ROUTES:
            m=hurt.ItemHurtMachine(self.plan,action=41);m.select(source,index)
            hurt.ItemHurtLookupTests().checked(m,True,target=target)

    def test_only_owned_carrier_changes_fixed_entries_and_relocations(self):
        unchanged=deepcopy(self.parent)
        self.assertEqual(h.apply_elemental_resistance_items(self.parent),self.plan)
        self.assertEqual(unchanged,self.parent)
        for layout in b.LAYOUTS:
            changed=[]
            for old,new in zip(assemble(self.parent,*layout),assemble(self.plan,*layout)):
                for key in ('site','patched','original','target','code_offset','code_capacity'):
                    self.assertEqual(old[key],new[key])
                if old['payload']!=new['payload']:changed.append(old['name'])
                if old['name']==h.CARRIER:
                    self.assertEqual(old['payload'][:0x4000],new['payload'][:0x4000])
                    self.assertEqual(old['payload'][0x6C00:],new['payload'][0x6C00:len(old['payload'])])
                self.assertLessEqual(len(new['payload']),new['code_capacity'])
            self.assertEqual(tuple(changed),h.CHANGED)
        self.assertEqual(len(relocation_specs(self.plan)),82)
        bad=deepcopy(self.parent);bad['tool_version']='other'
        with self.assertRaises(ValueError):h.apply_elemental_resistance_items(bad)

if __name__=='__main__':unittest.main()
