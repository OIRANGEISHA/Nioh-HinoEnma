"""Execute the new gates with native resources; game events are RET stubs.

These CPU tests verify ABI, owner/resource rejection, injury routing and ASLR.
Actual transformation/consumption/cleanup require the separate live witness.
"""
import base64
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import load_beta614_plan as load_plan, assemble, relocation_specs
from hinoenma_soul_purge import apply_soul_purge
import hinoenma_kodama_transform as k
import test_wind_weakness_dragon_portable as wind
import test_dung_fan_portable as dung
import test_item_hurt_lookup_portable as hurt
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

FIXTURE = json.loads((ROOT/'tests/fixtures/kodama-native.json').read_text('utf8'))
PARAMS = {int(a):bytes.fromhex(v) for a,v in FIXTURE['actions'].items()}
EVENTS = {int(e):bytes.fromhex(v) for e,v in FIXTURE['events'].items()}
SCHEDULES = {a:v[0x40:].hex() for a,v in PARAMS.items()}
SPEC = (19707,2,14,28,5,(0,0,0),161855,1205,122,414)
LOOP = b.ACTOR+0x30400


class Machine(wind.SpellResources, dung.DungFanMachine):
    def __init__(self,plan,layout=b.LAYOUTS[0]):
        with patch.multiple(dung,ITEM_SPECS=(SPEC,),SCHEDULE_HEX=SCHEDULES,EVENT_GUARDS={1205:(),1206:()}):
            super().__init__(plan,19707,layout)
        self.cpu.mem_write(dung.DEF,bytes.fromhex(FIXTURE['item']))
        self.lookup_results[1206]=LOOP
        self.put64(b.VECTOR+16,LOOP);self.put32(b.BANK+0x130,3)
        for action,record in ((1205,self.lookup_results[1205]),(1206,LOOP)):
            self.put32(record,action);self.put64(record+0x20,record+0x80)
            self.put64(record+0x38,b.BANK);self.cpu.mem_write(record+0x40,b'\1')
            self.cpu.mem_write(record+0x80,PARAMS[action])
        self.cpu.mem_write(b.BANK+0x88,struct.pack('<H',200))
        for index,raw in EVENTS.items():
            at=b.ACTOR+0xA1000+index*0x80;self.put64(b.EVENTS+index*8,at);self.cpu.mem_write(at,raw)
        self.motion_by_key={(slot,motion):index for slot in (2,6) for motion,index in ((122,0),(0,1))}
        for slot in (2,6):self.put64(b.CLIPS[slot]+8,b.ACTOR+0x80100)
        self.install_auxiliary_resources()
        for row in FIXTURE['aux']:
            n=row['row'];pack=wind.AUX_PACKS[n]
            self.cpu.mem_write(wind.AUX_TABLES[n],bytes.fromhex(FIXTURE['hash_tables'][n]))
            self.put32(pack+0x30+row['index']*4,row['offset'])
            self.put32(pack+0x34+row['index']*4,row['end'])
            self.cpu.mem_write(pack+row['offset'],bytes.fromhex(row['raw']))
        self.events.clear();self.writes.clear()

    def run(self,address,stop=None):
        self.reached=False;self.stop=stop or self.module+0x1100800
        self.cpu.emu_start(address,0,count=30000)
        if not self.reached:raise AssertionError('Bounded Kodama payload did not return')


class KodamaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=apply_soul_purge(load_plan());cls.plan=k.apply_kodama_transform(cls.parent)

    def checked(self,m,expected):
        dung.DungFanPortableTests().checked_entry(m,expected,k.spells.HELPER_OFFSET)

    def test_enter_uses_native172_and_both_clips_with_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E,0x51BE1):
                m=Machine(self.plan,layout)
                for at in (b.ACTOR,b.META,m.data+4):m.put32(at,template)
                self.checked(m,True)
                self.assertIn(('lookup',1206),m.events)
                for slot in (2,6):
                    self.assertIn(('clip',slot,122),m.events)
                    self.assertIn(('clip',slot,0),m.events)

    def test_exact_definition_owner_request_and_epoch_are_required(self):
        changes=[(dung.DEF+off,1,2 if off==4 else 4) for off,_ in k.DEFINITION]
        changes += [(b.ACTOR+4,0x20000,4),(b.ACTOR+0xEF0,1,4),(b.META+0xC,0,4),
                    (b.COMP+0x20,0,8),(b.PROXY+8,0,8),(b.CONTROLLER+0x555,0,1),
                    (b.CONTROLLER+0x548,0,4),(b.CONTROLLER+0x54C,0,4),
                    (b.CONTROLLER+0x556,1,1),(b.CONTROLLER+0x570,1,1),
                    (b.CONTROLLER+0x728,1,8),(b.CURRENT,1,4)]
        for at,val,width in changes:
            with self.subTest(address=hex(at)):
                m=Machine(self.plan);m.cpu.mem_write(at,val.to_bytes(width,'little'));self.checked(m,False)
        for at,value in ((0x1C,0),(4,0)):
            m=Machine(self.plan);m.put32(m.data+at,value);self.checked(m,False)

    def test_full_enter_loop_parameters_and_lifecycle_descriptors(self):
        for action in (1205,1206):
            for offset in range(0xA0):
                m=Machine(self.plan);at=m.lookup_results[action]+0x80+offset
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.checked(m,False)
        for index in EVENTS:
            for offset in (0,4,0x17,0x18,0x1C,0x3F,0x50,0x52,0x68,0x7F):
                m=Machine(self.plan);at=m.get64(b.EVENTS+index*8)+offset
                m.cpu.mem_write(at,bytes([m.cpu.mem_read(at,1)[0]^1]));self.checked(m,False)
        for at in (b.BANK+0x80,LOOP+0x20,LOOP+0x38):
            m=Machine(self.plan);m.put64(at,0);self.checked(m,False)
        for slot in (2,6):
            for off in (0,8):
                m=Machine(self.plan);m.put64(b.CLIPS[slot]+off,0);self.checked(m,False)

    def test_exact_timing_pack_probe_chain_and_descriptor_required(self):
        for row in FIXTURE['aux']:
            n=row['row'];pack=wind.AUX_PACKS[n]
            addresses=[pack+off for off in range(0,0x30,4)]
            addresses += [pack+0x30+row['index']*4,pack+0x34+row['index']*4]
            addresses += [pack+row['offset']+off for off in range(0,len(bytes.fromhex(row['raw'])),8)]
            addresses += [wind.AUX_HASHES[n]+8]
            addresses += [wind.AUX_TABLES[n]+e['bucket']*8+off for e in k.AUX_ROWS[n]['hash_probe_trace'] for off in (0,4)]
            for at in addresses:
                m=Machine(self.plan);m.put32(at,m.get32(at)^1);self.checked(m,False)

    def test_changes_in_native_callbacks_are_rechecked(self):
        for kind in ('epoch','owner','request','death','loop-owner','loop-params','descriptor','aux','motion-owner'):
            m=Machine(self.plan);changed=[False]
            def mutate(m,name):
                if changed[0] or name!='clip' or m.events[-1][1:]!=(6,0):return
                changed[0]=True
                if kind=='epoch':m.put32(m.data+0x1C,0)
                elif kind=='owner':m.put64(m.module+self.plan['targets']['player_slot'],b.ACTOR+0x100)
                elif kind=='request':m.put32(b.CONTROLLER+0x548,999)
                elif kind=='death':m.put64(b.COMP+0x20,0)
                elif kind=='loop-owner':m.put64(LOOP+0x38,b.OWN_BANK)
                elif kind=='loop-params':m.put32(LOOP+0xC0,0)
                elif kind=='descriptor':m.put32(m.get64(b.EVENTS+157*8)+0x18,0)
                elif kind=='aux':m.put32(wind.AUX_PACKS[1]+FIXTURE['aux'][1]['offset'],1)
                else:m.put64(b.ACTOR+0x38,b.MOTION+0x100)
            m.mutate_on_call=mutate;m.invoke(m.code+k.spells.HELPER_OFFSET)
            self.assertTrue(changed[0],kind)
            self.assertFalse(any(e[0]=='dispatch' for e in m.events),kind)

    def test_common_transform_suppresses_boss_remap_and_uses_native_hurt_routes(self):
        motions={1205:122,1206:0}
        with patch.object(hurt,'MOTIONS',{**hurt.MOTIONS,**motions}),patch.object(hurt.h,'SCHEDULES',{**hurt.h.SCHEDULES,**SCHEDULES}):
            for action in motions:
                for source,target,index,first,count,raw in hurt.h.ROUTES:
                    m=hurt.ItemHurtMachine(self.plan,action=action);m.select(source,index)
                    hurt.ItemHurtLookupTests().checked(m,True,target=target)
        for name in ('HE_InputA','HE_InputB'):
            for action,motion in motions.items():
                for bank,expected in ((b.BANK,0),(b.OWN_BANK,1)):
                    m=PortableMachine(self.plan);m.put32(b.CURRENT,action);m.put64(b.CURRENT+0x38,bank);m.put32(b.PARAM+0x20,motion)
                    for off in (0xC,0xE):m.cpu.mem_write(b.INPUT+off,b'\1')
                    m.cpu.mem_write(m.data+0x29,b'\1');m.reset()
                    for reg,val in ((UC_X86_REG_RBX,b.CONTROLLER),(UC_X86_REG_RDI,b.INPUT),(UC_X86_REG_RDX,b.INPUT),(UC_X86_REG_R10,0),(UC_X86_REG_RCX,6)):m.cpu.reg_write(reg,val)
                    hook=m.by_name[name];m.run(hook['target'],hook['site']+hook['length'])
                    self.assertEqual(m.get32(m.data+0x24),expected,(name,action,bank))

    def test_parent_sites_fixed_entrypoints_and_aslr_relocations_unchanged(self):
        before=deepcopy(self.parent);self.assertEqual(k.apply_kodama_transform(self.parent),self.plan);self.assertEqual(before,self.parent)
        ranges=sorted((h['code_offset'],h['code_offset']+h['code_capacity']) for h in self.plan['hooks'])
        self.assertTrue(all(a[1]<=b0[0] for a,b0 in zip(ranges,ranges[1:])))
        for a,z in ranges:
            for c,d in self.plan['protected_data_pages']:self.assertFalse(max(a,c)<min(z,d))
        specs=relocation_specs(self.plan)
        for module,alloc in b.LAYOUTS:
            for old,new,spec in zip(assemble(self.parent,module,alloc),assemble(self.plan,module,alloc),specs):
                for key in ('site','patched','original','target','code_offset','code_capacity'):self.assertEqual(old[key],new[key])
                self.assertLessEqual(len(new['payload']),new['code_capacity'])
                if new['name']=='HE_LivingWeaponDigitNine':
                    self.assertEqual(new['payload'][:0x4000],old['payload'][:0x4000])
                    self.assertEqual(new['payload'][0x5800:],old['payload'][0x5800:])
                if new['name']=='HE_MapVisualRestorePrivate':self.assertEqual(new['payload'][0xA00:0xBDF],old['payload'][0xA00:0xBDF])
                raw=bytearray(base64.b64decode(spec['template']))
                for f in spec['fixups']:
                    if f['kind']==0:v=struct.pack('<Q',alloc+self.plan['data_offset'])
                    elif f['kind']==2:v=struct.pack('<Q',module+f['target'])
                    else:v=struct.pack('<i',module+f['target']-alloc-spec['code_offset']-f['next'])
                    raw[f['offset']:f['offset']+len(v)]=v
                self.assertEqual(bytes(raw),new['payload'])


if __name__=='__main__':unittest.main()
