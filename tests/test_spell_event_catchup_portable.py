"""Offline CPU tests; no game process APIs are used."""
import hashlib
import json
import math
import struct
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"tools"),str(ROOT/"src")]
from build_profile import load_beta61_plan as load_plan, assemble
PLAN=load_plan()
from hinoenma_spell_event_catchup import apply_spell_event_catchup, ENTRY, CARRIER, DESCRIPTORS
from hinoenma_wind_weakness_dragon import SCHEDULE_HEX
candidate=lambda:apply_spell_event_catchup(PLAN)
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn.x86_const import *

BASE=0x140000000; ALLOC=0x144000000; DATA=ALLOC+0xF000
ACT=0x20000000; CTL=ACT+0x2000; REC=ACT+0x4000; PARAM=ACT+0x5000
BANK=ACT+0x6000; ARR=ACT+0x7000; D17=ACT+0x8000; D31=ACT+0x9000
PROXY=ACT+0xA000; COMP=ACT+0xB000; META=ACT+0xD000; MOTION=ACT+0xE000; SENT=ACT+0xF000
STACK=0x30000000; SP=STACK+0xF008; STATE=DATA+0x4E80
GPRS=(UC_X86_REG_RAX,UC_X86_REG_RBX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_RSI,UC_X86_REG_RDI,
      UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15)
XMMS=tuple(globals()['UC_X86_REG_XMM'+str(n)] for n in range(16))
NEW=candidate(); OLD_H=assemble(PLAN,BASE,ALLOC); NEW_H=assemble(NEW,BASE,ALLOC)

