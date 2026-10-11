"""Synthetic loaded owners for portable execution tests; no game assets."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import load_plan, assemble
from hinoenma_manual_purification import MENU_FIELDS, SUBMENU_FIELDS
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

MODULE, ALLOCATION, HEAP, STACK, STOP = 0x140000000, 0x144000000, 0x150000000, 0x160000000, 0x170000000
PLAN = load_plan()
HOOKS = assemble(PLAN, MODULE, ALLOCATION)[71:]
GPRS = (UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RCX, UC_X86_REG_RDX,
        UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_R8, UC_X86_REG_R9,
        UC_X86_REG_R10, UC_X86_REG_R11, UC_X86_REG_R12, UC_X86_REG_R13,
        UC_X86_REG_R14, UC_X86_REG_R15)
XMM = tuple(globals()['UC_X86_REG_XMM'+str(n)] for n in range(6))


class CPU:
    def __init__(self, index=0, pressed=True):
        self.uc, self.pages = Uc(UC_ARCH_X86, UC_MODE_64), set()
        self.next = HEAP
        self.d, self.core = ALLOCATION+0x42000, ALLOCATION+0xF000
        self.put(self.d, bytes(0x1000)); self.put(self.core, bytes(0x1000))
        self.put(STACK, bytes(0x5000)); self.put(STOP, b'\xc3')
        self.actor, self.ctl, self.target, self.tc = self.alloc(0x2000), self.alloc(), self.alloc(0x2000), self.alloc()
        self.stats, self.ts, self.proxy, self.tp = (self.alloc() for _ in range(4))
        self.put(self.actor, struct.pack('<IHH', 0x58E5E, 0, 1))
        self.put(self.target, struct.pack('<IHH', 0x1DC1C, 0, 19569))
        for actor, ctl, stats, proxy in ((self.actor, self.ctl, self.stats, self.proxy),
                                       (self.target, self.tc, self.ts, self.tp)):
            self.q(actor+0x240, stats); self.q(stats, actor); self.q(stats+0x20, 99 if actor == self.actor else 1)
            self.q(actor+0x230, proxy); self.q(proxy, actor); self.q(proxy+8, ctl); self.q(ctl+0x50, actor)
        self.q(self.ctl+0x640, self.target)
        self.metadata = self.alloc(); self.q(self.target+0xE90, self.metadata)
        self.u(self.metadata, 0x1DC1C); self.u(self.metadata+0xC, 1)
        self.native_bank, self.common, self.bank, self.enemy_bank = (self.alloc() for _ in range(4))
        self.q(self.ctl+0x70, self.native_bank); self.q(self.ctl+0x80, self.common); self.q(self.tc+0x70, self.enemy_bank)
        self.idle = self.record(0, self.native_bank)
        self.common_idle = self.record(0, self.common)
        self.dispatch = self.record(3008, self.bank)
        self.finish = self.record(3491, self.bank, 1200)
        # The real windup does not carry the native active-pair query86 bit29.
        self.u(self.params(self.finish)+0x18, 0x194C0000)
        self.paired = self.record(4000, self.bank, 1201)
        self.ready = self.record(3203, self.enemy_bank); self.enemy = self.record(4001, self.enemy_bank)
        self.u(self.params(self.ready)+0x18, 0x100)
        self.q(self.ctl+0x58, self.idle); self.q(self.tc+0x58, self.ready)
        self.rotation = self.transition(self.idle, -1, -1, 38, heavy=True)
        self.put(self.rotation+0x14, struct.pack('<h', 38))
        self.heavy = self.transition(self.common_idle, -1, -1, 3008, heavy=True)
        self.windup_transition = self.transition(self.dispatch, 380, 381, 3491, blend=3)
        self.paired_transition = self.transition(self.finish, 208, -1, 4000)
        self.terminal = self.transition(self.paired, -1, -1, 3000)
        self.records(self.native_bank, [self.idle]); self.records(self.common, [self.common_idle])
        self.records(self.bank, [self.dispatch, self.finish, self.paired])
        self.records(self.enemy_bank, [self.ready, self.enemy])
        self.package, self.wrapper = self.alloc(), self.alloc()
        self.q(self.package, MODULE+0x12C5510); self.q(self.package+0x1B8, self.wrapper); self.q(self.wrapper+0x468, self.bank)
        self.main, self.aux = self.motion_resource(), self.motion_resource()
        self.q(self.package+0x188, self.main); self.q(self.package+0x190, self.aux)
        self.primary, self.secondary = self.event_resource(), self.event_resource()
        self.q(self.package+0x198, self.primary['wrapper']); self.q(self.package+0x1A0, self.secondary['wrapper'])
        self.motion, self.baseline_motion = self.alloc(), self.alloc()
        self.q(self.actor+0x38, self.motion)
        for n in (1, 5): self.q(self.motion+8+n*8, 0)
        self.manager, self.event_state = self.alloc(), self.alloc()
        self.q(self.actor+0x68, self.manager); self.q(self.manager+8, self.actor)
        self.q(self.manager+0x40, self.event_state); self.q(self.event_state+8, self.actor)
        self.temp_owner = self.alloc(0x159000); self.temp = self.temp_owner+0x158184
        self.put(self.temp, b'\x07'); self.u(self.temp+4, 1); self.q(MODULE+0x189F408, self.temp_owner)
        self.tree, self.node = self.alloc(), self.alloc()
        self.q(MODULE+0x1871700, self.tree); self.q(self.tree+8, self.node)
        self.u(self.node+0x20, 1); self.q(self.node+0x28, self.package)
        self.q(MODULE+PLAN['targets']['player_slot'], self.actor)
        self.q(self.core+0x10, self.actor); self.u(self.core+0x1C, 3)
        self.window, self.ui = self.alloc(), self.alloc()
        self.q(MODULE+PLAN['targets']['native_window_owner'], self.window); self.put(self.window+0x4A, b'\x01')
        self.q(MODULE+PLAN['targets']['tutorial_ui_owner'], self.ui)
        for owner, field in MENU_FIELDS+SUBMENU_FIELDS+((0x318, 0x60),):
            at = self.alloc(); self.q(self.ui+owner, at); self.u(at+field, 0)
        self.calls, self.pressed, self.stopped = [], pressed, None
        for hook in HOOKS:
            self.put(hook['target'], hook['payload']); self.put(hook['site']+hook['length'], b'\xc3')
        for rva in (0x721010, 0x6E86B8, 0x216ADD, 0x216B32,
                    PLAN['targets']['native_query_false_epilogue']): self.put(MODULE+rva, b'\xc3')
        def control(uc, address, size, user):
            if address == MODULE+0x721010:
                assert uc.reg_read(UC_X86_REG_RSP)%16 == 8
                assert uc.reg_read(UC_X86_REG_RCX) == self.ctl
                assert uc.reg_read(UC_X86_REG_RDX) == self.heavy
                self.calls.append(address)
                for reg in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11):
                    uc.reg_write(reg, 0xDEAD)
                for reg in XMM: uc.reg_write(reg, 0)
                uc.reg_write(UC_X86_REG_RAX, int(self.pressed))
            if address in (STOP, self.hook['site']+self.hook['length'], MODULE+0x6E86B8,
                           MODULE+0x216ADD, MODULE+0x216B32,
                           MODULE+PLAN['targets']['native_query_false_epilogue']):
                self.stopped = address; uc.emu_stop()
        self.uc.hook_add(UC_HOOK_CODE, control)
        self.prepare(0)
        if index:
            self.pressed = False; self.run(); self.pressed = pressed
            if self.value(0) != 0x4643524F: raise AssertionError('Synthetic bootstrap rejected')
            self.prepare(index)

    def alloc(self, size=0x1000):
        at = self.next; self.next += (size+0xFFF)&~0xFFF
        self.put(at, bytes(size)); return at

    def put(self, at, raw):
        for page in range(at&~0xFFF, (at+len(raw)+0xFFF)&~0xFFF, 0x1000):
            if page not in self.pages: self.uc.mem_map(page, 0x1000); self.pages.add(page)
        self.uc.mem_write(at, raw)

    def q(self, at, value): self.put(at, struct.pack('<Q', value))
    def u(self, at, value): self.put(at, struct.pack('<I', value))
    def value(self, off): return struct.unpack('<I', self.uc.mem_read(self.d+off, 4))[0]
    def qvalue(self, at): return struct.unpack('<Q', self.uc.mem_read(at, 8))[0]
    def params(self, rec): return self.qvalue(rec+0x20)

    def set_head(self, template, instance, ready=3203, metadata_offset=0):
        self.put(self.target, struct.pack('<IHH', template, 0, instance))
        self.u(self.ready, ready)
        self.metadata = self.alloc()+metadata_offset
        self.q(self.target+0xE90, self.metadata)
        self.u(self.metadata, template); self.u(self.metadata+0xC, 1)

    def record(self, ident, bank, motion=0):
        rec, params = self.alloc(), self.alloc()
        self.u(rec, ident); self.put(rec+0x40, b'\x01'); self.q(rec+0x38, bank); self.q(rec+0x20, params)
        self.u(params+0x20, motion); self.u(params+0x34, 0xFFFFFFFF)
        return rec

    def records(self, bank, records):
        array = self.alloc(); self.q(bank+0x128, array); self.u(bank+0x130, len(records))
        for n, rec in enumerate(records): self.q(array+n*8, rec)

    def transition(self, rec, query1, query2, action, blend=0, heavy=False):
        at, array = self.alloc(), self.alloc()
        self.put(at, bytes(0x30)); self.put(at, struct.pack('<2h', query1, query2))
        self.put(at+0x14, struct.pack('<h', action)); self.put(at+0x17, bytes([blend]))
        if heavy:
            self.put(at, bytes.fromhex('ffffffffffffffffffff000101ffff0000000000c00b0000ff806464000000000080ff7fffffffffffffffffffffffff'))
        self.q(rec+0x78, array); self.put(rec+0x80, struct.pack('<HH', 0, 1)); self.q(array, at)
        return at

    def motion_resource(self):
        resource, array, mapping, pairs = (self.alloc() for _ in range(4))
        self.q(resource, MODULE+0x13C8FA0); self.q(resource+0x468, array); self.q(resource+0x470, array+16)
        self.q(resource+0x480, mapping); self.u(mapping+8, 4); self.q(mapping+0x10, pairs)
        self.put(pairs, b'\xff'*32)
        for n, frames in enumerate((95,409)):
            clip = self.alloc(); self.q(array+n*8, clip)
            self.put(clip+0x18, struct.pack('<fH', 60.0, frames))
            self.put(pairs+(n+1)*8, struct.pack('<Ii', 1200+n, n))
        return resource

    def event_resource(self):
        wrapper, owner, bank, mapping, pairs = (self.alloc() for _ in range(5))
        self.q(wrapper, MODULE+0x12C5408); self.q(wrapper+0x468, owner)
        self.q(owner, bank); self.q(owner+8, mapping)
        self.put(bank, b'TMG_PACK'); self.u(bank+0x10,0x1000); self.u(bank+0x14,2); self.u(bank+0x20,0x30)
        self.u(mapping+8,4); self.q(mapping+0x10,pairs); self.put(pairs,b'\xff'*32)
        descriptors=[]
        for n,count in enumerate((19,42)):
            offset=0x100+n*0x400; self.u(bank+0x30+n*4,offset)
            desc=bank+offset;descriptors.append(desc)
            self.u(desc+4,count);self.u(desc+8,0x24)
            for i in range(count):self.put(desc+0x24+i*12,struct.pack('<3I',i,40,i))
            self.put(pairs+(n+1)*8,struct.pack('<Ii',1200+n,n))
        return dict(wrapper=wrapper,owner=owner,bank=bank,map=mapping,pairs=pairs,descriptors=descriptors)

    def prepare(self, index, motion_id=1200, auxiliary=False):
        self.hook = HOOKS[index]; self.stopped = None
        self.rsp = STACK+0x3008
        for n, reg in enumerate(GPRS): self.uc.reg_write(reg, 0x88880000+n)
        for n, reg in enumerate(XMM): self.uc.reg_write(reg, (1<<120)+n)
        self.uc.reg_write(UC_X86_REG_RSP,self.rsp);self.uc.reg_write(UC_X86_REG_EFLAGS,0x246)
        self.q(self.rsp,STOP)
        if index == 0:
            self.uc.reg_write(UC_X86_REG_RCX,self.ctl);self.uc.reg_write(UC_X86_REG_RDX,self.idle)
            return
        self.u(self.d+0x74,1)
        self.q(self.ctl+0x58,self.paired if motion_id==1201 else self.finish)
        if index == 1:
            self.uc.reg_write(UC_X86_REG_RSI,self.ctl+0x70);self.uc.reg_write(UC_X86_REG_RAX,0)
            self.uc.reg_write(UC_X86_REG_RBX,0);self.uc.reg_write(UC_X86_REG_R10,3008)
        elif index == 2:
            self.uc.reg_write(UC_X86_REG_RDI,self.motion);self.uc.reg_write(UC_X86_REG_RCX,5 if auxiliary else 1)
            self.uc.reg_write(UC_X86_REG_RDX,motion_id)
        elif index == 3:
            self.uc.reg_write(UC_X86_REG_RCX,self.motion);self.uc.reg_write(UC_X86_REG_R9,5 if auxiliary else 1)
            self.uc.reg_write(UC_X86_REG_RDX,motion_id)
        elif index == 4:
            self.uc.reg_write(UC_X86_REG_R14,self.manager);self.uc.reg_write(UC_X86_REG_RCX,4 if auxiliary else 1)
            self.uc.reg_write(UC_X86_REG_RDX,motion_id)
        elif index in (5,6):
            self.uc.reg_write(UC_X86_REG_RDI,self.motion);self.uc.reg_write(UC_X86_REG_RCX,5 if auxiliary else 1)
            self.uc.reg_write(UC_X86_REG_RSI,motion_id);self.uc.reg_write(UC_X86_REG_R14,0)
        elif index == 9:
            self.q(self.ctl+0x5B0,0);self.q(self.ctl+0x5D8,0)
            self.uc.reg_write(UC_X86_REG_RCX,self.ctl);self.uc.reg_write(UC_X86_REG_RDI,self.ctl)
            self.uc.reg_write(UC_X86_REG_RSI,self.uc.reg_read(UC_X86_REG_RSI)&~255)
        else:
            self.pair()
            if index == 7:
                self.start,self.end=self.alloc(),self.alloc()
                for at in (self.start,self.end):self.put(at,struct.pack('<4f',1.0,2.0,3.0,0.0))
                self.uc.reg_write(UC_X86_REG_R8,self.start);self.uc.reg_write(UC_X86_REG_R9,self.end)
                self.q(self.rsp,MODULE+0x6E86B8);self.uc.reg_write(UC_X86_REG_R15,self.target)
            else:
                self.rsp=STACK+0x2000;self.uc.reg_write(UC_X86_REG_RSP,self.rsp)
                self.query,self.geometry=self.alloc(),self.alloc()
                self.put(self.query+0x20,struct.pack('<3f',1.0,2.0,3.0))
                self.put(self.query+0x30,struct.pack('<3f',float('nan'),float('nan'),float('nan')))
                self.uc.reg_write(UC_X86_REG_RDI,self.query);self.uc.reg_write(UC_X86_REG_RSI,self.geometry)
                self.uc.reg_write(UC_X86_REG_R8,0)
                self.q(self.rsp+0x200,self.target);self.q(self.rsp+0x238,MODULE+0x7DED33)

    def pair(self, dead=False):
        self.q(self.ctl+0x58,self.paired);self.q(self.tc+0x58,self.enemy)
        self.q(self.ctl+0x5B0,0 if dead else self.target);self.q(self.tc+0x5B0,0 if dead else self.actor)
        self.q(self.ts+0x20,0 if dead else 1);self.put(self.temp,b'\x08' if dead else b'\x07')

    def run(self):
        before={reg:self.uc.reg_read(reg) for reg in GPRS+XMM}
        self.uc.emu_start(self.hook['target'],0,count=1000000)
        if self.stopped is None:raise AssertionError('Hook did not reach its original/accepted continuation')
        return before,{reg:self.uc.reg_read(reg) for reg in GPRS+XMM}
