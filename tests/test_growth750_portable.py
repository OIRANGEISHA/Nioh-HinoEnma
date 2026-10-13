"""Current 82-hook growth revision in isolated CPU memory.

Full native calculation calls are explicit ABI stubs. A separate local audit
executes the real game curve/Focus functions; this file needs no game files.
"""
import struct
import unittest
from copy import deepcopy
from unittest.mock import patch

import test_inherent_element_portable as harness
from test_inherent_element_portable import (
    OverlayMachine, ACTOR, COMPONENT, METADATA, STACK, reg, XMMS, LAYOUTS,
)
from build_profile import load_plan, assemble
from hinoenma_growth750 import apply_growth750, mapped_index, HOOK_NAME

from build_profile import ROOT, source_plan_beta562
import json
BASELINE = source_plan_beta562(json.loads((ROOT / 'profiles/legacy-beta5.6.2.json').read_text('utf-8')))
PLAN = load_plan()
SAVED_MANAGER = 0x31000000
WORLD = ACTOR + 0x60000
CURVE_KEYS = ('hp_growth_native_hp', 'combat_growth_native_ki',
              'combat_growth_native_attack', 'combat_growth_native_defense',
              'combat_growth_difficulty_index')
ASSEMBLY_CACHE = {}


def cached_assemble(plan, module, allocation):
    key = (id(plan), module, allocation)
    if key not in ASSEMBLY_CACHE:
        ASSEMBLY_CACHE[key] = (plan, assemble(plan, module, allocation))
    return ASSEMBLY_CACHE[key][1]


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class GrowthMachine(OverlayMachine):
    def __init__(self, *, level=750, native_index=1, layout=LAYOUTS[0],
                 flag=1, ids=(11, 22), focus=(0, 0, 0, 0)):
        # Cache assembly only; native helpers remain the explicit test stubs.
        with patch.object(harness, 'assemble', cached_assemble):
            super().__init__(PLAN, layout=layout, flag=flag, ids=ids)
        self.cpu.mem_map(SAVED_MANAGER, 0x210000)
        self.put64(self.module + PLAN['targets']['hp_growth_saved_manager'], SAVED_MANAGER)
        self.put32(SAVED_MANAGER + 0xAE5C4, level)
        self.put32(COMPONENT + 8, native_index)
        for name in CURVE_KEYS:
            address = self.module + PLAN['targets'][name]
            self.functions[address] = name
            self.cpu.mem_write(address, b'\xC3')
        constants = dict(combat_growth_one=1., combat_growth_percent=.01,
                         combat_growth_attack_high_factor=1.15)
        for name in (*constants, 'combat_growth_world_slot'):
            address = self.module + PLAN['targets'][name]
            if not any(first <= address <= last for first, last, _ in self.cpu.mem_regions()):
                self.cpu.mem_map(address & ~0xFFF, 0x1000)
        self.put64(self.module + PLAN['targets']['combat_growth_world_slot'], WORLD)
        self.put64(WORLD + 0x560, WORLD + 0x1000)
        self.put32(WORLD + 0x1010, 5)
        for name, number in constants.items():
            self.cpu.mem_write(self.module + PLAN['targets'][name], struct.pack('<f', number))
        self.put32(METADATA + 0xD0, 160)
        for offset in (0x1298, 0x129C, 0x12A0, 0x12A4):
            self.cpu.mem_write(COMPONENT + offset, struct.pack('<f', 1.))
        # Native-focus-like fixtures: ordinary gear and growth are deliberately
        # nonzero so multiplying a final player total would fail the checks.
        self.focus = focus
        self.focus_bonus = tuple(int(f32(f32(level) * f32(factor)))
                                 for level, factor in zip(focus, (.5, .2, .2, .1)))
        self.flat_deltas = [self.focus_bonus[1]] * 2
        for slot in range(2):
            struct.pack_into('<i', self.reference, 12 + slot * 40, 7 + slot)
            struct.pack_into('<i', self.real, 12 + slot * 40, 7 + slot + self.flat_deltas[slot])
        for field, bonus in ((0, self.focus_bonus[0]), (0xE0, self.focus_bonus[2])):
            struct.pack_into('<I', self.real, field, struct.unpack_from('<I', self.real, field)[0] + bonus)
        self.curve_calls = []
        self.curves = {'hp_growth_native_hp': lambda index: 10000 + index,
                       'combat_growth_native_ki': lambda index: 1.8,
                       'combat_growth_native_attack': lambda index: 1000 + index,
                       'combat_growth_native_defense': lambda index: 500 + index,
                       'combat_growth_difficulty_index': lambda index: 5}

    def trace(self, cpu, address, size, user):
        name = getattr(self, 'functions', {}).get(address)
        if name not in CURVE_KEYS:
            super().trace(cpu, address, size, user)
            if name == 'player_stats':
                bonus = 0 if self.player_calls % 2 == 1 else self.focus_bonus[3]
                self.put32(self.effects + 0x1EC, 184 + bonus)
            return
        stack = cpu.reg_read(reg.UC_X86_REG_RSP)
        if stack % 16 != 8:
            raise AssertionError('Growth callee stack is not Win64 aligned')
        rcx, rdx = (cpu.reg_read(r) for r in (reg.UC_X86_REG_RCX, reg.UC_X86_REG_RDX))
        index = rcx if name == 'combat_growth_native_ki' else rdx
        if name not in ('combat_growth_native_ki', 'combat_growth_difficulty_index') and rcx != METADATA:
            raise AssertionError('Wrong native curve owner')
        self.curve_calls.append((name, index))
        value = self.curves[name](index)
        cpu.mem_write(stack + 8, b'\xA5' * 32)
        for register in (reg.UC_X86_REG_RAX, reg.UC_X86_REG_RCX, reg.UC_X86_REG_RDX,
                         reg.UC_X86_REG_R8, reg.UC_X86_REG_R9, reg.UC_X86_REG_R10,
                         reg.UC_X86_REG_R11, *XMMS[:6]):
            cpu.reg_write(register, 0xFEED001122334455)
        cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0x202)
        if name == 'combat_growth_native_ki':
            cpu.reg_write(reg.UC_X86_REG_XMM0, struct.unpack('<I', struct.pack('<f', value))[0])
        else:
            cpu.reg_write(reg.UC_X86_REG_RAX, int(value))

    def refresh(self):
        self.player_calls = 0
        self.stop = None
        self.calls.clear()
        self.curve_calls.clear()
        self.cpu.reg_write(reg.UC_X86_REG_RSP, STACK)
        self.cpu.reg_write(reg.UC_X86_REG_RCX, self.stats)
        self.cpu.reg_write(reg.UC_X86_REG_RDX, ACTOR)
        self.run()
        if self.registers() != self.boss_return_registers:
            raise AssertionError('Overlay did not restore native return registers/flags')

    def signed(self, address):
        return struct.unpack('<i', self.cpu.mem_read(address, 4))[0]