class Fixture:
    def __init__(self,action=1165, old=False):
        self.u=Uc(UC_ARCH_X86,UC_MODE_64); self.native=[]; self.writes=[]
        self.u.mem_map(ACT,0x20000); self.u.mem_map(STACK,0x10000)
        self.u.mem_map(ALLOC,0x69000)
        slot=BASE+PLAN['targets']['player_slot']; self.u.mem_map(slot & ~0xfff,0x1000)
        self.u.mem_map(BASE+0x718000,0x1000)
        for h in OLD_H if old else NEW_H:self.u.mem_write(h['target'],h['payload'])
        self.q(slot,ACT); self.q(DATA+0x10,ACT); self.d(DATA+4,0x58E5E); self.d(DATA+0x1C,3)
        self.d(ACT,0x58E5E); self.d(ACT+4,0x10000)
        self.q(ACT+0x230,PROXY); self.q(PROXY,ACT); self.q(PROXY+8,CTL)
        self.q(ACT+0x240,COMP); self.q(COMP,ACT); self.q(COMP+0x108,ACT); self.q(COMP+0x20,9000)
        self.q(ACT+0xE90,META); self.d(META,0x58E5E); self.d(META+0xC,1)
        self.q(ACT+0x38,MOTION); self.d(MOTION+0x48,2)
        self.q(CTL+0x50,ACT); self.q(CTL+0x58,REC); self.d(CTL+0x68,2); self.q(CTL+0x80,BANK)
        self.f(CTL+0x24,1); self.d(CTL+0x550,1)
        self.q(CTL+0x720,SENT); self.q(SENT,SENT); self.q(SENT+8,SENT)
        self.d(REC,action); self.q(REC+0x20,PARAM); self.q(REC+0x38,BANK); self.b(REC+0x40,1)
        if action in (42,1165):
            self.d(PARAM+0x20,111); self.d(PARAM+0x34,90111 if action==1165 else -1)
            self.u.mem_write(PARAM+0x40,bytes.fromhex(SCHEDULE_HEX[action]))
            self.u.mem_write(D17,bytes.fromhex(DESCRIPTORS[17]))
            self.u.mem_write(D31,bytes.fromhex(DESCRIPTORS[31]))
            self.d(CTL+0x548,26116 if action==1165 else 44930); self.d(CTL+0x54C,25 if action==1165 else 9)
        else:
            from hinoenma_special_item_actions import SCHEDULE_HEX as SALT_SCHEDULE
            self.d(PARAM+0x20,120); self.u.mem_write(PARAM+0x40,bytes.fromhex(SALT_SCHEDULE[982]))
            self.d(CTL+0x548,7739); self.d(CTL+0x54C,6)
        self.q(BANK+0x80,ARR); self.w(BANK+0x88,200)
        self.q(ARR+17*8,D17); self.q(ARR+31*8,D31)
        self.u.hook_add(UC_HOOK_CODE,self.trace); self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
    def b(self,a,v):self.u.mem_write(a,struct.pack('<B',v))
    def w(self,a,v):self.u.mem_write(a,struct.pack('<H',v))
    def d(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
    def q(self,a,v):self.u.mem_write(a,struct.pack('<Q',v))
    def f(self,a,v):self.u.mem_write(a,struct.pack('<f',v))
    def marker(self):return struct.unpack('<I',self.u.mem_read(STATE,4))[0]
    def write(self,u,access,at,size,value,user):
        if not (STACK<=at<at+size<=STACK+0x10000 or STATE<=at<at+size<=STATE+0x24):
            raise AssertionError('Unexpected write '+hex(at))
        self.writes.append((at,size,value))
    def trace(self,u,at,size,user):
        if at==BASE+0x718955:u.emu_stop();return
        raw=bytes(u.mem_read(at,size))
        if raw[:1]==b'\xe8':
            target=at+5+struct.unpack_from('<i',raw,1)[0]
            assert target==BASE+0x704E50
            self.native.append(dict(r9=u.reg_read(UC_X86_REG_R9),frame=u.reg_read(UC_X86_REG_XMM2)&0xffffffff,
                rcx=u.reg_read(UC_X86_REG_RCX),rdx=u.reg_read(UC_X86_REG_RDX),rsp=u.reg_read(UC_X86_REG_RSP),
                flags=u.reg_read(UC_X86_REG_EFLAGS),regs={r:u.reg_read(r) for r in GPRS+XMMS}))
            # Observe ABI before this native call; never emulate effects here.
            u.reg_write(UC_X86_REG_RIP,at+size)
    def run(self,frame,catchup):
        for n,r in enumerate(GPRS+XMMS):self.u.reg_write(r,0x112233445500+n)
        self.u.reg_write(UC_X86_REG_RCX,CTL); self.u.reg_write(UC_X86_REG_RDX,REC)
        self.u.reg_write(UC_X86_REG_R9,catchup); self.u.reg_write(UC_X86_REG_XMM2,struct.unpack('<I',struct.pack('<f',frame))[0])
        self.u.reg_write(UC_X86_REG_EFLAGS,0x246); self.u.reg_write(UC_X86_REG_RSP,SP)
        initial={r:self.u.reg_read(r) for r in GPRS+XMMS}; before=len(self.native)
        self.u.emu_start(ALLOC+0x1040,BASE+0x718956,count=20000)
        assert len(self.native)==before+1
        hit=self.native[-1]
        assert hit['rsp']==SP and hit['flags']==0x246
        for r,v in initial.items():
            if r!=UC_X86_REG_R9:assert hit['regs'][r]==v, r
        assert self.u.reg_read(UC_X86_REG_RSP)==SP
        return hit['r9']

class Cases(unittest.TestCase):
    def test_layout(self):
        changes=[a['name'] for a,b in zip(OLD_H,NEW_H) if a['payload']!=b['payload']]
        self.assertEqual(changes,[CARRIER,ENTRY])
        for a,b in zip(OLD_H,NEW_H):
            self.assertEqual(a['patched'],b['patched']);self.assertLessEqual(len(b['payload']),b['code_capacity'])
        a=next(h for h in OLD_H if h['name']==CARRIER); b=next(h for h in NEW_H if h['name']==CARRIER)
        self.assertEqual(a['payload'],b['payload'][:len(a['payload'])])
    def test_two_spells_once(self):
        for action in (42,1165):
            for frame in (18,50,76,77,103):
                with self.subTest(action=action,frame=frame):
                    f=Fixture(action);self.assertEqual(f.run(0,1),1);self.assertEqual(f.marker(),2)
                    self.assertEqual(f.run(frame,0),1);self.assertEqual(f.marker(),0)
                    self.assertEqual(f.run(frame,0),0)
    def test_normal_progress_disarms(self):
        f=Fixture();f.run(0,1);self.assertEqual(f.run(1,0),0);self.assertEqual(f.run(77,0),0)
    def test_boundary_rejections(self):
        for frame in (0,1,17,104,150,-1,float('nan'),float('inf')):
            with self.subTest(frame=frame):
                f=Fixture();f.run(0,1);self.assertEqual(f.run(frame,0),0)
    def test_owned_scope_rejects(self):
        edits=[(ACT+4,0x20000),(ACT+0xEF0,1),(META+0xC,2),(DATA+0x1C,4),
            (CTL+0x548,4998),(CTL+0x54C,9),(CTL+0x550,2),(CTL+0x554,1),(CTL+0x557,1),
            (CTL+0x570,1),(CTL+0x68,1),(MOTION+0x48,1),(MOTION+0x50,1),
            (REC,42),(PARAM+0x20,112),(PARAM+0x34,-1),(PARAM+0x40,0),(D17+0x18,9)]
        for address,value in edits:
            with self.subTest(address=hex(address)):
                f=Fixture();f.run(0,1);f.d(address,value);self.assertEqual(f.run(77,0),0);self.assertEqual(f.marker(),0)
    def test_busy_object_and_changed_owner(self):
        for address,value in ((CTL+0x728,1),(CTL+0x558,ACT),(CTL+0x50,ACT+0x10000),
            (REC+0x38,BANK+0x1000),(COMP+0x20,0),(PROXY+8,0),(ACT+0x240,0)):
            f=Fixture();f.run(0,1);f.q(address,value);self.assertEqual(f.run(77,0),0)
    def test_bad_step_or_r9(self):
        for step,r9 in ((2,0),(0,0),(-1,0),(1,2)):
            f=Fixture();f.run(0,1);f.f(CTL+0x24,step);self.assertEqual(f.run(77,r9),r9)
    def test_salt_unchanged(self):
        old,new=Fixture(982,True),Fixture(982)
        for frame,r9 in ((0,1),(16,0),(16,0),(35,0),(0,1),(1,0),(16,0)):
            self.assertEqual(old.run(frame,r9),new.run(frame,r9))
            self.assertEqual(bytes(old.u.mem_read(STATE,0x40)),bytes(new.u.mem_read(STATE,0x40)))
    def test_interruption_disarms(self):
        f=Fixture();f.run(0,1);f.d(REC,0);f.run(77,0);f.d(REC,1165);self.assertEqual(f.run(77,0),0)
    def test_existing_native_catchup_not_changed(self):
        f=Fixture();f.run(0,1);self.assertEqual(f.run(77,1),1);self.assertEqual(f.marker(),0)
    def test_no_unarmed_fix(self):self.assertEqual(Fixture().run(77,0),0)

if __name__=="__main__":unittest.main()
