"""CPU validation of a one-shot early event call, including hostile volatile registers.

The native scheduler call is a recorded boundary here; separate local native
CPU replay verifies which event it selects. Neither test asserts target damage.
"""
import base64
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta613_plan as load_plan,assemble,relocation_specs
from hinoenma_general_jutsu import apply_general_jutsu
import hinoenma_general_jutsu_timing as h
import test_general_jutsu_portable as generic
import test_spell_event_catchup_portable as old
from unicorn.x86_const import *

FIXTURE=json.loads((ROOT/'tests/fixtures/general-jutsu-native.json').read_text('utf8'))
CHAINS=json.loads((ROOT/'tests/fixtures/general-jutsu-chain-native.json').read_text('utf8'))
ACTIONS={**FIXTURE['actions'],**CHAINS['actions']}
PARENT=apply_general_jutsu(load_plan())
PLAN=h.apply_general_jutsu_timing(PARENT)
HOOKS=assemble(PLAN,old.BASE,old.ALLOC)
SP=old.STACK+0xF000  # Actual alignment at native CALL site 718950.


class Fixture(old.Fixture):
    def __init__(self,action=986,item=None):
        with patch.object(old,'NEW_H',HOOKS):
            super().__init__(action)
        if action in h.RULES:
            cat,motion,first,last=h.RULES[action]
            self.u.mem_write(old.PARAM,bytes.fromhex(ACTIONS[str(action)]['params_raw']))
            if item is None:
                item=next(r['id'] for r in FIXTURE['items'] if r['category']==cat and r['id']!=7739)
            self.d(old.CTL+0x548,item)
            self.d(old.CTL+0x54C,cat)
        for index,raw in FIXTURE['events'].items():
            i=int(index)
            if i>=10000:
                continue
            address=old.ACT+0x10000+i*128
            self.q(old.ARR+i*8,address)
            self.u.mem_write(address,bytes.fromhex(raw))
        self.global_events=old.ACT+0x19000
        ptr=old.BASE+PLAN['targets']['item_assets']-0x1E0
        if not any(a<=ptr<=b for a,b,_ in self.u.mem_regions()):
            self.u.mem_map(ptr&~0xfff,0x1000)
        self.q(ptr,old.ACT+0x18000)
        self.q(old.ACT+0x18000,old.ACT+0x18100)
        self.q(old.ACT+0x18100+0x468,self.global_events)
        self.q(old.ACT+0x18100+0x470,self.global_events+0x100)
        self.u.mem_write(self.global_events+0x80,bytes.fromhex(FIXTURE['events']['10001']))
        self.extra=[]
        self.initial={}

    def trace(self,u,at,size,user):
        if at==old.BASE+0x718955:
            u.emu_stop()
            return
        raw=bytes(u.mem_read(at,size))
        if raw[:1]!=b'\xe8':
            return
        target=at+5+struct.unpack_from('<i',raw,1)[0]
        if old.ALLOC<=target<old.ALLOC+0x69000:
            return
        if target!=old.BASE+0x704E50:
            raise AssertionError('Unexpected native call')
        frame=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_X86_REG_XMM2)&0xffffffff))[0]
        extra=old.ALLOC+h.OFFSET<=at<old.ALLOC+0x19000
        self.native.append(dict(frame=frame,r9=u.reg_read(UC_X86_REG_R9),extra=extra))
        if u.reg_read(UC_X86_REG_RSP)%16:
            raise AssertionError('Native scheduler CALL site is not aligned')
        if u.reg_read(UC_X86_REG_RCX)!=old.CTL or u.reg_read(UC_X86_REG_RDX)!=old.REC:
            raise AssertionError('Native scheduler owner mismatch')
        if extra:
            self.extra.append(frame)
            u.mem_write(u.reg_read(UC_X86_REG_RSP),b'\xA5'*32)
            for reg in (UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11,*old.XMMS[:6]):
                u.reg_write(reg,0xBADF00D123456789)
            u.reg_write(UC_X86_REG_MXCSR,0x1FC5)
            u.reg_write(UC_X86_REG_EFLAGS,0x202)
        else:
            for reg,value in self.initial.items():
                # Existing spell/Salt hooks may intentionally set R9B once.
                if reg!=UC_X86_REG_R9 and u.reg_read(reg)!=value:
                    raise AssertionError('Original scheduler ABI changed: '+str(reg))
            if u.reg_read(UC_X86_REG_EFLAGS)!=0x246 or u.reg_read(UC_X86_REG_MXCSR)!=0x1F80:
                raise AssertionError('Flags/MXCSR not restored')
        u.reg_write(UC_X86_REG_RIP,at+size)

    def run(self,frame,catchup):
        for n,reg in enumerate(old.GPRS+old.XMMS):
            self.u.reg_write(reg,0x112233445500+n)
        self.u.reg_write(UC_X86_REG_RCX,old.CTL)
        self.u.reg_write(UC_X86_REG_RDX,old.REC)
        self.u.reg_write(UC_X86_REG_R9,catchup)
        self.u.reg_write(UC_X86_REG_XMM2,h.float_bits(frame))
        self.u.reg_write(UC_X86_REG_RSP,SP)
        self.u.reg_write(UC_X86_REG_MXCSR,0x1F80)
        self.u.reg_write(UC_X86_REG_EFLAGS,0x246)
        self.initial={reg:self.u.reg_read(reg) for reg in old.GPRS+old.XMMS}
        n=len(self.native)
        self.u.emu_start(old.ALLOC+0x1040,old.BASE+0x718956,count=20000)
        if self.u.reg_read(UC_X86_REG_RSP)!=SP:
            raise AssertionError('Unbalanced event stack')
        hits=self.native[n:]
        if not hits or hits[-1]['extra']:
            raise AssertionError('Original scheduler call missing')
        return hits


