"""Synthetic item records/native RET boundaries; these are not gameplay tests.

The native item factory, scheduled events and inventory commit are not run.
Only the generated public compatibility payloads execute under Unicorn.
"""
from copy import deepcopy
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import load_beta563_plan as load_plan, assemble
from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import (apply_dung_fan, ITEM_SPECS, SCHEDULE_HEX,
                              EVENT_GUARDS, HELPER_OFFSET, CARRIER_NAME, CHANGED_HOOKS)
import test_special_items_portable as old_items
import test_harakiri_portable as harakiri_tests
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

DEF = old_items.DEFINITION
OLD_SPECS = old_items.ITEM_SPECS
OLD_HELPER = old_items.HELPER_OFFSET


class DungFanMachine(old_items.ItemMachine):
    """Reuse the public item fixture with local, temporary definition tables."""
    def __init__(self, plan, item=44220, layout=b.LAYOUTS[0]):
        with patch.multiple(old_items, ITEM_SPECS=ITEM_SPECS,
                            SCHEDULE_HEX=SCHEDULE_HEX, EVENT_GUARDS=EVENT_GUARDS):
            super().__init__(plan, item, layout)
        self.definition_result = DEF
        self.mutate_on_call = None
        self.put32(b.CONTROLLER + 0x570, 0)
        self.events.clear()
        self.writes.clear()

    def trace(self, cpu, address, size, user):
        name = self.callbacks.get(address)
        if name == 'definition':
            rsp = cpu.reg_read(UC_X86_REG_RSP)
            if rsp % 16 != 8:
                raise AssertionError('Unaligned native definition lookup')
            if cpu.reg_read(UC_X86_REG_EDX) != self.get32(b.CONTROLLER + 0x548):
                raise AssertionError('Definition lookup does not match the request')
            if cpu.reg_read(UC_X86_REG_RCX) != old_items.ITEM_TABLE + 0x500:
                raise AssertionError('Wrong definition table')
            self.events.append(('definition', cpu.reg_read(UC_X86_REG_EDX)))
            cpu.mem_write(rsp + 8, b'\xA5' * 32)
            for reg in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8,
                        UC_X86_REG_R9, UC_X86_REG_R10, UC_X86_REG_R11, *b.XMMS[:6]):
                cpu.reg_write(reg, 0xDEADBEEF12345678)
            cpu.reg_write(UC_X86_REG_EFLAGS, 0x202)
            cpu.reg_write(UC_X86_REG_MXCSR, 0x1FC5)
            cpu.reg_write(UC_X86_REG_RAX, self.definition_result)
        else:
            super().trace(cpu, address, size, user)
        if name and self.mutate_on_call:
            self.mutate_on_call(self, name)


class DungFanPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = apply_harakiri(load_plan())
        cls.plan = apply_dung_fan(cls.base)

    def checked_entry(self, m, accepted, entry=HELPER_OFFSET):
        before = m.protected_snapshot()
        registers = {}
        def setup():
            registers.update({r: m.cpu.reg_read(r) for r in b.REGISTERS})
        m.invoke(m.code + entry, setup)
        registers[UC_X86_REG_RSP] = b.STACK
        self.assertEqual({r: m.cpu.reg_read(r) for r in b.REGISTERS}, registers)
        self.assertEqual(m.protected_snapshot(), before)
        self.assertEqual([e for e in m.events if e[0] == 'dispatch'],
                         [('dispatch', b.CONTROLLER, 172)] if accepted else [])
        self.assertTrue(all(0x20000000 <= at < 0x20010000 for _, at, _ in m.writes))

    def test_three_items_two_player_templates_three_layouts_preserve_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for row in ITEM_SPECS:
                    with self.subTest(layout=layout, template=template, item=row[0]):
                        m = DungFanMachine(self.plan, row[0], layout)
                        for at in (b.ACTOR, b.META, m.data + 4):
                            m.put32(at, template)
                        self.checked_entry(m, True)
                        self.assertEqual(m.events, [('definition', row[0]), ('lookup', 172),
                            ('lookup', row[7]), ('clip', 2, row[8]), ('clip', 6, row[8]),
                            ('dispatch', b.CONTROLLER, 172)])

    def test_request_cancel_dialog_owner_and_dead_actor_fail_closed(self):
        changes = ((b.CONTROLLER + 0x548, 999, 4), (b.CONTROLLER + 0x54C, 99, 4),
            (b.CONTROLLER + 0x550, 0, 4), (b.CONTROLLER + 0x550, 2, 4),
            (b.CONTROLLER + 0x554, 1, 1), (b.CONTROLLER + 0x555, 0, 1),
            (b.CONTROLLER + 0x555, 2, 1), (b.CONTROLLER + 0x556, 1, 1),
            (b.CONTROLLER + 0x557, 1, 1), (b.CONTROLLER + 0x558, 1, 8),
            (b.CONTROLLER + 0x570, 1, 1), (b.CONTROLLER + 0x728, 1, 8),
            (b.CONTROLLER + 0x720, 0, 8), (b.ACTOR + 0x88000, 0, 8),
            (b.ACTOR + 4, 0x20000, 4), (b.ACTOR + 0xEF0, 1, 4),
            (b.META + 0xC, 0, 4), (b.META, 0x58E5F, 4),
            (b.PROXY, b.ACTOR + 0x100, 8), (b.PROXY + 8, b.CONTROLLER + 0x100, 8),
            (b.CONTROLLER + 0x50, b.ACTOR + 0x100, 8),
            (b.COMP, b.ACTOR + 0x100, 8), (b.COMP + 0x108, b.ACTOR + 0x100, 8),
            (b.COMP + 0x20, 0, 8), (b.CURRENT, 1, 4),
            (b.CURRENT + 0x38, b.BANK, 8), (b.PARAM, 0, 4), (b.PARAM + 1, 8, 1))
        for row in ITEM_SPECS:
            for at, value, width in changes:
                with self.subTest(item=row[0], at=hex(at), value=value):
                    m = DungFanMachine(self.plan, row[0])
                    m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            for kind in ('native-owner', 'recorded-owner', 'epoch', 'template'):
                m = DungFanMachine(self.plan, row[0])
                if kind == 'native-owner':
                    m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                elif kind == 'recorded-owner': m.put64(m.data + 0x10, b.ACTOR + 0x100)
                elif kind == 'epoch': m.put32(m.data + 0x1C, 0)
                else: m.put32(m.data + 4, 0x58E5F)
                self.checked_entry(m, False)

    def test_all_item_definition_fields_are_exact_and_unknowns_reject(self):
        for row in ITEM_SPECS:
            for offset, width in ((0, 4), (4, 1), (5, 1), (0x104, 4), (0x10C, 4),
                                  (0x110, 4), (0x114, 4), (0x118, 4), (0x11C, 4)):
                with self.subTest(item=row[0], offset=hex(offset)):
                    m = DungFanMachine(self.plan, row[0])
                    raw = int.from_bytes(m.cpu.mem_read(DEF + offset, width), 'little')
                    m.cpu.mem_write(DEF + offset, (raw ^ 1).to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            m = DungFanMachine(self.plan, row[0]); m.definition_result = 0
            self.checked_entry(m, False)

    def test_native_action_schedule_descriptors_and_both_motion_resources_reject_corruption(self):
        for row in ITEM_SPECS:
            action = row[7]
            # Every scheduled reference byte, every checked descriptor field.
            for offset in range(0x60):
                m = DungFanMachine(self.plan, row[0])
                at = m.lookup_results[action] + 0xC0 + offset
                m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0] ^ 1]))
                self.checked_entry(m, False)
            for index, *_ in EVENT_GUARDS[action]:
                at = (old_items.GLOBAL_EVENTS + (index - 10000) * 0x80 if index >= 10000
                      else b.ACTOR + 0xA1000 + index * 0x80)
                for offset in (0x17, 0x18, 0x1C, 0x3F, 0x2A, 0x52):
                    m = DungFanMachine(self.plan, row[0])
                    m.cpu.mem_write(at + offset, bytes([m.cpu.mem_read(at + offset, 1)[0] ^ 1]))
                    self.checked_entry(m, False)
            for uid in (172, action):
                for bad in ('missing', 'id', 'owner', 'enabled', 'motion', 'params'):
                    m = DungFanMachine(self.plan, row[0]); record = m.lookup_results[uid]
                    if bad == 'missing': m.lookup_results[uid] = 0
                    elif bad == 'id': m.put32(record, uid + 1)
                    elif bad == 'owner': m.put64(record + 0x38, b.OWN_BANK)
                    elif bad == 'enabled': m.cpu.mem_write(record + 0x40, b'\0')
                    elif bad == 'motion': m.put32(record + 0xA0, 999)
                    else: m.put64(record + 0x20, 0)
                    self.checked_entry(m, False)
            for slot in (2, 6):
                for bad in ('resource', 'map', 'clip', 'negative', 'range'):
                    m = DungFanMachine(self.plan, row[0])
                    if bad == 'resource': m.put64(b.MOTION + 8 + slot * 8, 0)
                    elif bad == 'map': m.put64(b.RES[slot] + 0x480, 0)
                    elif bad == 'clip': m.put64(b.CLIPS[slot], 0)
                    else: m.motion_results[slot] = -1 if bad == 'negative' else 78
                    self.checked_entry(m, False)

    def test_owner_request_dialog_and_action_changes_during_lookup_reject(self):
        for kind in ('epoch', 'owner', 'request', 'cancel', 'dialog', 'death',
                     'role', 'idle', 'bank', 'motion-owner'):
            m = DungFanMachine(self.plan)
            def mutate(m, name):
                if name != 'clip' or m.events[-1][1] != 6: return
                if kind == 'epoch': m.put32(m.data + 0x1C, 12)
                elif kind == 'owner': m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                elif kind == 'request': m.put32(b.CONTROLLER + 0x548, 32016)
                elif kind == 'cancel': m.cpu.mem_write(b.CONTROLLER + 0x555, b'\0')
                elif kind == 'dialog': m.cpu.mem_write(b.CONTROLLER + 0x570, b'\1')
                elif kind == 'death': m.put64(b.COMP + 0x20, 0)
                elif kind == 'role': m.put32(b.META + 0xC, 0)
                elif kind == 'idle': m.put32(b.CURRENT, 1)
                elif kind == 'bank': m.put64(b.CONTROLLER + 0x80, b.OWN_BANK)
                else: m.put64(b.ACTOR + 0x38, b.MOTION + 0x100)
            m.mutate_on_call = mutate
            m.invoke(m.code + HELPER_OFFSET)
            self.assertFalse(any(e[0] == 'dispatch' for e in m.events), kind)

    def test_existing_six_items_and_harakiri_keep_previous_routes(self):
        for row in OLD_SPECS:
            self.checked_entry(old_items.ItemMachine(self.plan, row[0]), True, OLD_HELPER)
            self.checked_entry(old_items.ItemMachine(self.plan, row[0]), False)
        h = harakiri_tests.HarakiriTests()
        for layout in b.LAYOUTS:
            h.check(harakiri_tests.GateMachine(self.plan, layout), True)
        # Same preceding gate checks, including existing talismans.
        h.old, h.plan = self.base, self.plan
        h.test_existing_talismans_and_unrelated_categories_preserve_routing()

    def test_fan_input_suppression_requires_owned_common_action_and_exact_motion(self):
        for hook_name in ('HE_InputA', 'HE_InputB'):
            for owner, motion, suppressed in ((b.BANK, 150, True),
                                               (b.OWN_BANK, 150, False),
                                               (b.BANK, 151, False)):
                with self.subTest(hook=hook_name, owner=owner, motion=motion):
                    m = PortableMachine(self.plan)
                    m.put32(b.CURRENT, 1225); m.put64(b.CURRENT + 0x38, owner)
                    m.put32(b.PARAM + 0x20, motion)
                    for offset in (0xC, 0xE): m.cpu.mem_write(b.INPUT + offset, b'\1')
                    m.cpu.mem_write(m.data + 0x29, b'\1')
                    m.reset()
                    for reg, value in ((UC_X86_REG_RBX, b.CONTROLLER), (UC_X86_REG_RDI, b.INPUT),
                                       (UC_X86_REG_RDX, b.INPUT), (UC_X86_REG_R10, 0),
                                       (UC_X86_REG_RCX, 6)):
                        m.cpu.reg_write(reg, value)
                    hook = m.by_name[hook_name]
                    m.run(hook['target'], hook['site'] + hook['length'])
                    self.assertEqual(m.get32(m.data + 0x24), int(not suppressed))
                    self.assertEqual(m.cpu.reg_read(UC_X86_REG_RCX), 6 if suppressed else 11)

    def test_transform_pure_exact_four_payloads_sites_and_carrier_prefix_preserved(self):
        before = deepcopy(self.base)
        self.assertEqual(apply_dung_fan(self.base), self.plan)
        self.assertEqual(self.base, before)
        for layout in b.LAYOUTS:
            old, new = assemble(self.base, *layout), assemble(self.plan, *layout)
            self.assertEqual(tuple(a['name'] for a, c in zip(old, new) if a['payload'] != c['payload']), CHANGED_HOOKS)
            self.assertEqual(len(new), 82)
            for a, c in zip(old, new):
                for field in ('name', 'site', 'target', 'original', 'patched', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])
                if a['name'] == CARRIER_NAME:
                    self.assertEqual(c['payload'][:len(a['payload'])], a['payload'])
                    self.assertLessEqual(len(c['payload']), c['code_capacity'])
        for bad in (load_plan(), self.plan):
            with self.assertRaises(ValueError): apply_dung_fan(bad)


if __name__ == '__main__':
    unittest.main()
