"""Portable CPU checks for local 0.51's object-kind latch guard.

Only public generated payloads execute. Action lookup, motion lookup and the
native action setter are explicit Win64 call stubs, not game-code snapshots.
The native queue, query115, door scripts and rendered animation do not execute.
These eight regressions are separate from the private native-CodeImage suite.
"""
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
from build_profile import assemble, source_plan_v051 as source_plan, source_plan_v050
from hinoenma_latched_door_instances import apply_latched_door_instances, OLD_BYTES, NEW_BYTES
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *

LAYOUTS = ((0x140000000, 0x144000000), (0x7FF600000000, 0x7FF604000000),
           (0x180000000, 0x176000000))
STACK = 0x20008000
ACTOR, INPUT, CONTROLLER, METADATA = 0x30000000, 0x32000000, 0x32001000, 0x32002000
COMP, META, MOTION, PROXY, CURRENT = (ACTOR+x for x in (0x4000,0x10000,0x11000,0x12000,0x13000))
PARAM = CURRENT+0x100
OWN_BANK, BANK, VECTOR = ACTOR+0x21000, ACTOR+0x22000, ACTOR+0x25000
ENTRY170, LATCH_RECORD, EVENTS = ACTOR+0x50000, ACTOR+0x50100, ACTOR+0xA0000
RES = {2: ACTOR+0x60000, 6: ACTOR+0x68000}
MAPS = {2: ACTOR+0x70000, 6: ACTOR+0x71000}
CLIPS = {2: ACTOR+0x74000, 6: ACTOR+0x75000}
GPRS = (UC_X86_REG_RAX, UC_X86_REG_RBX, UC_X86_REG_RCX, UC_X86_REG_RDX,
        UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_RBP, UC_X86_REG_RSP,
        UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_R10, UC_X86_REG_R11,
        UC_X86_REG_R12, UC_X86_REG_R13, UC_X86_REG_R14, UC_X86_REG_R15)
XMMS = tuple(globals()["UC_X86_REG_XMM"+str(i)] for i in range(16))
REGISTERS = GPRS+XMMS+(UC_X86_REG_EFLAGS, UC_X86_REG_MXCSR)
PREFLIGHT = [("lookup",170),("lookup",157),("clip",2,223),("clip",6,223)]
_ASSEMBLED = {}