class Growth750Tests(unittest.TestCase):
    def test_only_current_attribute_payload_changes_and_fits_all_aslr(self):
        original = deepcopy(BASELINE)
        for layout in LAYOUTS:
            old, new = assemble(BASELINE, *layout), assemble(PLAN, *layout)
            for a, b in zip(old, new):
                self.assertEqual(a['patched'], b['patched'])
                self.assertEqual(a['code_capacity'], b['code_capacity'])
                if a['name'] != HOOK_NAME:
                    self.assertEqual(a, b)
                else:
                    self.assertNotEqual(a['payload'], b['payload'])
                    self.assertLessEqual(len(b['payload']), 0x1000)
        self.assertEqual(BASELINE, original)
        with self.assertRaises(ValueError):
            apply_growth750(PLAN)

    def test_math_endpoints_and_every_valid_live_level_in_cpu(self):
        values = [mapped_index(level) for level in range(751)]
        self.assertEqual((values[0], values[400], values[401], values[750]), (1, 2413, 2419, 4525))
        self.assertTrue(all(b - a in (6, 7) for a, b in zip(values, values[1:])))
        m = GrowthMachine()
        for level in range(1, 751):
            m.put32(SAVED_MANAGER + 0xAE5C4, level)
            m.refresh()
            requested = [idx for name, idx in m.curve_calls if name != 'combat_growth_difficulty_index']
            self.assertEqual(requested, [values[level]] * 4)
            mult = 2 if level >= 401 else 1
            self.assertEqual(m.get32(m.stats), (10000 + values[level]) * mult + 120)
            base = int(f32((1000 + values[level]) * f32(1.15)))
            if level >= 401:
                base = base * 6 // 5
            self.assertEqual(m.get32(m.stats + 8), base + 100)

    def test_all_four_focus_channels_boundaries_and_legal_mixture(self):
        m = GrowthMachine()
        for channel in range(4):
            for level in (0, 1, 4, 5, 999, 1000):
                levels = [0] * 4
                levels[channel] = level
                case = GrowthMachine(focus=levels)
                case.refresh()
                self.assertEqual(case.get32(case.stats), (10000 + 4525) * 2 + 120 + case.focus_bonus[0])
                self.assertEqual(case.get32(case.stats + 0xE0), 500 + 4525 + 200 + case.focus_bonus[2])
                self.assertEqual(case.get32(case.effects + 0x1EC), 184 + case.focus_bonus[3])
                for view in range(5):
                    boss_flat = struct.unpack_from('<i', case.boss, 12 + view * 40)[0]
                    self.assertEqual(case.signed(case.stats + 12 + view * 40), boss_flat + case.focus_bonus[1])
        mixture = GrowthMachine(focus=(250, 250, 250, 250))
        mixture.refresh()
        self.assertEqual(mixture.focus_bonus, (125, 50, 50, 25))
        self.assertEqual(mixture.get32(mixture.effects + 0x1EC), 209)

    def test_native_index_preserved_and_threshold_still_applies(self):
        for level, native in ((400, 5000), (401, 2419), (750, 5000)):
            m = GrowthMachine(level=level, native_index=native)
            m.refresh()
            self.assertEqual(m.curve_calls, [])
            self.assertEqual(m.get32(COMPONENT + 8), native)
            self.assertEqual(m.get32(m.stats), 7000 * (2 if level >= 401 else 1) + 120)
            for view in range(5):
                basis = 74 + view
                if level >= 401:
                    basis = basis * 6 // 5
                self.assertEqual(m.get32(m.stats + 8 + view * 40), basis + 100)

    def test_invalid_levels_keep_native_basis_but_preserve_focus(self):
        for level in (0, 751, 0xFFFFFFFF):
            m = GrowthMachine(level=level, focus=(0, 1000, 0, 0))
            m.refresh()
            self.assertEqual(m.curve_calls, [])
            self.assertEqual(m.get32(m.stats), 7120)
            self.assertEqual(m.get32(m.stats + 8), 174)
            self.assertEqual(m.signed(m.stats + 12), 0x20202020 + 200)

    def test_selection_empty_fallback_signed_flat_removal_and_no_accumulation(self):
        for flag, ids, selected in ((1, (11, 22), 0), (0, (11, 22), 1),
                                    (1, (-1, 22), 1), (0, (11, -1), 0)):
            m = GrowthMachine(flag=flag, ids=ids)
            for view in range(5):
                struct.pack_into('<i', m.boss, 12 + view * 40, 10)
            for delta in (200, 0, -17):
                for slot in range(2):
                    struct.pack_into('<i', m.real, 12 + slot * 40, 7 + slot + (delta if slot == selected else 500))
                for repeat in range(10):
                    m.refresh()
                    self.assertEqual(m.get32(m.data + 0x8C), selected)
                    for view in range(5):
                        self.assertEqual(m.signed(m.stats + 12 + view * 40), 10 + delta)
                self.assertEqual(m.get32(m.cache + 8), 2 if selected == 0 else 3)
                self.assertEqual(m.get32(m.cache + 0xC), 8 if selected == 0 else 90)

    def test_foreign_actors_metadata_views_and_disabled_overlay_fail_closed(self):
        cases = ((ACTOR + 0xEF0, 1, 4), (ACTOR + 6, 2, 2),
                 (COMPONENT, ACTOR + 0x100, 8), (COMPONENT + 0xB98, ACTOR, 8),
                 (METADATA + 0xC, 0, 4))
        for address, value, size in cases:
            m = GrowthMachine()
            m.cpu.mem_write(address, value.to_bytes(size, 'little'))
            m.refresh()
            self.assertEqual(m.curve_calls, [])
            self.assertEqual(m.player_calls, 0)
            self.assertEqual(bytes(m.cpu.mem_read(m.stats, 0x198)), bytes(m.boss))

    def test_scoped_writes_keep_save_metadata_equipment_current_hp_and_other_fields(self):
        m = GrowthMachine()
        spans = ((METADATA, 0x1000), (SAVED_MANAGER, 0x210000),
                 (COMPONENT + 0x18, 0x28), (COMPONENT + 0x128, 0x8B0))
        before = [bytes(m.cpu.mem_read(at, size)) for at, size in spans]
        m.refresh()
        self.assertEqual(before, [bytes(m.cpu.mem_read(at, size)) for at, size in spans])
        for view in range(5):
            start = 8 + view * 40
            self.assertEqual(bytes(m.cpu.mem_read(m.stats + start + 8, 32)), m.boss[start + 8:start + 40])
        self.assertEqual(m.get32(m.stats + 4), 298)


if __name__ == '__main__':
    unittest.main()
