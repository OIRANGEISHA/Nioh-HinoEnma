"""Synthetic Arrowproof/Sloth records and explicit Win64 native call stubs.

These verify only the public compatibility payload, not the native cast
state machine, fast-cast branches, item stock, projectiles or gameplay.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import load_beta563_plan as load_plan, assemble
from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import apply_dung_fan
from hinoenma_four_throwables import apply_four_throwables, ALL_ITEM_SPECS as PREVIOUS_ITEMS
from hinoenma_arrow_sloth import (apply_arrow_sloth, ITEM_SPECS, ALL_ITEM_SPECS,
                                 SCHEDULE_HEX, EVENT_GUARDS, HELPER_OFFSET,
                                 CARRIER_NAME, CHANGED_HOOKS)
import test_dung_fan_portable as dung_tests
import test_harakiri_portable as harakiri_tests
import test_special_items_portable as special_tests
from portable_machine import PortableMachine, b
from unicorn.x86_const import *


class ArrowSlothMachine(dung_tests.DungFanMachine):
    def __init__(self, plan, item, layout=b.LAYOUTS[0]):
        with patch.multiple(dung_tests, ITEM_SPECS=ALL_ITEM_SPECS,
                            SCHEDULE_HEX=SCHEDULE_HEX, EVENT_GUARDS=EVENT_GUARDS):
            super().__init__(plan, item, layout)


class ArrowSlothPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = apply_four_throwables(apply_dung_fan(apply_harakiri(load_plan())))
        cls.plan = apply_arrow_sloth(cls.base)

    checked_entry = dung_tests.DungFanPortableTests.checked_entry

    def test_both_items_templates_three_layouts_dispatch172_with_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for row in ITEM_SPECS:
                    with self.subTest(layout=layout, template=template, item=row[0]):
                        m = ArrowSlothMachine(self.plan, row[0], layout)
                        for at in (b.ACTOR, b.META, m.data + 4):
                            m.put32(at, template)
                        self.checked_entry(m, True)
                        self.assertEqual(m.events, [('definition', row[0]), ('lookup', 172),
                            ('lookup', row[7]), ('clip', 2, row[8]), ('clip', 6, row[8]),
                            ('dispatch', b.CONTROLLER, 172)])

    def test_exact_kind_subtype_and_all_definition_fields_required(self):
        for row in ITEM_SPECS:
            for offset, width in ((0, 4), (4, 1), (5, 1), (0x104, 4), (0x10C, 4),
                                  (0x110, 4), (0x114, 4), (0x118, 4), (0x11C, 4)):
                with self.subTest(item=row[0], offset=hex(offset)):
                    m = ArrowSlothMachine(self.plan, row[0])
                    at = dung_tests.DEF + offset
                    value = int.from_bytes(m.cpu.mem_read(at, width), 'little') ^ 1
                    m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            for kind in (0, 1, 2, 3):
                if kind == row[1]: continue
                m = ArrowSlothMachine(self.plan, row[0])
                m.cpu.mem_write(dung_tests.DEF + 4, bytes([kind]))
                self.checked_entry(m, False)
            m = ArrowSlothMachine(self.plan, row[0]); m.definition_result = 0
            self.checked_entry(m, False)
        self.assertEqual(tuple(row[1:4] for row in ITEM_SPECS), ((1, 0, 7), (2, 15, 9)))

    def test_request_owner_cancellation_and_dead_actor_fail_closed(self):
        changes = ((b.CONTROLLER + 0x548, 999, 4), (b.CONTROLLER + 0x54C, 0, 4),
            (b.CONTROLLER + 0x550, 2, 4), (b.CONTROLLER + 0x554, 1, 1),
            (b.CONTROLLER + 0x555, 0, 1), (b.CONTROLLER + 0x556, 1, 1),
            (b.CONTROLLER + 0x557, 1, 1), (b.CONTROLLER + 0x558, 1, 8),
            (b.CONTROLLER + 0x570, 1, 1), (b.CONTROLLER + 0x728, 1, 8),
            (b.ACTOR + 4, 0x20000, 4), (b.ACTOR + 0xEF0, 1, 4),
            (b.META + 0xC, 0, 4), (b.PROXY + 8, b.CONTROLLER + 0x100, 8),
            (b.COMP + 0x108, b.ACTOR + 0x100, 8), (b.COMP + 0x20, 0, 8),
            (b.CURRENT, 1, 4), (b.CURRENT + 0x38, b.BANK, 8))
        for row in ITEM_SPECS:
            for at, value, width in changes:
                m = ArrowSlothMachine(self.plan, row[0])
                m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                self.checked_entry(m, False)

    def test_each_schedule_descriptor_and_both_motion_slots_checked(self):
        for row in ITEM_SPECS:
            action = row[7]
            for offset in range(0x60):
                m = ArrowSlothMachine(self.plan, row[0])
                at = m.lookup_results[action] + 0xC0 + offset
                m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0] ^ 1]))
                self.checked_entry(m, False)
            for index, *_ in EVENT_GUARDS[action]:
                at = (special_tests.GLOBAL_EVENTS + (index - 10000) * 0x80 if index >= 10000
                      else b.ACTOR + 0xA1000 + index * 0x80)
                for offset in (0x17, 0x18, 0x1C, 0x3F, 0x2A, 0x52):
                    m = ArrowSlothMachine(self.plan, row[0])
                    m.cpu.mem_write(at + offset, bytes([m.cpu.mem_read(at + offset, 1)[0] ^ 1]))
                    self.checked_entry(m, False)
            for uid in (172, action):
                for bad in ('missing', 'owner', 'disabled', 'motion'):
                    m = ArrowSlothMachine(self.plan, row[0]); at = m.lookup_results[uid]
                    if bad == 'missing': m.lookup_results[uid] = 0
                    elif bad == 'owner': m.put64(at + 0x38, b.OWN_BANK)
                    elif bad == 'disabled': m.cpu.mem_write(at + 0x40, b'\0')
                    else: m.put32(at + 0xA0, 999)
                    self.checked_entry(m, False)
            for slot in (2, 6):
                for bad in ('resource', 'map', 'clip', 'negative', 'range'):
                    m = ArrowSlothMachine(self.plan, row[0])
                    if bad == 'resource': m.put64(b.MOTION + 8 + slot * 8, 0)
                    elif bad == 'map': m.put64(b.RES[slot] + 0x480, 0)
                    elif bad == 'clip': m.put64(b.CLIPS[slot], 0)
                    else: m.motion_results[slot] = -1 if bad == 'negative' else 78
                    self.checked_entry(m, False)

    def test_after_native_lookup_owner_request_and_dialog_revalidated(self):
        for row in ITEM_SPECS:
            for kind in ('owner', 'epoch', 'request', 'cancel', 'dialog', 'death', 'idle', 'bank'):
                with self.subTest(item=row[0], change=kind):
                    m = ArrowSlothMachine(self.plan, row[0])
                    def mutate(m, name):
                        if name != 'clip' or m.events[-1][1] != 6: return
                        if kind == 'owner': m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                        elif kind == 'epoch': m.put32(m.data + 0x1C, 12)
                        elif kind == 'request': m.put32(b.CONTROLLER + 0x548, 999)
                        elif kind == 'cancel': m.cpu.mem_write(b.CONTROLLER + 0x555, b'\0')
                        elif kind == 'dialog': m.cpu.mem_write(b.CONTROLLER + 0x570, b'\1')
                        elif kind == 'death': m.put64(b.COMP + 0x20, 0)
                        elif kind == 'idle': m.put32(b.CURRENT, 1)
                        else: m.put64(b.CONTROLLER + 0x80, b.OWN_BANK)
                    m.mutate_on_call = mutate
                    m.invoke(m.code + HELPER_OFFSET)
                    self.assertFalse(any(e[0] == 'dispatch' for e in m.events))

    def test_input_protection_only_exact_owned_common41_42_not_boss_or_other_actions(self):
        for hook_name in ('HE_InputA', 'HE_InputB'):
            for action, motion in ((41, 110), (42, 111)):
                for bank, actual_action, actual_motion, suppressed in (
                    (b.BANK, action, motion, True), (b.OWN_BANK, action, motion, False),
                    (b.BANK, action, motion + 1, False), (b.BANK, 43, motion, False)):
                    with self.subTest(hook=hook_name, action=action, bank=bank,
                                      actual_action=actual_action, motion=actual_motion):
                        m = PortableMachine(self.plan)
                        m.put32(b.CURRENT, actual_action); m.put64(b.CURRENT + 0x38, bank)
                        m.put32(b.PARAM + 0x20, actual_motion)
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

    def test_previous_seven_throwables_six_special_items_and_harakiri_keep_routes(self):
        self.assertEqual(len(PREVIOUS_ITEMS), 7)
        for row in PREVIOUS_ITEMS:
            for layout in b.LAYOUTS:
                self.checked_entry(ArrowSlothMachine(self.plan, row[0], layout), True)
        for row in special_tests.ITEM_SPECS:
            self.checked_entry(special_tests.ItemMachine(self.plan, row[0]), True,
                               special_tests.HELPER_OFFSET)
            self.checked_entry(special_tests.ItemMachine(self.plan, row[0]), False)
        checker = harakiri_tests.HarakiriTests()
        for layout in b.LAYOUTS:
            checker.check(harakiri_tests.GateMachine(self.plan, layout), True)
        checker.old, checker.plan = self.base, self.plan
        checker.test_existing_talismans_and_unrelated_categories_preserve_routing()

    def test_pure_transform_only_three_payloads_tail_prefix_and_all_native_sites_preserved(self):
        before = deepcopy(self.base)
        self.assertEqual(apply_arrow_sloth(self.base), self.plan)
        self.assertEqual(self.base, before)
        for layout in b.LAYOUTS:
            old, new = assemble(self.base, *layout), assemble(self.plan, *layout)
            self.assertEqual(len(new), 82)
            self.assertEqual(tuple(a['name'] for a, c in zip(old, new)
                                   if a['payload'] != c['payload']), CHANGED_HOOKS)
            for a, c in zip(old, new):
                for field in ('name', 'site', 'target', 'original', 'patched',
                              'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])
                self.assertLessEqual(len(c['payload']), c['code_capacity'])
                if a['name'] == CARRIER_NAME:
                    prefix = HELPER_OFFSET - a['code_offset']
                    self.assertEqual(a['payload'][:prefix], c['payload'][:prefix])
                elif a['name'] not in CHANGED_HOOKS:
                    self.assertEqual(a['payload'], c['payload'])
        for bad in (load_plan(), apply_dung_fan(apply_harakiri(load_plan())), self.plan):
            with self.assertRaises(ValueError): apply_arrow_sloth(bad)
        tampered = deepcopy(self.base)
        next(h for h in tampered['hooks'] if h['name'] == CARRIER_NAME)['asm'] += '\nnop\n'
        with self.assertRaises(ValueError): apply_arrow_sloth(tampered)


if __name__ == '__main__':
    unittest.main()