class DoorMachine:
    def __init__(self, plan, layout=LAYOUTS[0], instance=100):
        self.plan = plan
        self.module, self.code = layout
        self.data = self.code+plan["data_offset"]
        key = (id(plan), layout)
        if key not in _ASSEMBLED:
            _ASSEMBLED[key] = assemble(plan, *layout)
        self.hooks = _ASSEMBLED[key]
        self.by_name = {hook["name"]:hook for hook in self.hooks}
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_64)
        self.cpu.mem_map(self.code, plan["allocation_size"])
        self.cpu.mem_map(0x20000000, 0x10000)
        self.cpu.mem_map(ACTOR, 0xC0000)
        self.cpu.mem_map(INPUT, 0x4000)
        self.stop = self.module+0x1100800
        self.callbacks = {
            self.module+plan["targets"]["signpost_action_lookup"]:"lookup",
            self.module+plan["targets"]["native_ladder_motion_index"]:"clip",
            self.module+plan["targets"]["native_ladder_set_action"]:"dispatch",
        }
        pages = {at & ~0xFFF for at in self.callbacks}
        pages.update((self.stop & ~0xFFF, (self.module+plan["targets"]["player_slot"]) & ~0xFFF))
        pages.update((hook["site"]+hook["length"]) & ~0xFFF for hook in self.hooks)
        pages.add((self.module+plan["targets"]["interaction_animated"]) & ~0xFFF)
        for page in pages:
            self.cpu.mem_map(page,0x1000)
        for hook in self.hooks:
            self.cpu.mem_write(hook["target"],hook["payload"])
        for address in self.callbacks:
            self.cpu.mem_write(address,b"\xC3")
        self.events, self.writes = [], []
        self.lookup_results = {170:ENTRY170,157:LATCH_RECORD}
        self.motion_results = {2:77,6:77}
        self.put32(self.data+4,0x58E5E)
        self.put64(self.data+0x10,ACTOR)
        self.put32(self.data+0x1C,11)
        self.cpu.mem_write(self.data+0x2A,b"\x02")
        self.put64(self.module+plan["targets"]["player_slot"],ACTOR)
        self.put32(ACTOR,0x58E5E)
        self.put32(ACTOR+4,0x10000)
        self.put64(ACTOR+0xE90,META)
        self.put32(META,0x58E5E)
        self.put32(META+0xC,1)
        self.put64(ACTOR+0x240,COMP)
        self.put64(COMP,ACTOR)
        self.put64(COMP+0x108,ACTOR)
        self.put64(COMP+0x20,0x100000000)
        self.put64(ACTOR+0x230,PROXY)
        self.put64(PROXY,ACTOR)
        self.put64(PROXY+8,CONTROLLER)
        self.put64(CONTROLLER+0x50,ACTOR)
        self.put32(INPUT,15)
        self.put32(INPUT+4,(instance << 16)|2)
        self.put64(INPUT+0x320,ACTOR)
        self.put64(METADATA,INPUT)
        self.cpu.mem_write(METADATA+8,b"\x01\x01\x00")
        self.put32(METADATA+0x48,16)
        self.put64(CONTROLLER+0x510,INPUT)
        self.put64(CONTROLLER+0x528,METADATA)
        self.put64(CONTROLLER+0x530,0xFFFFFFFFFFFFFFFF)
        self.put64(CONTROLLER+0x58,CURRENT)
        self.put64(CURRENT+0x20,PARAM)
        self.put64(CURRENT+0x38,OWN_BANK)
        self.put32(PARAM,1)
        self.put64(CONTROLLER+0x78,OWN_BANK)
        self.put64(CONTROLLER+0x80,BANK)
        self.put32(BANK+0x130,2)
        self.put64(BANK+0x128,VECTOR)
        for index,(at,action,motion) in enumerate(((ENTRY170,170,-1),(LATCH_RECORD,157,223))):
            self.put64(VECTOR+index*8,at)
            self.put32(at,action)
            self.put64(at+0x20,at+0x80)
            self.put64(at+0x38,BANK)
            self.cpu.mem_write(at+0x40,b"\x01")
            self.put32(at+0xA0,motion)
            self.put32(at+0xB4,-1)
        self.put32(LATCH_RECORD+0xC0,0)
        self.put32(LATCH_RECORD+0xC4,0x4BFFFF)
        self.put32(LATCH_RECORD+0xC8,0xFFFF0000)
        self.put64(BANK+0x80,EVENTS)
        self.cpu.mem_write(BANK+0x88,struct.pack("<H",183))
        self.put64(EVENTS,ACTOR+0xA1000)
        self.put64(EVENTS+75*8,ACTOR+0xA1100)
        self.put64(ACTOR+0x38,MOTION)
        for slot in (2,6):
            self.put64(MOTION+8+slot*8,RES[slot])
            self.put64(RES[slot]+0x480,MAPS[slot])
            self.put32(MAPS[slot]+8,3)
            self.put64(MAPS[slot]+0x10,ACTOR+0x72000+slot*0x100)
            self.put64(RES[slot]+0x468,CLIPS[slot])
            self.put64(RES[slot]+0x470,CLIPS[slot]+78*8)
            self.put64(CLIPS[slot]+77*8,ACTOR+0x80000)
        self.cpu.hook_add(UC_HOOK_CODE,self.trace)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE,self.track_write)
        self.reset()

    def put32(self,address,value):
        self.cpu.mem_write(address,struct.pack("<I",value & 0xFFFFFFFF))

    def put64(self,address,value):
        self.cpu.mem_write(address,struct.pack("<Q",value & 0xFFFFFFFFFFFFFFFF))

    def get32(self,address):
        return struct.unpack("<I",self.cpu.mem_read(address,4))[0]

    def reset(self):
        for i,register in enumerate(GPRS):
            self.cpu.reg_write(register,0xBEEF000000+i)
        for i,register in enumerate(XMMS):
            self.cpu.reg_write(register,int.from_bytes(bytes([i+17])*16,"little"))
        for register,value in ((UC_X86_REG_RSP,STACK),(UC_X86_REG_RDI,CONTROLLER),
                               (UC_X86_REG_RAX,METADATA),(UC_X86_REG_R8,INPUT)):
            self.cpu.reg_write(register,value)
        self.cpu.reg_write(UC_X86_REG_EFLAGS,0xA97)
        self.cpu.reg_write(UC_X86_REG_MXCSR,0x5FA5)

    def snapshot(self):
        return {at:bytes(self.cpu.mem_read(at,size)) for at,size in
                ((ACTOR,0xC0000),(INPUT,0x4000),(self.data,0x1000),(self.code+0x13000,0x1000))}

    def trace(self,cpu,address,size,user):
        if address == self.stop:
            self.reached = True
            cpu.emu_stop()
            return
        name = self.callbacks.get(address)
        if name is None:
            return
        rsp = cpu.reg_read(UC_X86_REG_RSP)
        if rsp % 16 != 8:
            raise AssertionError("Native call stub does not have aligned Win64 stack")
        cpu.mem_write(rsp+8,b"\xCC"*32)
        if name == "lookup":
            action = cpu.reg_read(UC_X86_REG_EDX)
            self.events.append((name,action))
            result = self.lookup_results.get(action,0)
        elif name == "clip":
            pointer = cpu.reg_read(UC_X86_REG_RCX)
            slot = next(slot for slot,at in MAPS.items() if at == pointer)
            action = cpu.reg_read(UC_X86_REG_EDX)
            if cpu.reg_read(UC_X86_REG_R8D) != 0xFFFFFFFF:
                raise AssertionError("Unexpected motion lookup selector")
            self.events.append((name,slot,action))
            result = self.motion_results[slot]
        else:
            args = (cpu.reg_read(UC_X86_REG_RCX),cpu.reg_read(UC_X86_REG_EDX))
            self.events.append((name,*args))
            result = 0
        for register in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,
                         UC_X86_REG_R10,UC_X86_REG_R11):
            cpu.reg_write(register,0xDEADBEEF12345678)
        for register in XMMS[:6]:
            cpu.reg_write(register,0xDEADBEEF0123456789ABCDEF)
        cpu.reg_write(UC_X86_REG_EFLAGS,0x202)
        cpu.reg_write(UC_X86_REG_MXCSR,0x1FC5)
        cpu.reg_write(UC_X86_REG_RAX,result & 0xFFFFFFFFFFFFFFFF)

    def track_write(self,cpu,access,address,size,value,user):
        self.writes.append((cpu.reg_read(UC_X86_REG_RIP),address,size))

    def run(self,address,stop=None):
        self.reached = False
        self.stop = stop or self.module+0x1100800
        self.cpu.emu_start(address,0,count=8000)
        if not self.reached:
            raise AssertionError("Payload did not reach the expected continuation")


class LatchedDoorInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen = json.loads((ROOT/"profiles/steam-1.24.8.json").read_text("utf-8"))
        cls.previous = source_plan_v050(frozen)
        cls.plan = source_plan(frozen)

    def machine(self,**options):
        return DoorMachine(self.previous if options.pop("previous",False) else self.plan,**options)

    def helper(self,m,queued=False,ready=True):
        m.reset()
        m.cpu.reg_write(UC_X86_REG_RSP,STACK-8)
        m.put64(STACK-8,m.module+0x1100800)
        before = m.snapshot()
        registers = {r:m.cpu.reg_read(r) for r in REGISTERS}
        m.run(m.code+(0x10310 if queued else 0x10300))
        registers[UC_X86_REG_RSP] = STACK
        if not queued:
            registers[UC_X86_REG_EFLAGS] = (registers[UC_X86_REG_EFLAGS]&~1)|int(ready)
        self.assertEqual({r:m.cpu.reg_read(r) for r in REGISTERS},registers)
        self.assertEqual(m.snapshot(),before)
        self.assertTrue(all(0x20000000 <= address < 0x20010000 for _,address,_ in m.writes))
        self.assertEqual(any(e[0] == "dispatch" for e in m.events),queued and ready)

    def test_pure_transform_is_repeatable_and_rejects_changed_frozen_inputs(self):
        saved = deepcopy(self.previous)
        self.assertEqual(apply_latched_door_instances(self.previous),self.plan)
        self.assertEqual(self.previous,saved)
        self.assertEqual(self.plan["tool_version"],"0.51")
        for candidate in (self.plan,dict(self.previous,tool_version="0.49")):
            with self.assertRaises(ValueError):
                apply_latched_door_instances(candidate)
        for field,value in (("code_offset",0x10100),("rva",0x8B1874),("code_capacity",0x400)):
            changed = deepcopy(self.previous)
            changed["hooks"][45][field] = value
            with self.assertRaises(ValueError):
                apply_latched_door_instances(changed)
        changed = deepcopy(self.previous)
        changed["hooks"][45]["asm"] = changed["hooks"][45]["asm"].replace(
            "cmp dword ptr [r9+4], 0x10002\n","cmp dword ptr [r9+4], 0x20002\n",1)
        with self.assertRaises(ValueError):
            apply_latched_door_instances(changed)

    def test_exact_eight_byte_change_preserves_49_sites_other_48_payloads_and_entries(self):
        for layout in LAYOUTS:
            old,new = assemble(self.previous,*layout),assemble(self.plan,*layout)
            self.assertEqual((len(old),len(new)),(49,49))
            self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a["payload"] != b["payload"]],[45])
            for i,(a,b) in enumerate(zip(old,new)):
                for key in ("name","rva","length","site","target","patched","original","code_offset","code_capacity"):
                    self.assertEqual(a.get(key),b.get(key))
                self.assertEqual(len(a["payload"]),len(b["payload"]))
                if i != 45:
                    self.assertEqual(a["payload"],b["payload"])
            before,after = old[45]["payload"],new[45]["payload"]
            self.assertEqual(before.count(OLD_BYTES),1)
            self.assertEqual(after,before.replace(OLD_BYTES,NEW_BYTES,1))
            self.assertEqual(after[:0x320],before[:0x320])
            self.assertEqual(after[0x700:],before[0x700:])
            m = self.machine(layout=layout)
            for offset,expected in ((0x10300,b"\x6A\x00"),(0x10310,b"\x6A\x01"),
                                    (0x10320,b"\x9C"),(0x10700,b"\x48\x83\xEC\x38")):
                self.assertEqual(bytes(m.cpu.mem_read(m.code+offset,len(expected))),expected)
            self.helper(m,queued=True)
        self.assertEqual((self.plan["data_offset"],self.plan["allocation_size"]),(0xF000,0x14000))

    def test_old_instance100_rejection_and_immediate_fallback_are_reproduced(self):
        for queued in (False,True):
            m = self.machine(previous=True)
            self.helper(m,queued=queued,ready=False)
            self.assertEqual(m.events,[])
        old = self.machine(previous=True)
        old.run(old.by_name["HE_Interaction"]["target"],old.module+0x751160)
        self.assertEqual((old.get32(old.data+0x34),old.get32(old.data+0x38),old.get32(old.data+0x3C)),(1,16,15))
        new = self.machine()
        self.helper(new,queued=True)
        self.assertEqual(new.events,PREFLIGHT+[("dispatch",CONTROLLER,170)])

    def test_all_instance_words_keep_owner_role_resource_guards_and_full_abi(self):
        for instance in (0,1,36,100,0x8000,0xFFFF):
            for template in (0x58E5E,0x51BE1):
                for owner in (0,ACTOR):
                    for queued in (False,True):
                        with self.subTest(instance=instance,template=template,owner=owner,queued=queued):
                            m = self.machine(instance=instance)
                            for at in (ACTOR,META,m.data+4):
                                m.put32(at,template)
                            m.put64(INPUT+0x320,owner)
                            self.helper(m,queued=queued)
                            self.assertEqual(m.events[:4],PREFLIGHT)
                            self.assertEqual(m.get32(INPUT+4),(instance<<16)|2)

    def test_public_generic_and_queued_entries_dispatch_once_across_three_layouts(self):
        for layout in LAYOUTS:
            for instance in (1,36,100,0xFFFF):
                m = self.machine(layout=layout,instance=instance)
                m.reset()
                before = m.snapshot()
                m.run(m.by_name["HE_Interaction"]["target"],m.module+self.plan["targets"]["interaction_animated"])
                self.assertEqual(m.events,PREFLIGHT)
                self.assertEqual(m.snapshot(),before)
                self.assertEqual(m.get32(m.data+0x34),0)
                # Accepted queue references are an explicit fixture, not native queue execution.
                m.reset()
                registers = {r:m.cpu.reg_read(r) for r in REGISTERS}
                m.run(m.by_name["HE_QueuedDoor"]["target"],m.module+0x7512AA)
                self.assertEqual({r:m.cpu.reg_read(r) for r in REGISTERS},registers)
                self.assertEqual(m.events[-5:],PREFLIGHT+[("dispatch",CONTROLLER,170)])
                self.assertEqual(sum(e[0] == "dispatch" for e in m.events),1)
                self.assertEqual(m.snapshot(),before)

    def test_wrong_kind_id_request_owner_started_and_player_fail_closed(self):
        changes = [(INPUT+4,(100<<16)|kind,4) for kind in (0,1,3,0xFFFF)]
        changes += [(INPUT,ident,4) for ident in (2,14,16)]
        changes += [(METADATA+0x48,request,4) for request in (15,17,22,46)]
        changes += [(INPUT+0x320,ACTOR+0x1000,8),(METADATA,INPUT+0x100,8),(METADATA+0x4C,1,8),
                    (CURRENT,157,4),(ACTOR+4,0x640000,4),(ACTOR+0xEF0,1,4),
                    (PROXY+8,CONTROLLER+0x100,8),(CONTROLLER+0x50,ACTOR+0x1000,8)]
        for address,value,width in changes:
            for queued in (False,True):
                m = self.machine()
                m.cpu.mem_write(address,value.to_bytes(width,"little"))
                self.helper(m,queued=queued,ready=False)
                self.assertFalse(any(e[0] == "dispatch" for e in m.events))
        for offset,value in ((8,0),(9,0),(10,1)):
            m = self.machine()
            m.cpu.mem_write(METADATA+offset,bytes([value]))
            self.helper(m,ready=False)

    def test_missing_owned_records_events_and_clips_preserve_old_fallback(self):
        changes = [(ENTRY170+0x40,0,1),(LATCH_RECORD+0x40,0,1),(LATCH_RECORD+0x38,OWN_BANK,8),
                   (LATCH_RECORD+0x20,0,8),(EVENTS+75*8,0,8)]
        changes += [(CLIPS[slot]+77*8,0,8) for slot in (2,6)]
        for address,value,width in changes:
            for queued in (False,True):
                m = self.machine()
                m.cpu.mem_write(address,value.to_bytes(width,"little"))
                self.helper(m,queued=queued,ready=False)
        for slot in (2,6):
            old,new = self.machine(previous=True),self.machine()
            for m in (old,new):
                m.put64(CLIPS[slot]+77*8,0)
                m.run(m.by_name["HE_Interaction"]["target"],m.module+0x751160)
            self.assertEqual(new.snapshot(),old.snapshot())
            self.assertEqual({r:new.cpu.reg_read(r) for r in REGISTERS},
                             {r:old.cpu.reg_read(r) for r in REGISTERS})

    def test_stubbed_lookup_motion_and_dispatch_contracts_reject_bad_resources(self):
        for action in (170,157):
            for queued in (False,True):
                m = self.machine()
                m.lookup_results[action] = 0
                self.helper(m,queued=queued,ready=False)
        for slot in (2,6):
            for result in (-1,0x10000,78):
                for queued in (False,True):
                    m = self.machine()
                    m.motion_results[slot] = result
                    self.helper(m,queued=queued,ready=False)
        for request in (0,15,17,39):
            for instance in (0,1,100,0xFFFF):
                m = self.machine(instance=instance)
                m.put32(METADATA+0x48,request)
                self.helper(m,queued=True,ready=False)


if __name__ == "__main__":
    unittest.main()
