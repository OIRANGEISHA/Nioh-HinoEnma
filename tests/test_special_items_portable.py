"""Portable item ABI regressions with synthetic records and native RET stubs.

No native event engine, item factory, inventory commit or game resource runs.
These checks are separate from the private native CPU and user play checks.
"""
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import source_plan
from hinoenma_special_item_actions import ITEM_SPECS, SCHEDULE_HEX, EVENT_GUARDS, HELPER_OFFSET
from hinoenma_special_items import EFFECT_HELPER_OFFSET
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

DEFINITION, ITEM_OWNER, ITEM_TABLE = (b.ACTOR + x for x in (0x90000, 0x91000, 0x92000))
GLOBAL_HANDLE, GLOBAL_OWNER, GLOBAL_EVENTS = (b.ACTOR + x for x in (0xB0000, 0xB0100, 0xB1000))
GUARDIAN, SAVED, POOL = (b.ACTOR + x for x in (0x83000, 0x84000, 0x85000))


class ItemMachine(PortableMachine):
    def __init__(self, plan, item, layout=b.LAYOUTS[0]):
        super().__init__(plan, layout)
        row = next(x for x in ITEM_SPECS if x[0] == item)
        ident, kind, subtype, category, flags, effects, spawn, action, motion, _ = row
        self.action, self.item = action, item
        self.put64(b.CONTROLLER + 0x548, item)
        self.put32(b.CONTROLLER + 0x54C, category)
        self.put32(b.CONTROLLER + 0x550, 1)
        self.put32(b.CONTROLLER + 0x554, 0x100)
        self.put64(b.CONTROLLER + 0x558, 0)
        self.put64(b.CONTROLLER + 0x728, 0)
        head = b.ACTOR + 0x88000
        self.put64(b.CONTROLLER + 0x720, head)
        self.put64(head, head)
        self.put64(head + 8, head)
        self.put32(DEFINITION, ident)
        self.cpu.mem_write(DEFINITION + 4, struct.pack('<H', kind | (subtype << 8)))
        for off, value in ((0x104, flags), (0x10C, category), (0x11C, spawn),
                           *((0x110 + i * 4, value) for i, value in enumerate(effects))):
            self.put32(DEFINITION + off, value)
        assets = self.module + plan['targets']['item_assets']
        self.page(assets)
        self.put64(assets, ITEM_OWNER)
        self.put64(ITEM_OWNER + 0x20, ITEM_TABLE)
        self.put64(ITEM_TABLE + 0x428, ITEM_TABLE + 0x500)
        self.put64(assets - 0x1E0, GLOBAL_HANDLE)
        self.put64(GLOBAL_HANDLE, GLOBAL_OWNER)
        self.put64(GLOBAL_OWNER + 0x468, GLOBAL_EVENTS)
        self.put64(GLOBAL_OWNER + 0x470, GLOBAL_EVENTS + 0x100)
        lookup = self.module + plan['targets']['item_lookup']
        self.page(lookup)
        self.cpu.mem_write(lookup, b'\xC3')
        self.callbacks[lookup] = 'definition'
        for index, (uid, mid) in enumerate(((172, -1), (action, motion))):
            record = b.ACTOR + 0x30000 + index * 0x200
            self.lookup_results[uid] = record
            self.put64(b.VECTOR + index * 8, record)
            self.put32(record, uid)
            self.put64(record + 0x20, record + 0x80)
            self.put64(record + 0x38, b.BANK)
            self.cpu.mem_write(record + 0x40, b'\x01')
            self.put32(record + 0xA0, mid)
            self.put32(record + 0xB4, -1)
            if uid == action:
                self.cpu.mem_write(record + 0xC0, bytes.fromhex(SCHEDULE_HEX[action]))
        self.put64(b.BANK + 0x80, b.EVENTS)
        self.cpu.mem_write(b.BANK + 0x88, struct.pack('<H', 183))
        for index, opcode, template, bone, commit, channel, word52 in EVENT_GUARDS[action]:
            at = GLOBAL_EVENTS + (index - 10000) * 0x80 if index >= 10000 else b.ACTOR + 0xA1000 + index * 0x80
            if index < 10000:
                self.put64(b.EVENTS + index * 8, at)
            self.cpu.mem_write(at + 0x17, bytes([opcode & 255]))
            self.put32(at + 0x18, template)
            self.cpu.mem_write(at + 0x1C, struct.pack('<H', bone & 0xFFFF))
            self.cpu.mem_write(at + 0x3F, bytes([commit]))
            self.cpu.mem_write(at + 0x2A, bytes([channel]))
            self.cpu.mem_write(at + 0x52, struct.pack('<H', word52 & 0xFFFF))
        self.events.clear()
        self.writes.clear()

    def trace(self, cpu, address, size, user):
        if self.callbacks.get(address) == 'definition':
            if cpu.reg_read(UC_X86_REG_EDX) != self.item:
                raise AssertionError('Wrong item definition lookup')
            if cpu.reg_read(UC_X86_REG_RSP) % 16 != 8:
                raise AssertionError('Unaligned Win64 definition stub')
            self.events.append(('definition', self.item))
            cpu.reg_write(UC_X86_REG_RAX, DEFINITION)
            return
        super().trace(cpu, address, size, user)


class SpecialItemsPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = source_plan(json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8')))

    def checked_entry(self, m, accepted):
        before = m.protected_snapshot()
        m.invoke(m.code + HELPER_OFFSET)
        self.assertEqual(m.protected_snapshot(), before)
        self.assertEqual([e for e in m.events if e[0] == 'dispatch'],
                         [('dispatch', b.CONTROLLER, 172)] if accepted else [])

    def test_six_owned_item_actions_choose_common172_at_three_layouts(self):
        for layout in b.LAYOUTS:
            for row in ITEM_SPECS:
                with self.subTest(layout=layout, item=row[0]):
                    self.checked_entry(ItemMachine(self.plan, row[0], layout), True)

    def test_definition_and_player_ownership_reject_before_dispatch(self):
        mutations = ((DEFINITION, 999, 4), (DEFINITION + 4, 2, 2),
                     (DEFINITION + 0x110, 1, 4), (b.ACTOR + 4, 0x20000, 4),
                     (b.COMP + 0x20, 0, 8), (b.CONTROLLER + 0x550, 2, 4),
                     (b.PROXY + 8, b.CONTROLLER + 0x100, 8))
        for address, value, width in mutations:
            m = ItemMachine(self.plan, 7739)
            m.cpu.mem_write(address, value.to_bytes(width, 'little'))
            self.checked_entry(m, False)

    def test_event_schedule_and_exact_clip_guards(self):
        for mutation in ('schedule', 'descriptor', 'missing-slot2', 'missing-slot6', 'lookup'):
            m = ItemMachine(self.plan, 7739)
            if mutation == 'schedule':
                m.put32(m.lookup_results[982] + 0xC0, 0)
            elif mutation == 'descriptor':
                m.cpu.mem_write(b.ACTOR + 0xA1000 + 17 * 0x80 + 0x17, b'\xFF')
            elif mutation == 'lookup':
                m.lookup_results[172] = 0
            else:
                slot = 2 if mutation.endswith('2') else 6
                m.put64(b.CLIPS[slot], 0)
            self.checked_entry(m, False)

    def effect_machine(self, item):
        m = PortableMachine(self.plan)
        definition = DEFINITION
        effect_id, effect_type = (60833, 13) if item == 46858 else (5779, 30)
        m.put32(b.CONTROLLER + 0x548, item)
        m.put32(b.CONTROLLER + 0x54C, 1)
        m.put32(b.CONTROLLER + 0x550, 1)
        m.put32(b.CONTROLLER + 0x554, 0x100)
        for off, value in ((0, item), (4, 1), (0x104, 1), (0x10C, 1), (0x114, effect_id)):
            m.put32(definition + off, value)
        saved_slot = m.module + self.plan['targets']['special_item_saved_manager']
        pool_slot = m.module + self.plan['targets']['special_item_guardian_pool_slot']
        m.page(saved_slot); m.page(pool_slot)
        m.put64(saved_slot, SAVED); m.cpu.mem_write(SAVED + 0x74, b'\x01')
        m.put64(pool_slot, POOL - 0x1D0)
        m.put64(b.ACTOR + 0x2C0, GUARDIAN)
        m.put64(b.ACTOR + 0x2C8, POOL)
        m.put64(GUARDIAN, m.module + self.plan['targets']['native_guardian_vtable'])
        m.put64(GUARDIAN + 0x10, b.ACTOR)
        m.effect_type, m.effect_id = effect_type, effect_id
        return m

    def checked_effect(self, m, accepted):
        before = m.protected_snapshot()
        def setup():
            m.cpu.reg_write(UC_X86_REG_RSI, DEFINITION)
            m.cpu.reg_write(UC_X86_REG_RCX, m.effect_type)
            m.cpu.reg_write(UC_X86_REG_RDX, m.effect_id)
        self.assertEqual(m.invoke(m.code + EFFECT_HELPER_OFFSET, setup), int(accepted))
        self.assertEqual(m.protected_snapshot(), before)

    def test_branch_and_lost_guardian_candle_eligibility_are_read_only(self):
        for item in (46858, 33287):
            self.checked_effect(self.effect_machine(item), True)

    def test_candle_rejects_present_guardian_or_foreign_component(self):
        for address, value, width in ((SAVED + 0x74, 0, 1), (GUARDIAN + 0x10, b.ACTOR + 0x1000, 8),
                                      (b.ACTOR + 0x2C8, POOL + 16, 8), (DEFINITION + 0x114, 5780, 4)):
            m = self.effect_machine(33287)
            m.cpu.mem_write(address, value.to_bytes(width, 'little'))
            self.checked_effect(m, False)


if __name__ == '__main__':
    unittest.main()
