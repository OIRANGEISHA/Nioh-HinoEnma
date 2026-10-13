"""Offline CPU regressions for the three prepared spell requests.

Only generated compatibility payloads execute. Synthetic action banks expose
the real lookup wrapper to a colliding Boss42 record; native definition, clip
and setter boundaries are ABI-clobbering stubs. These tests do not execute the
game's query/event engine, consume stock, spawn effects or validate gameplay.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import load_beta6_plan as load_plan, load_beta563_plan, assemble
import hinoenma_wind_weakness_dragon as spell
import test_arrow_sloth_portable as arrow_tests
import test_arrow_sloth_lookup_portable as lookup_tests
import test_dung_fan_portable as dung_tests
import test_special_items_portable as special_tests
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

# Observations are fixed separately from the implementation's dispatch tables.
# The schedules are the sixteen six-byte references at action params+0x40.
OBSERVED_ITEMS = (
    (26116, 2, 15, 25, 5, (0, 0, 0), 0xD3A86, 1165, 111, 359),
    (44930, 2, 15, 9, 5, (0, 0, 0), 0x7ED63, 42, 111, 194),
    (44607, 2, 14, 30, 5, (0, 0, 0), 0x7BF64, 1227, 60020, 462),
)
OBSERVED_SCHEDULES = {
    42: '11001100ffff1f006800ffff14000000320011273200280014005a000e0011276800ffff7a00320019008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    1165: '11001100ffff1f006800ffff14000000320011273200280014005a000e0011276800ffff9b00320019008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    1227: 'ffff0000ffffaf0012000100b00058000100ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    1228: 'ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff00001e00ffff1f00ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
}
OBSERVED_GUARDS = {
    42: ((17, 6, -1, 21, 255, 255, -1), (20, -1, -1, -1, 255, 18, -1),
         (31, 5, -1, -1, 255, 255, -1), (122, -1, -1, -1, 255, 255, -1),
         (142, -1, -1, -1, 255, 255, -1), (143, -1, -1, -1, 255, 255, -1),
         (10001, -1, -1, -1, 255, 0, -1)),
    1165: ((17, 6, -1, 21, 255, 255, -1), (20, -1, -1, -1, 255, 18, -1),
           (31, 5, -1, -1, 255, 255, -1), (142, -1, -1, -1, 255, 255, -1),
           (143, -1, -1, -1, 255, 255, -1), (155, -1, -1, -1, 255, 255, -1),
           (10001, -1, -1, -1, 255, 0, -1)),
    1227: ((175, 2, 0x7BF64, 1, 255, 255, -1), (176, 5, -1, -1, 255, 255, -1)),
    1228: (),
}
FIXTURE_ITEMS = arrow_tests.ALL_ITEM_SPECS + OBSERVED_ITEMS
FIXTURE_SCHEDULES = {**arrow_tests.SCHEDULE_HEX, **OBSERVED_SCHEDULES}
FIXTURE_GUARDS = {**arrow_tests.EVENT_GUARDS, **OBSERVED_GUARDS}
RECOVERY_RECORD = b.ACTOR + 0x30400
AUX_TIMING = b.ACTOR + 0xC0000
AUX_PLAYBACK = b.ACTOR + 0xC0100
AUX_RESOURCES = (b.ACTOR + 0xC0200, b.ACTOR + 0xC0220)
AUX_HASHES = (b.ACTOR + 0xC0300, b.ACTOR + 0xC0330)
AUX_TABLES = (b.ACTOR + 0xC1000, b.ACTOR + 0xC3000)
AUX_PACKS = (b.ACTOR + 0xD0000, b.ACTOR + 0x150000)
AUX_CAPACITIES = (953, 811)
AUX_HEADERS = (
    '544d475f5041434b000001013000000010c40700dc010000dc0100000000000030000000a0070000100f000000000000',
    '544d475f5041434b000001013000000010ed06009501000095010000000000003000000090060000f00c000000000000',
)
# key: (index, pack-relative offset, bounded descriptor extent, probe chain)
AUX_RECORDS = (
    {90111: (423, 494208, 1408, ((9, 267, 117), (10, 99404, 13), (11, 34003, 333), (12, 90111, 423))),
     60020: (418, 489632, 1024, ((333, 6030, 220), (334, 257, 107), (335, 21004, 263),
                               (336, 6010, 215), (337, 16011, 227), (338, 30501, 328), (339, 60020, 418))),
     60021: (419, 490656, 1088, ((43, 28, 33), (44, 60021, 419)))},
    {90111: (352, 439264, 1408, ((83, 90111, 352),)),
     60020: (347, 434688, 1024, ((695, 16031, 204), (696, 34100, 271), (697, 34420, 283),
                               (698, 201, 64), (699, 35260, 314), (700, 60020, 347))),
     60021: (348, 435712, 1088, ((565, 977, 186), (566, 34101, 272), (567, 34421, 284),
                               (568, 35360, 325), (569, 60021, 348)))},
)
DRAGON_AUX_HEADERS = {
    60020: (0, 11, 36, 168, 416, 1024, 1024, 1024, 0),
    60021: (0, 11, 36, 168, 540, 1072, 1072, 1072, 0),
}
DRAGON_AUX_EVENTS = {
    60020: ((0, 0, 0), (0, 10, 5), (0, 10, 6), (0, 10, 7), (10, 10, 1),
            (23, 0, 1), (24, 10, 0), (24, 10, 3), (40, 10, 4), (60, 10, 2), (88, 11, 6)),
    60021: ((0, 10, 1), (0, 10, 6), (2, 10, 4), (6, 10, 5), (11, 0, 0),
            (12, 10, 0), (20, 1, 2), (24, 10, 3), (46, 10, 1), (60, 10, 2), (62, 0, 1)),
}


class SpellResources:
    def install_auxiliary_resources(self):
        self.put64(b.ACTOR + 0x68, AUX_TIMING)
        self.put64(AUX_TIMING, self.module + self.plan['targets']['timing_vtable'])
        self.put64(AUX_TIMING + 8, b.ACTOR)
        self.put64(AUX_TIMING + 0x40, AUX_PLAYBACK)
        self.put64(AUX_PLAYBACK, self.module + self.plan['targets']['timing_vtable'] + 0x10)
        self.put64(AUX_PLAYBACK + 8, b.ACTOR)
        self.put32(AUX_PLAYBACK + 0x10, 1)  # Idle's current bank need not be common2.
        self.put32(AUX_PLAYBACK + 0x14, 0)
        for row, pack in enumerate(AUX_PACKS):
            self.put64(AUX_TIMING + 0x20 + row * 0x18, AUX_RESOURCES[row])
            self.put64(AUX_RESOURCES[row], pack)
            self.put64(AUX_RESOURCES[row] + 8, AUX_HASHES[row])
            self.put32(AUX_HASHES[row] + 8, AUX_CAPACITIES[row])
            self.put64(AUX_HASHES[row] + 0x10, AUX_TABLES[row])
            self.cpu.mem_write(AUX_TABLES[row], b'\xFF' * (AUX_CAPACITIES[row] * 8))
            self.cpu.mem_write(pack, bytes.fromhex(AUX_HEADERS[row]))
            for key, (index, offset, extent, probes) in AUX_RECORDS[row].items():
                for bucket, actual_key, actual_index in probes:
                    self.put32(AUX_TABLES[row] + bucket * 8, actual_key)
                    self.put32(AUX_TABLES[row] + bucket * 8 + 4, actual_index)
                self.put32(pack + 0x30 + index * 4, offset)
                self.put32(pack + 0x30 + (index + 1) * 4, offset + extent)
                if key == 90111:
                    raw = bytes.fromhex(spell.WIND_DESCRIPTOR_HEX)
                else:
                    words = DRAGON_AUX_HEADERS[key] + tuple(v for event in DRAGON_AUX_EVENTS[key] for v in event)
                    raw = struct.pack('<' + 'I' * len(words), *words)
                self.cpu.mem_write(pack + offset, raw)

    def install_spell_resources(self):
        self.motion_by_key = {(slot, motion): index for slot in (2, 6)
                              for motion, index in ((111, 0), (60020, 0), (60021, 1))}
        self.put32(self.lookup_results[self.action] + 0xB4,
                   90111 if self.item == 26116 else -1)
        if self.item == 44607:
            self.lookup_results[1228] = RECOVERY_RECORD
            self.put64(b.VECTOR + 16, RECOVERY_RECORD)
            self.put32(b.BANK + 0x130, 3)
            self.put32(RECOVERY_RECORD, 1228)
            self.put64(RECOVERY_RECORD + 0x20, RECOVERY_RECORD + 0x80)
            self.put64(RECOVERY_RECORD + 0x38, b.BANK)
            self.cpu.mem_write(RECOVERY_RECORD + 0x40, b'\1')
            self.put32(RECOVERY_RECORD + 0xA0, 60021)
            self.put32(RECOVERY_RECORD + 0xB4, -1)
            self.cpu.mem_write(RECOVERY_RECORD + 0xC0,
                               bytes.fromhex(OBSERVED_SCHEDULES[1228]))
            for slot in (2, 6):
                self.put64(b.CLIPS[slot] + 8, b.ACTOR + 0x80100)
        if self.item in (26116, 44607):
            self.install_auxiliary_resources()
        self.events.clear()
        self.writes.clear()

    def trace(self, cpu, address, size, user):
        if self.callbacks.get(address) == 'clip':
            pointer = cpu.reg_read(UC_X86_REG_RCX)
            slot = next(slot for slot, at in b.MAPS.items() if at == pointer)
            motion = cpu.reg_read(UC_X86_REG_EDX)
            previous = self.motion_results[slot]
            self.motion_results[slot] = self.motion_by_key.get((slot, motion), previous)
            try:
                return super().trace(cpu, address, size, user)
            finally:
                self.motion_results[slot] = previous
        return super().trace(cpu, address, size, user)


class SpellMachine(SpellResources, dung_tests.DungFanMachine):
    def __init__(self, plan, item, layout=b.LAYOUTS[0]):
        with patch.multiple(dung_tests, ITEM_SPECS=FIXTURE_ITEMS,
                            SCHEDULE_HEX=FIXTURE_SCHEDULES, EVENT_GUARDS=FIXTURE_GUARDS):
            super().__init__(plan, item, layout)
        self.install_spell_resources()


class SpellLookupMachine(SpellResources, lookup_tests.LookupMachine):
    def __init__(self, plan, item=44930, layout=b.LAYOUTS[0]):
        with patch.multiple(arrow_tests, ALL_ITEM_SPECS=FIXTURE_ITEMS,
                            SCHEDULE_HEX=FIXTURE_SCHEDULES, EVENT_GUARDS=FIXTURE_GUARDS):
            super().__init__(plan, item, layout)
        self.install_spell_resources()


class WindWeaknessDragonPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public_before = (ROOT / 'profiles/steam-1.24.8.json').read_bytes()
        cls.base = load_plan()
        cls.plan = spell.apply_wind_weakness_dragon(cls.base)

    def checked_entry(self, m, accepted):
        dung_tests.DungFanPortableTests().checked_entry(m, accepted, spell.HELPER_OFFSET)

    checked_lookup = lookup_tests.ArrowSlothLookupPortableTests.checked_lookup

    def test_observed_exact_item_definitions_are_the_only_new_items(self):
        self.assertEqual(tuple(spell.ITEM_SPECS), OBSERVED_ITEMS)
        self.assertEqual(tuple(spell.ALL_ITEM_SPECS), FIXTURE_ITEMS)
        for action in (42, 1165, 1227):
            self.assertEqual(spell.SCHEDULE_HEX[action], OBSERVED_SCHEDULES[action])
            self.assertEqual(sorted(spell.EVENT_GUARDS[action]), sorted(OBSERVED_GUARDS[action]))
        self.assertEqual(hashlib.sha256(bytes.fromhex(spell.WIND_DESCRIPTOR_HEX)).hexdigest(),
                         '071e3126c19f1c13911688c0fbca6a7e52b2c362fb51a9aef6b61f3979ddeb56')
        self.assertEqual(spell.RECOVERY_SCHEDULE_HEX, OBSERVED_SCHEDULES[1228])

    def test_three_items_both_templates_three_relocations_enter172_once_with_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for item, *_, action, motion, query in OBSERVED_ITEMS:
                    with self.subTest(layout=layout, template=template, item=item):
                        m = SpellMachine(self.plan, item, layout)
                        for at in (b.ACTOR, b.META, m.data + 4):
                            m.put32(at, template)
                        self.checked_entry(m, True)
                        self.assertEqual(m.events[0], ('definition', item))
                        self.assertIn(('lookup', 172), m.events)
                        self.assertIn(('lookup', action), m.events)
                        for slot in (2, 6):
                            self.assertIn(('clip', slot, motion), m.events)
                        self.assertEqual(m.events[-1], ('dispatch', b.CONTROLLER, 172))
                        if item == 44607:
                            self.assertIn(('lookup', 1228), m.events)
                            for slot in (2, 6):
                                self.assertIn(('clip', slot, 60021), m.events)
                        if item == 26116:
                            self.assertEqual([e[2] for e in m.events if e[0] == 'clip'], [111, 111])

    def test_every_definition_field_and_absent_definition_fail_closed(self):
        for row in OBSERVED_ITEMS:
            for offset, width in ((0, 4), (4, 1), (5, 1), (0x104, 4), (0x10C, 4),
                                  (0x110, 4), (0x114, 4), (0x118, 4), (0x11C, 4)):
                with self.subTest(item=row[0], definition_offset=hex(offset)):
                    m = SpellMachine(self.plan, row[0])
                    at = special_tests.DEFINITION + offset
                    raw = int.from_bytes(m.cpu.mem_read(at, width), 'little')
                    m.cpu.mem_write(at, (raw ^ 1).to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            m = SpellMachine(self.plan, row[0])
            m.definition_result = 0
            self.checked_entry(m, False)

    def test_actor_npc_request_cancel_dialog_and_bank_guards_reject(self):
        mutations = ((b.ACTOR + 4, 0x20000, 4), (b.ACTOR + 0xEF0, 1, 4),
            (b.META + 0xC, 0, 4), (b.META, 0x58E5F, 4),
            (b.PROXY, b.ACTOR + 0x100, 8), (b.PROXY + 8, b.CONTROLLER + 0x100, 8),
            (b.COMP, b.ACTOR + 0x100, 8), (b.COMP + 0x108, b.ACTOR + 0x100, 8),
            (b.COMP + 0x20, 0, 8), (b.CONTROLLER + 0x50, b.ACTOR + 0x100, 8),
            (b.CONTROLLER + 0x548, 999, 4), (b.CONTROLLER + 0x54C, 99, 4),
            (b.CONTROLLER + 0x550, 2, 4), (b.CONTROLLER + 0x554, 1, 1),
            (b.CONTROLLER + 0x555, 0, 1), (b.CONTROLLER + 0x556, 1, 1),
            (b.CONTROLLER + 0x557, 1, 1), (b.CONTROLLER + 0x558, 1, 8),
            (b.CONTROLLER + 0x570, 1, 1), (b.CONTROLLER + 0x728, 1, 8),
            (b.CONTROLLER + 0x720, 0, 8), (b.CURRENT, 1, 4),
            (b.CURRENT + 0x38, b.BANK, 8), (b.CONTROLLER + 0x80, b.OWN_BANK, 8),
            (b.BANK + 0x128, 0, 8), (b.BANK + 0x130, 0, 4))
        for row in OBSERVED_ITEMS:
            for at, value, width in mutations:
                with self.subTest(item=row[0], address=hex(at)):
                    m = SpellMachine(self.plan, row[0])
                    m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            for kind in ('native-owner', 'recorded-owner', 'epoch', 'template'):
                m = SpellMachine(self.plan, row[0])
                if kind == 'native-owner':
                    m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                elif kind == 'recorded-owner':
                    m.put64(m.data + 0x10, b.ACTOR + 0x100)
                elif kind == 'epoch':
                    m.put32(m.data + 0x1C, 0)
                else:
                    m.put32(m.data + 4, 0x58E5F)
                self.checked_entry(m, False)

    def test_all_schedule_bytes_and_event_descriptor_fields_are_guarded(self):
        for item, action in ((26116, 1165), (44930, 42), (44607, 1227), (44607, 1228)):
            for offset in range(0x60):
                with self.subTest(item=item, action=action, schedule_offset=offset):
                    m = SpellMachine(self.plan, item)
                    at = m.lookup_results[action] + 0xC0 + offset
                    m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0] ^ 1]))
                    self.checked_entry(m, False)
            for index, *_ in OBSERVED_GUARDS[action]:
                at = (special_tests.GLOBAL_EVENTS + (index - 10000) * 0x80 if index >= 10000
                      else b.ACTOR + 0xA1000 + index * 0x80)
                for offset in (0x17, 0x18, 0x1C, 0x3F, 0x2A, 0x52):
                    with self.subTest(item=item, action=action, descriptor=index, field=offset):
                        m = SpellMachine(self.plan, item)
                        m.cpu.mem_write(at + offset, bytes([m.cpu.mem_read(at + offset, 1)[0] ^ 1]))
                        self.checked_entry(m, False)

    def test_entry_cast_and_dragon_recovery_records_require_exact_shape(self):
        for row in OBSERVED_ITEMS:
            actions = (172, row[7], 1228) if row[0] == 44607 else (172, row[7])
            for action in actions:
                for kind in ('missing', 'id', 'owner', 'disabled', 'params', 'motion'):
                    with self.subTest(item=row[0], action=action, corruption=kind):
                        m = SpellMachine(self.plan, row[0])
                        record = m.lookup_results[action]
                        if kind == 'missing': m.lookup_results[action] = 0
                        elif kind == 'id': m.put32(record, action + 1)
                        elif kind == 'owner': m.put64(record + 0x38, b.OWN_BANK)
                        elif kind == 'disabled': m.cpu.mem_write(record + 0x40, b'\0')
                        elif kind == 'params': m.put64(record + 0x20, 0)
                        else: m.put32(record + 0xA0, 999)
                        self.checked_entry(m, False)
            for action in actions[1:]:
                for alternate in (-1, 0, 90110, 90111, 90112):
                    expected = 90111 if action == 1165 else -1
                    if alternate == expected:
                        continue
                    with self.subTest(item=row[0], action=action, alternate=alternate):
                        m = SpellMachine(self.plan, row[0])
                        m.put32(m.lookup_results[action] + 0xB4, alternate)
                        self.checked_entry(m, False)

    def test_both_body_slots_and_independent_dragon_recovery_clip_are_required(self):
        for row in OBSERVED_ITEMS:
            motions = (row[8], 60021) if row[0] == 44607 else (row[8],)
            for motion in motions:
                for slot in (2, 6):
                    for kind in ('resource', 'map', 'clip', 'negative', 'range'):
                        with self.subTest(item=row[0], motion=motion, slot=slot, corruption=kind):
                            m = SpellMachine(self.plan, row[0])
                            if kind == 'resource': m.put64(b.MOTION + 8 + slot * 8, 0)
                            elif kind == 'map': m.put64(b.RES[slot] + 0x480, 0)
                            elif kind == 'clip':
                                index = m.motion_by_key[slot, motion]
                                m.put64(b.CLIPS[slot] + index * 8, 0)
                            else:
                                m.motion_by_key[slot, motion] = -1 if kind == 'negative' else 78
                            self.checked_entry(m, False)

    def test_auxiliary_rows_work_from_each_valid_playback_bank_without_rewriting_it(self):
        for item in (26116, 44607):
            for row in (0, 1):
                for bank in (0, 1, 2):
                    with self.subTest(item=item, row=row, bank=bank):
                        m = SpellMachine(self.plan, item)
                        m.put32(AUX_PLAYBACK + 0x10, bank)
                        m.put32(AUX_PLAYBACK + 0x14, row)
                        self.checked_entry(m, True)

    def test_auxiliary_owner_playback_both_pack_headers_and_hash_bounds_are_required(self):
        common = ((b.ACTOR + 0x68, 0, 8), (AUX_TIMING, 0, 8),
            (AUX_TIMING + 8, b.ACTOR + 0x100, 8), (AUX_TIMING + 0x40, 0, 8),
            (AUX_PLAYBACK, 0, 8), (AUX_PLAYBACK + 8, b.ACTOR + 0x100, 8),
            (AUX_PLAYBACK + 0x10, 3, 4), (AUX_PLAYBACK + 0x14, 2, 4),
            (AUX_PLAYBACK + 0x10, 0xFFFFFFFF, 4), (AUX_PLAYBACK + 0x14, 0xFFFFFFFF, 4))
        for item in (26116, 44607):
            for at, value, width in common:
                with self.subTest(item=item, field=hex(at), value=value):
                    m = SpellMachine(self.plan, item)
                    m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                    self.checked_entry(m, False)
            for row in (0, 1):
                mutations = ((AUX_TIMING + 0x20 + row * 0x18, 0, 8),
                    (AUX_RESOURCES[row], 0, 8), (AUX_RESOURCES[row] + 8, 0, 8),
                    (AUX_HASHES[row] + 8, 0, 4),
                    (AUX_HASHES[row] + 8, AUX_CAPACITIES[row] + 1, 4),
                    (AUX_HASHES[row] + 0x10, 0, 8))
                for at, value, width in mutations:
                    with self.subTest(item=item, row=row, field=hex(at), value=value):
                        m = SpellMachine(self.plan, item)
                        m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                        self.checked_entry(m, False)
                for offset in range(0, 0x30, 4):
                    with self.subTest(item=item, row=row, header_offset=offset):
                        m = SpellMachine(self.plan, item)
                        at = AUX_PACKS[row] + offset
                        m.put32(at, m.get32(at) ^ 1)
                        self.checked_entry(m, False)

    def test_auxiliary_exact_hash_chains_index_offsets_and_descriptor_contents_are_guarded(self):
        for item, keys in ((26116, (90111,)), (44607, (60020, 60021))):
            for row in (0, 1):
                for key in keys:
                    index, offset, extent, probes = AUX_RECORDS[row][key]
                    for bucket, _, _ in probes:
                        for field in (0, 4):
                            with self.subTest(item=item, row=row, key=key, bucket=bucket, field=field):
                                m = SpellMachine(self.plan, item)
                                at = AUX_TABLES[row] + bucket * 8 + field
                                m.put32(at, m.get32(at) ^ 1)
                                self.checked_entry(m, False)
                    for wrong_offset in (0, offset + 1, 0xFFFFFFFF):
                        with self.subTest(item=item, row=row, key=key, index_offset=wrong_offset):
                            m = SpellMachine(self.plan, item)
                            m.put32(AUX_PACKS[row] + 0x30 + index * 4, wrong_offset)
                            self.checked_entry(m, False)
                    # Check every compared qword, plus the final byte. Wind's
                    # entire descriptor is exact; Dragon's header and eleven
                    # event triples are exact, with its larger extent bounded.
                    checked_size = extent if key == 90111 else 168
                    for delta in (*range(0, checked_size, 8), checked_size - 1):
                        with self.subTest(item=item, row=row, key=key, descriptor_offset=delta):
                            m = SpellMachine(self.plan, item)
                            at = AUX_PACKS[row] + offset + delta
                            m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0] ^ 1]))
                            self.checked_entry(m, False)

    def test_auxiliary_changes_during_last_body_callback_reject_before_dispatch(self):
        for item, last_motion, key in ((26116, 111, 90111), (44607, 60021, 60021)):
            for kind in ('timing-owner', 'playback-owner', 'row', 'bank-pointer',
                         'pack-pointer', 'hash-zero', 'hash-table', 'key', 'descriptor'):
                with self.subTest(item=item, mutation=kind):
                    m = SpellMachine(self.plan, item)
                    def mutate(m, name):
                        if name != 'clip' or m.events[-1] != ('clip', 6, last_motion): return
                        if kind == 'timing-owner': m.put64(AUX_TIMING + 8, b.ACTOR + 0x100)
                        elif kind == 'playback-owner': m.put64(AUX_PLAYBACK + 8, b.ACTOR + 0x100)
                        elif kind == 'row': m.put32(AUX_PLAYBACK + 0x14, 2)
                        elif kind == 'bank-pointer': m.put64(AUX_TIMING + 0x38, 0)
                        elif kind == 'pack-pointer': m.put64(AUX_RESOURCES[1], 0)
                        elif kind == 'hash-zero': m.put32(AUX_HASHES[1] + 8, 0)
                        elif kind == 'hash-table': m.put64(AUX_HASHES[1] + 0x10, 0)
                        elif kind == 'key':
                            bucket = AUX_RECORDS[1][key][3][-1][0]
                            m.put32(AUX_TABLES[1] + bucket * 8, 0)
                        else: m.put32(AUX_PACKS[1] + AUX_RECORDS[1][key][1], 99)
                    m.mutate_on_call = mutate
                    m.invoke(m.code + spell.HELPER_OFFSET)
                    self.assertIn(('clip', 6, last_motion), m.events)
                    self.assertFalse(any(e[0] == 'dispatch' for e in m.events))

    def test_callback_changes_to_owner_epoch_request_and_resources_never_dispatch(self):
        for row in OBSERVED_ITEMS:
            for kind in ('owner', 'epoch', 'request', 'cancel', 'dialog', 'death',
                         'idle', 'bank', 'motion-owner', 'definition', 'schedule', 'alternate'):
                with self.subTest(item=row[0], mutation=kind):
                    m = SpellMachine(self.plan, row[0])
                    def mutate(m, name):
                        if name != 'clip' or m.events[-1][1] != 6:
                            return
                        if kind == 'owner':
                            m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                        elif kind == 'epoch': m.put32(m.data + 0x1C, 12)
                        elif kind == 'request': m.put32(b.CONTROLLER + 0x548, 999)
                        elif kind == 'cancel': m.cpu.mem_write(b.CONTROLLER + 0x555, b'\0')
                        elif kind == 'dialog': m.cpu.mem_write(b.CONTROLLER + 0x570, b'\1')
                        elif kind == 'death': m.put64(b.COMP + 0x20, 0)
                        elif kind == 'idle': m.put32(b.CURRENT, 1)
                        elif kind == 'bank': m.put64(b.CONTROLLER + 0x80, b.OWN_BANK)
                        elif kind == 'motion-owner': m.put64(b.ACTOR + 0x38, b.MOTION + 0x100)
                        elif kind == 'definition': m.put32(special_tests.DEFINITION + 0x104, 0)
                        elif kind == 'schedule': m.put32(m.lookup_results[m.action] + 0xC0, 0)
                        else: m.put32(m.lookup_results[m.action] + 0xB4, 77)
                    m.mutate_on_call = mutate
                    saved = {}
                    m.invoke(m.code + spell.HELPER_OFFSET,
                             lambda: saved.update({r: m.cpu.reg_read(r) for r in b.REGISTERS}))
                    saved[UC_X86_REG_RSP] = b.STACK
                    self.assertEqual({r: m.cpu.reg_read(r) for r in b.REGISTERS}, saved)
                    self.assertFalse(any(e[0] == 'dispatch' for e in m.events))

    def test_dragon_recovery_changes_during_its_last_clip_lookup_reject(self):
        for kind in ('record', 'params', 'owner', 'disabled', 'motion', 'alternate', 'schedule'):
            with self.subTest(mutation=kind):
                m = SpellMachine(self.plan, 44607)
                def mutate(m, name):
                    if name != 'clip' or m.events[-1] != ('clip', 6, 60021): return
                    if kind == 'record': m.put32(RECOVERY_RECORD, 1229)
                    elif kind == 'params': m.put64(RECOVERY_RECORD + 0x20, RECOVERY_RECORD + 0x88)
                    elif kind == 'owner': m.put64(RECOVERY_RECORD + 0x38, b.OWN_BANK)
                    elif kind == 'disabled': m.cpu.mem_write(RECOVERY_RECORD + 0x40, b'\0')
                    elif kind == 'motion': m.put32(RECOVERY_RECORD + 0xA0, 60020)
                    elif kind == 'alternate': m.put32(RECOVERY_RECORD + 0xB4, 90111)
                    else: m.put32(RECOVERY_RECORD + 0xC0, 0)
                m.mutate_on_call = mutate
                m.invoke(m.code + spell.HELPER_OFFSET)
                self.assertIn(('clip', 6, 60021), m.events)
                self.assertFalse(any(e[0] == 'dispatch' for e in m.events))

    def test_input_preservation_only_exact_owned_common_actions_including_recovery(self):
        for hook_name in ('HE_InputA', 'HE_InputB'):
            for action, motion in ((41, 110), (42, 111), (1165, 111), (1227, 60020), (1228, 60021)):
                for bank, uid, mid, preserved in ((b.BANK, action, motion, True),
                    (b.OWN_BANK, action, motion, False), (b.BANK, action, motion + 1, False),
                    (b.BANK, 9999, motion, False)):
                    with self.subTest(hook=hook_name, action=action, bank=bank, uid=uid, motion=mid):
                        m = PortableMachine(self.plan)
                        m.put32(b.CURRENT, uid)
                        m.put64(b.CURRENT + 0x38, bank)
                        m.put32(b.PARAM + 0x20, mid)
                        for offset in (0xC, 0xE): m.cpu.mem_write(b.INPUT + offset, b'\1')
                        m.cpu.mem_write(m.data + 0x29, b'\1')
                        m.reset()
                        for reg, value in ((UC_X86_REG_RBX, b.CONTROLLER), (UC_X86_REG_RDI, b.INPUT),
                                           (UC_X86_REG_RDX, b.INPUT), (UC_X86_REG_R10, 0),
                                           (UC_X86_REG_RCX, 6)):
                            m.cpu.reg_write(reg, value)
                        hook = m.by_name[hook_name]
                        m.run(hook['target'], hook['site'] + hook['length'])
                        self.assertEqual(m.get32(m.data + 0x24), int(not preserved))
                        self.assertEqual(m.cpu.reg_read(UC_X86_REG_RCX), 6 if preserved else 11)

    def test_weakness42_actual_wrapper_selects_common_record_and_enters172(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for phase, pending in (('idle', 1), ('entry', 0), ('entry', 1), ('cast', 0)):
                    with self.subTest(layout=layout, template=template, phase=phase, pending=pending):
                        m = SpellLookupMachine(self.plan, layout=layout)
                        for at in (b.ACTOR, b.META, m.data + 4): m.put32(at, template)
                        m.phase(phase, pending)
                        self.checked_lookup(m, True)
            m = SpellLookupMachine(self.plan, layout=layout)
            self.checked_entry(m, True)
        self.checked_lookup(SpellLookupMachine(self.plan), True, group=0)
        old = SpellLookupMachine(self.base)
        self.checked_lookup(old, False)
        self.checked_entry(SpellLookupMachine(self.base), False)

    def test_weakness_lookup_rejects_boss_npc_malformed_definition_and_alternate(self):
        for phase, pending in (('boss', 0), ('boss', 1), ('idle', 0)):
            m = SpellLookupMachine(self.plan)
            m.phase(phase, pending)
            self.checked_lookup(m, False)
        for at, value, width in ((b.ACTOR + 4, 0x20000, 4), (b.META + 0xC, 0, 4),
            (b.COMP + 0x20, 0, 8), (b.CONTROLLER + 0x555, 2, 1),
            (b.CONTROLLER + 0x570, 1, 1), (b.CONTROLLER + 0x54C, 7, 4),
            (special_tests.DEFINITION + 0x11C, 0x42B17, 4)):
            m = SpellLookupMachine(self.plan)
            m.cpu.mem_write(at, value.to_bytes(width, 'little'))
            self.checked_lookup(m, False)
        for alternate in (0, 90111):
            m = SpellLookupMachine(self.plan)
            m.put32(m.lookup_results[42] + 0xB4, alternate)
            self.checked_lookup(m, False)
        m = SpellLookupMachine(self.plan)
        npc = b.ACTOR + 0x37000
        m.put64(npc + 0x78, b.OWN_BANK)
        m.put64(npc + 0x80, b.BANK)
        self.checked_lookup(m, False, controller=npc)

    def test_weakness_lookup_missing_or_ambiguous_common_record_and_resources_reject(self):
        for kind in ('missing', 'owner', 'duplicate', 'schedule', 'descriptor', 'slot2', 'slot6'):
            with self.subTest(corruption=kind):
                m = SpellLookupMachine(self.plan)
                record = m.lookup_results[42]
                if kind == 'missing': m.put64(b.VECTOR + 8, 0)
                elif kind == 'owner': m.put64(record + 0x38, b.OWN_BANK)
                elif kind == 'duplicate':
                    m.cpu.mem_write(lookup_tests.EXTRA, bytes(m.cpu.mem_read(record, 0x120)))
                    m.put64(b.VECTOR + 16, lookup_tests.EXTRA)
                    m.put32(b.BANK + 0x130, 3)
                elif kind == 'schedule': m.put32(record + 0xC0, 0)
                elif kind == 'descriptor':
                    m.cpu.mem_write(b.ACTOR + 0xA1000 + 17 * 0x80 + 0x17, b'\xFF')
                else: m.put64(b.CLIPS[2 if kind == 'slot2' else 6], 0)
                self.checked_lookup(m, False)

    def test_weakness_lookup_stale_callbacks_reject_and_preserve_fallback_abi(self):
        for kind in ('epoch', 'owner', 'request', 'cancel', 'definition', 'schedule',
                     'record-owner', 'alternate', 'duplicate'):
            with self.subTest(mutation=kind):
                m = SpellLookupMachine(self.plan)
                def mutate(m, name):
                    if name != 'clip' or m.events[-1][1] != 6: return
                    record = m.lookup_results[42]
                    if kind == 'epoch': m.put32(m.data + 0x1C, 12)
                    elif kind == 'owner': m.put64(m.data + 0x10, b.ACTOR + 0x100)
                    elif kind == 'request': m.put32(b.CONTROLLER + 0x548, 999)
                    elif kind == 'cancel': m.cpu.mem_write(b.CONTROLLER + 0x555, b'\0')
                    elif kind == 'definition': m.put32(special_tests.DEFINITION + 0x104, 0)
                    elif kind == 'schedule': m.put32(record + 0xC0, 0)
                    elif kind == 'record-owner': m.put64(record + 0x38, b.OWN_BANK)
                    elif kind == 'alternate': m.put32(record + 0xB4, 0)
                    else:
                        m.cpu.mem_write(lookup_tests.EXTRA, bytes(m.cpu.mem_read(record, 0x120)))
                        m.put64(b.VECTOR + 16, lookup_tests.EXTRA)
                        m.put32(b.BANK + 0x130, 3)
                m.mutate_on_call = mutate
                result, saved = m.lookup()
                self.assertEqual(result, lookup_tests.PRIVATE_RECORDS[42])
                self.assertEqual(m.fallback_registers[0], saved)
                self.assertEqual(m.native_search_count, 1)

    def test_old_arrow_sloth_lookup_and_all_previous_item_routes_remain_valid(self):
        for row in arrow_tests.ITEM_SPECS:
            for plan in (self.base, self.plan):
                for phase, pending in (('idle', 1), ('entry', 0), ('cast', 0)):
                    m = lookup_tests.LookupMachine(plan, row[0])
                    m.phase(phase, pending)
                    self.checked_lookup(m, True)
                m = lookup_tests.LookupMachine(plan, row[0])
                self.checked_entry(m, True)
        for row in arrow_tests.ALL_ITEM_SPECS:
            self.checked_entry(arrow_tests.ArrowSlothMachine(self.plan, row[0]), True)
        for row in special_tests.ITEM_SPECS:
            dung_tests.DungFanPortableTests().checked_entry(
                special_tests.ItemMachine(self.plan, row[0]), True, special_tests.HELPER_OFFSET)
            self.checked_entry(special_tests.ItemMachine(self.plan, row[0]), False)

    def test_unrelated_lookup_ids_and_unrecognized_requests_match_beta6(self):
        for action in (0, 17, 40, 41, 43, 172, 165, 609, 1165, 1225, 1227, 1228, 9999):
            outcomes = []
            for plan in (self.base, self.plan):
                m = SpellLookupMachine(plan)
                result, _ = m.lookup(action=action)
                outcomes.append((result, m.get32(lookup_tests.GROUP), m.protected_snapshot(),
                                 {r: m.cpu.reg_read(r) for r in b.REGISTERS}))
                self.assertEqual(m.native_search_count, 1)
            self.assertEqual(*outcomes, action)
        for item in (0, 26115, 26117, 44929, 44931, 44606, 44608, 0xFFFFFFFF):
            m = SpellMachine(self.plan, 44930)
            m.put32(b.CONTROLLER + 0x548, item)
            self.checked_entry(m, False)

    def test_transform_is_pure_relocated_and_keeps_beta6_native_sites_and_layout(self):
        saved = deepcopy(self.base)
        self.assertEqual(spell.apply_wind_weakness_dragon(self.base), self.plan)
        self.assertEqual(self.base, saved)
        self.assertEqual((ROOT / 'profiles/steam-1.24.8.json').read_bytes(), self.public_before)
        self.assertEqual(self.base['tool_version'], '1.0.0-beta.6')
        for key in ('targets', 'allocation_size', 'data_offset'):
            self.assertEqual(self.base[key], self.plan[key])
        for layout in b.LAYOUTS:
            old, new = assemble(self.base, *layout), assemble(self.plan, *layout)
            self.assertEqual((len(old), len(new)), (82, 82))
            changed = tuple(a['name'] for a, c in zip(old, new) if a['payload'] != c['payload'])
            self.assertEqual(changed, ('HE_InputA', 'HE_InputB', spell.CARRIER_NAME))
            self.assertEqual(changed, spell.CHANGED_HOOKS)
            for a, c in zip(old, new):
                for field in ('name', 'rva', 'length', 'site', 'target', 'original', 'patched',
                              'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])
                self.assertLessEqual(len(c['payload']), c['code_capacity'])
                if a['name'] == spell.CARRIER_NAME:
                    prefix = spell.HELPER_OFFSET - a['code_offset']
                    self.assertEqual(a['payload'][:prefix], c['payload'][:prefix])
                elif a['name'] not in spell.CHANGED_HOOKS:
                    self.assertEqual(a['payload'], c['payload'])
        for candidate in (load_beta563_plan(), self.plan):
            with self.assertRaises(ValueError):
                spell.apply_wind_weakness_dragon(candidate)
        for name in (*spell.CHANGED_HOOKS, 'HE_LadderCommonLookup'):
            tampered = deepcopy(self.base)
            next(h for h in tampered['hooks'] if h['name'] == name)['asm'] += '\nnop\n'
            with self.assertRaises(ValueError, msg=name):
                spell.apply_wind_weakness_dragon(tampered)


if __name__ == '__main__':
    unittest.main()