class TimingTests(unittest.TestCase):
    def test_observed_kunai_gap_and_all_family_boundaries_once(self):
        for action,(_,_,first,last) in h.RULES.items():
            for frame in (first+1,last-1):
                f=Fixture(action)
                self.assertEqual(len(f.run(0,1)),1)
                self.assertEqual(f.marker(),3)
                self.assertEqual(f.run(frame,0),[dict(frame=first,r9=0,extra=True),dict(frame=frame,r9=0,extra=False)])
                self.assertEqual(f.marker(),0)
                self.assertEqual(len(f.run(frame+1,0)),1)
            for frame in (0,1,first,last,last+1,-1,float('inf'),float('nan')):
                f=Fixture(action);f.run(0,1)
                self.assertEqual(len(f.run(frame,0)),1,(action,frame))

    def test_natural_progress_unarmed_and_interrupted_cast_never_replay(self):
        for action,(_,_,first,_) in h.RULES.items():
            f=Fixture(action);self.assertEqual(len(f.run(first+1,0)),1)
            f.run(0,1);self.assertEqual(len(f.run(1,0)),1)
            self.assertEqual(len(f.run(first+1,0)),1)
            f.run(0,1);f.d(old.REC,0);f.run(1,0);f.d(old.REC,action)
            self.assertEqual(len(f.run(first+1,0)),1)
            f.run(0,1);f.run(first+1,1)
            self.assertEqual(f.extra,[])

    def test_changed_player_request_schedule_and_descriptors_reject(self):
        edits=((old.ACT+4,0x20000,4),(old.ACT+0xEF0,1,4),(old.META+0xC,0,4),
            (old.DATA+0x1C,4,4),(old.PROXY+8,0,8),(old.COMP+0x20,0,8),
            (old.CTL+0x548,999,4),(old.CTL+0x54C,5,4),(old.CTL+0x550,2,4),
            (old.CTL+0x554,1,4),(old.CTL+0x558,1,8),(old.CTL+0x570,1,1),
            (old.CTL+0x728,1,8),(old.CTL+0x24,h.float_bits(2),4),
            (old.CTL+0x68,1,4),(old.REC+0x38,0,8),(old.PARAM+0x20,1,4))
        for at,value,width in edits:
            f=Fixture();f.run(0,1);f.u.mem_write(at,value.to_bytes(width,'little'))
            self.assertEqual(len(f.run(6,0)),1,hex(at))
        for off in range(96):
            f=Fixture();f.run(0,1);at=old.PARAM+0x40+off
            f.b(at,f.u.mem_read(at,1)[0]^1)
            self.assertEqual(len(f.run(6,0)),1,off)
        for event in (18,31):
            for off in range(128):
                f=Fixture();f.run(0,1);at=old.ACT+0x10000+event*128+off
                f.b(at,f.u.mem_read(at,1)[0]^1)
                self.assertEqual(len(f.run(6,0)),1,(event,off))

    def test_existing_salt_and_spell_catchup_remain_native(self):
        f=Fixture(982,item=7739)
        self.assertEqual(f.run(0,1)[0]['r9'],1)
        self.assertEqual(f.run(16,0)[0]['r9'],1)
        self.assertEqual(len(f.extra),0)
        for action in (42,1165):
            f=Fixture(action);f.run(0,1)
            self.assertEqual(f.run(77,0),[dict(frame=77,r9=1,extra=False)])

    def test_generic_entry_lookup_injury_and_moving_recast_still_work(self):
        generic.GeneralJutsuTests.setUpClass()
        with patch.object(generic.GeneralJutsuTests,'plan',PLAN):
            for name in ('test_complete_catalogue_preserves_native_effects_and_item_stock',
                         'test_all_families_resolve_common_bank_instead_of_colliding_boss_action',
                         'test_new_family_injury_and_input_remapping_protection',
                         'test_existing_special_cases_and_released_dispersal_stay_intact'):
                getattr(generic.GeneralJutsuTests(name),name)()

    def test_consecutive_throw_input_and_injury_native_routes(self):
        schedules={a:bytes.fromhex(ACTIONS[str(a)]['params_raw'])[0x40:0xA0].hex() for a in h.CHAIN_SCHEDULES}
        self.assertEqual(schedules,h.CHAIN_SCHEDULES)
        inj=generic.nine.old.hurt
        motions={a:h.RULES[a][1] for a in schedules}
        with patch.object(inj,'MOTIONS',{**inj.MOTIONS,**motions}),patch.object(inj.h,'SCHEDULES',{**inj.h.SCHEDULES,**schedules}):
            for a in schedules:
                for source,target,index,first,count,raw in inj.h.ROUTES:
                    m=inj.ItemHurtMachine(PLAN,action=a);m.select(source,index)
                    inj.ItemHurtLookupTests().checked(m,True,target=target)
        b=generic.b
        for name in ('HE_InputA','HE_InputB'):
            for a,motion in motions.items():
                for owner,ok in ((b.BANK,True),(b.OWN_BANK,False)):
                    m=generic.PortableMachine(PLAN);m.put32(b.CURRENT,a);m.put64(b.CURRENT+0x38,owner);m.put32(b.PARAM+0x20,motion)
                    for off in (0xC,0xE):m.cpu.mem_write(b.INPUT+off,b'\1')
                    m.cpu.mem_write(m.data+0x29,b'\1');m.reset()
                    for reg,val in ((UC_X86_REG_RBX,b.CONTROLLER),(UC_X86_REG_RDI,b.INPUT),(UC_X86_REG_RDX,b.INPUT),(UC_X86_REG_R10,0),(UC_X86_REG_RCX,6)):m.cpu.reg_write(reg,val)
                    hook=m.by_name[name];m.run(hook['target'],hook['site']+hook['length'])
                    self.assertEqual(m.get32(m.data+0x24),int(not ok))

    def test_alternating_native_casts_rearm_and_do_not_duplicate(self):
        for sequence in ((986,612,986,612),(166,613,166,613)):
            f=Fixture(sequence[0]);cat=h.RULES[sequence[0]][0]
            for action in sequence:
                f.d(old.REC,action);f.u.mem_write(old.PARAM,bytes.fromhex(ACTIONS[str(action)]['params_raw']))
                f.run(0,1)
                first=h.RULES[action][2]
                self.assertEqual(f.run(first+4,0)[0],dict(frame=first,r9=0,extra=True))
                self.assertEqual(len(f.run(first+5,0)),1)
            self.assertEqual(len(f.extra),4)

    def test_exact_parent_native_sites_carrier_prefix_and_relocations(self):
        self.assertEqual(h.apply_general_jutsu_timing(PARENT),PLAN)
        specs=relocation_specs(PLAN)
        for module,alloc in generic.b.LAYOUTS:
            changes=[]
            for a,b,spec in zip(assemble(PARENT,module,alloc),assemble(PLAN,module,alloc),specs):
                for key in ('site','patched','target','code_capacity','original'):
                    self.assertEqual(a[key],b[key])
                self.assertLessEqual(len(b['payload']),b['code_capacity'])
                if a['payload']!=b['payload']:
                    changes.append(a['name'])
                    if a['name']==h.CARRIER:self.assertTrue(b['payload'].startswith(a['payload']))
                raw=bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind']==0:value=struct.pack('<Q',alloc+PLAN['data_offset'])
                    elif fix['kind']==2:value=struct.pack('<Q',module+fix['target'])
                    else:value=struct.pack('<i',module+fix['target']-alloc-spec['code_offset']-fix['next'])
                    raw[fix['offset']:fix['offset']+len(value)]=value
                self.assertEqual(bytes(raw),b['payload'])
            self.assertEqual(set(changes),set(PLAN['general_jutsu_timing_candidate']['changed_hooks']))


if __name__=='__main__':unittest.main()
