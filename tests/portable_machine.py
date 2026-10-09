"""Synthetic Win64 CPU fixtures; no game files, snapshots or process access.

Only public generated payloads execute. Native call boundaries are explicit
RET stubs. Constructed records describe the public assembly's ABI contract;
they are not evidence of real native resource/event or gameplay execution.
"""
import struct
import test_latched_door_instances as b
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


class PortableMachine(b.DoorMachine):
    def __init__(self, plan, layout=b.LAYOUTS[0]):
        super().__init__(plan, layout)
        self.mapped_pages = {address & ~0xFFF for address in self.callbacks}
        self.mapped_pages.update((hook['site'] + hook['length']) & ~0xFFF for hook in self.hooks)
        self.mapped_pages.add((self.module + plan['targets']['player_slot']) & ~0xFFF)
        self.mapped_pages.add(self.stop & ~0xFFF)
        self.mapped_pages.add((self.module + plan['targets']['interaction_animated']) & ~0xFFF)
        self.cpu.mem_map(b.ACTOR + 0xC0000, 0x100000)
        self.put32(b.PARAM, 1)
        self.put32(b.CURRENT, 0)
        self.put64(b.CONTROLLER + 0x510, 0)
        self.put64(b.CONTROLLER + 0x528, 0)
        self.put64(b.CONTROLLER + 0x4F0, 0)
        self.put64(b.CONTROLLER + 0x508, 0)
        self.put32(b.MOTION + 0x48, 2)
        self.put32(b.MOTION + 0x50, 0)
        self.put32(b.COMP + 0x20, 10000)
        self.lookup_results = {}
        self.motion_results = {2: 0, 6: 0}
        for slot in (2, 6):
            self.put64(b.CLIPS[slot], b.ACTOR + 0x80000)
        self.events.clear()
        self.writes.clear()

    def get64(self, address):
        return struct.unpack('<Q', self.cpu.mem_read(address, 8))[0]

    def page(self, address):
        page = address & ~0xFFF
        if page not in self.mapped_pages:
            self.cpu.mem_map(page, 0x1000)
            self.mapped_pages.add(page)

    def invoke(self, address, setup=None):
        self.reset()
        self.cpu.reg_write(UC_X86_REG_RSP, b.STACK - 8)
        self.put64(b.STACK - 8, self.stop)
        if setup:
            setup()
        self.events.clear()
        self.writes.clear()
        self.run(address)
        return self.cpu.reg_read(UC_X86_REG_RAX)

    def protected_snapshot(self):
        return {address: bytes(self.cpu.mem_read(address, size)) for address, size in
                ((b.ACTOR, 0x1C0000), (b.INPUT, 0x4000), (self.data, 0x1000))}

