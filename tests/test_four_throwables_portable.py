"""Synthetic Win64 regression for four exact ordinary throwables.

Only public compatibility code executes. Native calls are explicit stubs;
these checks do not prove native spawn, collision, effects or consumption.
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
from hinoenma_dung_fan import apply_dung_fan, ITEM_SPECS as PREVIOUS_ITEMS
from hinoenma_four_throwables import (apply_four_throwables, ITEM_SPECS, ALL_ITEM_SPECS,
                                     HELPER_OFFSET, CARRIER_NAME, CHANGED_HOOKS)
import test_dung_fan_portable as dung_tests
import test_harakiri_portable as harakiri_tests
import test_special_items_portable as special_tests
from portable_machine import b


class FourThrowableMachine(dung_tests.DungFanMachine):
    def __init__(self, plan, item, layout=b.LAYOUTS[0]):
        with patch.object(dung_tests, 'ITEM_SPECS', ALL_ITEM_SPECS):
            super().__init__(plan, item, layout)


class FourThrowablesPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = apply_dung_fan(apply_harakiri(load_plan()))
        cls.plan = apply_four_throwables(cls.base)

    checked_entry = dung_tests.DungFanPortableTests.checked_entry

    def test_four_items_two_templates_three_layouts_keep_native_route_and_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for row in ITEM_SPECS:
                    with self.subTest(layout=layout, template=template, item=row[0]):
                        m = FourThrowableMachine(self.plan, row[0], layout)
                        for at in (b.ACTOR, b.META, m.data + 4):
                            m.put32(at, template)
                        self.checked_entry(m, True)
                        self.assertEqual(m.events, [('definition', row[0]), ('lookup', 172),
                            ('lookup', 165), ('clip', 2, 103), ('clip', 6, 103),
                            ('dispatch', b.CONTROLLER, 172)])

    def test_ordinary_bombs_require_kind_one_subtype_fourteen(self):
        bombs = [row for row in ITEM_SPECS if row[2] == 14]
        self.assertEqual({row[0] for row in bombs}, {63258, 40896})
        for row in bombs:
            self.checked_entry(FourThrowableMachine(self.plan, row[0]), True)
            for kind, subtype in ((2, 14), (1, 0), (2, 0), (1, 13), (1, 15)):
                with self.subTest(item=row[0], kind=kind, subtype=subtype):
                    m = FourThrowableMachine(self.plan, row[0])
                    m.cpu.mem_write(dung_tests.DEF + 4, bytes([kind, subtype]))
                    self.checked_entry(m, False)
        # Oil and stones remain ordinary kind1/subtype0, not prepared ninjutsu.
        for row in ITEM_SPECS:
            if row[2] != 0: continue
            for kind, subtype in ((2, 0), (1, 14)):
                m = FourThrowableMachine(self.plan, row[0])
                m.cpu.mem_write(dung_tests.DEF + 4, bytes([kind, subtype]))
                self.checked_entry(m, False)

    def test_each_spawn_definition_is_distinct_and_cross_item_spawns_reject(self):
        self.assertEqual(len({row[6] for row in ITEM_SPECS}), 4)
        for row in ITEM_SPECS:
            for other in ITEM_SPECS:
                if row[0] == other[0]: continue
                with self.subTest(item=row[0], other=other[0]):
                    m = FourThrowableMachine(self.plan, row[0])
                    m.put32(dung_tests.DEF + 0x11C, other[6])
                    self.checked_entry(m, False)
            for offset, value in ((0, row[0] + 1), (0x104, 0), (0x10C, 5),
                                  (0x110, 1), (0x114, 1), (0x118, 1), (0x11C, 0)):
                m = FourThrowableMachine(self.plan, row[0])
                m.put32(dung_tests.DEF + offset, value)
                self.checked_entry(m, False)

    def test_request_owner_cancel_and_resource_guards_still_reject(self):
        changes = ((b.CONTROLLER + 0x555, 0, 1), (b.CONTROLLER + 0x556, 1, 1),
            (b.CONTROLLER + 0x550, 2, 4), (b.CONTROLLER + 0x570, 1, 1),
            (b.CONTROLLER + 0x54C, 6, 4), (b.ACTOR + 4, 0x20000, 4),
            (b.COMP + 0x20, 0, 8), (b.PROXY + 8, b.CONTROLLER + 0x100, 8))
        for row in ITEM_SPECS:
            for at, value, width in changes:
                m = FourThrowableMachine(self.plan, row[0])
                m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                self.checked_entry(m, False)
            for slot in (2, 6):
                m = FourThrowableMachine(self.plan, row[0])
                m.put64(b.CLIPS[slot], 0)
                self.checked_entry(m, False)
            m = FourThrowableMachine(self.plan, row[0])
            m.put32(m.lookup_results[165] + 0xC0, 0)
            self.checked_entry(m, False)
            m = FourThrowableMachine(self.plan, row[0])
            m.lookup_results[172] = 0
            self.checked_entry(m, False)

    def test_previous_dung_fan_six_special_items_and_harakiri_preserved(self):
        for row in PREVIOUS_ITEMS:
            for layout in b.LAYOUTS:
                self.checked_entry(FourThrowableMachine(self.plan, row[0], layout), True)
        for row in special_tests.ITEM_SPECS:
            self.checked_entry(special_tests.ItemMachine(self.plan, row[0]), True,
                               special_tests.HELPER_OFFSET)
            self.checked_entry(special_tests.ItemMachine(self.plan, row[0]), False)
        checker = harakiri_tests.HarakiriTests()
        for layout in b.LAYOUTS:
            checker.check(harakiri_tests.GateMachine(self.plan, layout), True)
        checker.old, checker.plan = self.base, self.plan
        checker.test_existing_talismans_and_unrelated_categories_preserve_routing()

    def test_pure_transform_changes_one_tail_only_no_sites_or_input_bytes_change(self):
        saved = deepcopy(self.base)
        self.assertEqual(apply_four_throwables(self.base), self.plan)
        self.assertEqual(self.base, saved)
        for layout in b.LAYOUTS:
            old, new = assemble(self.base, *layout), assemble(self.plan, *layout)
            self.assertEqual(len(new), 82)
            self.assertEqual(tuple(a['name'] for a, c in zip(old, new)
                                   if a['payload'] != c['payload']), CHANGED_HOOKS)
            for a, c in zip(old, new):
                for field in ('name', 'site', 'target', 'original', 'patched',
                              'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])
                if a['name'] == CARRIER_NAME:
                    prefix_size = HELPER_OFFSET - a['code_offset']
                    self.assertEqual(a['payload'][:prefix_size], c['payload'][:prefix_size])
                    self.assertLessEqual(len(c['payload']), c['code_capacity'])
                else:
                    self.assertEqual(a['payload'], c['payload'])
        for bad in (load_plan(), apply_harakiri(load_plan()), self.plan):
            with self.assertRaises(ValueError): apply_four_throwables(bad)
        tampered = deepcopy(self.base)
        carrier = next(h for h in tampered['hooks'] if h['name'] == CARRIER_NAME)
        carrier['asm'] += '\nnop\n'
        with self.assertRaises(ValueError): apply_four_throwables(tampered)


if __name__ == '__main__':
    unittest.main()
