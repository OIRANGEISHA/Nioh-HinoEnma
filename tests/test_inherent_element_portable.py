"""Portable innate-element CPU regressions using constructed records only.

No game executable, private source modules, saved snapshots or process access
are used. Public generated payloads execute in Unicorn. Native overlay calls
are explicit RET stubs with synthetic results, so these checks establish ABI,
ownership, cache and preservation behavior rather than gameplay correctness.
"""
from __future__ import annotations

from copy import deepcopy
import struct
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from build_profile import assemble, load_plan, source_plan_v059, source_plan_beta52
from hinoenma_ladder_scale import apply_ladder_scale
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
import unicorn.x86_const as reg

PLAN = source_plan_beta52(load_plan())
BASELINE = source_plan_v059(PLAN)
BASELINE['allocation_size'] = 0x19000
BASELINE = apply_ladder_scale(BASELINE)
CACHE_OFFSET, CACHE_SIZE = 0x1F000, 0x40
HOOK_NAMES = ('HE_AttributeOverlay', 'HE_ProjectileElementInheritance',
              'HE_GrabElementDamage', 'HE_GrabElementAccumulation',
              'HE_InherentDirectElement')
LAYOUTS = ((0x140000000, 0x144000000),
           (0x7FF600000000, 0x7FF604000000),
           (0x180000000, 0x176000000))
ACTOR = 0x30000000
COMPONENT = ACTOR + 0x3000
PROXY = ACTOR + 0x5000
CONTROLLER = ACTOR + 0x6000
METADATA = ACTOR + 0x7000
PROJECTILE = ACTOR + 0x8000
PARAMETERS = ACTOR + 0x9000
CONTEXT = ACTOR + 0xA000
DESCRIPTORS = tuple(ACTOR + 0x10000 + 0x80 * index for index in range(4))
RECORD = ACTOR + 0x20000
MOTION_PARAMETERS = ACTOR + 0x21000
COLLISION = ACTOR + 0x24000
VECTOR = ACTOR + 0x70000
STACK_BASE, STACK = 0x20000000, 0x20008000
GPRS = tuple(getattr(reg, 'UC_X86_REG_' + name) for name in
             ('RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'RBP', 'RSP',
              'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15'))
XMMS = tuple(getattr(reg, 'UC_X86_REG_XMM' + str(index)) for index in range(16))
REGS = GPRS + XMMS + (reg.UC_X86_REG_EFLAGS, reg.UC_X86_REG_MXCSR)


def pack32(value):
    return struct.pack('<I', value & 0xFFFFFFFF)


def capture_cache_asm():
    # Execute the exact fragment included in the public overlay, instead of a
    # private generator or a second implementation of the cache algorithm.
    overlay = next(h for h in PLAN['hooks'] if h['name'] == 'HE_AttributeOverlay')
    marker = 'inc dword ptr [r11+0x9C]\n'
    tail = 'mov edx, 8\nattr_restore_boss_weapon:'
    if overlay['asm'].count(marker) != 1 or overlay['asm'].count(tail) != 1:
        raise AssertionError('Public capture insertion ABI changed')
    return overlay['asm'].split(marker)[1].split(tail)[0]


class Machine:
    def __init__(self, name, *, layout=LAYOUTS[0], **options):
        self.module, self.code = layout
        self.data = self.code + PLAN['data_offset']
        self.cache = self.code + CACHE_OFFSET
        self.hook = next(entry for entry in assemble(PLAN, *layout) if entry['name'] == name)
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_64)
        for start, size in ((self.module, 0x1200000), (self.module + 0x18A0000, 0x1000),
                            (self.code, PLAN['allocation_size']), (STACK_BASE, 0x10000),
                            (ACTOR, 0xC0000)):
            self.cpu.mem_map(start, size)
        self.cpu.mem_write(self.hook['target'], self.hook['payload'])
        self.put32(self.data + 0x58, 1)
        for index, register in enumerate(GPRS):
            self.cpu.reg_write(register, 0x1234ABC000 + index)
        for index, register in enumerate(XMMS):
            self.cpu.reg_write(register, (0xAABBCCDD00112233 << 64) + 0x12340000 + index)
        self.cpu.reg_write(reg.UC_X86_REG_RSP, STACK)
        self.cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0x247)
        self.cpu.reg_write(reg.UC_X86_REG_MXCSR, 0x1F80)
        self.cpu.mem_write(STACK, b'\xCC' * 0x300)
        self.stop = None
        self.calls = []
        self.native_stub_calls = []
        self.writes = []
        self.continuation = self.hook['site'] + self.hook['length']
        self.cpu.hook_add(UC_HOOK_CODE, self.trace)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE, self.write_trace)
        self.seed(options)

    def write_trace(self, cpu, access, address, size, value, _):
        self.writes.append((address, size, value))

    def trace(self, cpu, address, size, _):
        if address == self.continuation:
            self.stop = address
            cpu.emu_stop()
        elif address in (self.module + 0x950A80, self.module + 0x951A00):
            rsp = cpu.reg_read(reg.UC_X86_REG_RSP)
            if rsp % 16 != 8:
                raise AssertionError('Native reference helper stack ABI')
            self.native_stub_calls.append((address - self.module, cpu.reg_read(reg.UC_X86_REG_RCX)))

    def put32(self, at, value): self.cpu.mem_write(at, pack32(value))
    def put64(self, at, value): self.cpu.mem_write(at, struct.pack('<Q', value & 0xFFFFFFFFFFFFFFFF))
    def get32(self, at): return struct.unpack('<I', self.cpu.mem_read(at, 4))[0]
    def get64(self, at): return struct.unpack('<Q', self.cpu.mem_read(at, 8))[0]

    def seed(self, o):
        self.options = o
        template = o.get('template', 0x58E5E)
        self.put32(self.data + 4, template if o.get('loaded', True) else 0)
        self.put64(self.data + 0x10, o.get('captured', ACTOR))
        self.put64(self.module + PLAN['targets']['player_slot'], o.get('native_player', ACTOR))
        self.put32(ACTOR, template)
        self.cpu.mem_write(ACTOR + 4, struct.pack('<HH', o.get('kind', 0), o.get('instance', 1)))
        self.put32(ACTOR + 0xEF0, o.get('state', 0))
        self.put64(ACTOR + 0xE90, METADATA if o.get('metadata', True) else 0)
        self.put32(METADATA + 0x0C, o.get('role', 1))
        self.put64(ACTOR + 0x240, COMPONENT if o.get('component', True) else 0)
        self.put64(COMPONENT, o.get('component_owner', ACTOR))
        self.put64(COMPONENT + 0x108, o.get('resource_owner', ACTOR))
        self.put64(COMPONENT + 0xB98, o.get('external_component', 0))
        self.put64(COMPONENT + 0x20, o.get('hp', 1000))
        self.put32(COMPONENT + 0x1118, o.get('buff_element', -1))
        self.put32(COMPONENT + 0x111C, o.get('buff_power', 0))
        self.put32(self.data + 0x1C, o.get('epoch', 19))
        self.put32(self.data + 0x8C, o.get('slot', 0))
        self.put32(self.data + 0x98, o.get('item_id', 55904))
        self.put32(self.data + 0x9C, o.get('recalc', 11))
        self.put32(self.cache, o.get('cache_seq', 2))
        self.put32(self.cache + 8, o.get('cache_element', 2))
        self.put32(self.cache + 0xC, o.get('cache_power', 8))
        self.put64(self.cache + 0x10, o.get('cache_actor', ACTOR))
        self.put64(self.cache + 0x18, o.get('cache_component', COMPONENT))
        self.put32(self.cache + 0x20, o.get('cache_epoch', o.get('epoch', 19)))
        self.put32(self.cache + 0x24, o.get('cache_item_id', o.get('item_id', 55904)))
        self.put32(self.cache + 0x28, o.get('cache_slot', o.get('slot', 0)))
        self.put32(self.cache + 0x2C, o.get('cache_recalc', o.get('recalc', 11)))
        self.put64(ACTOR + 0x230, PROXY if o.get('proxy', True) else 0)
        self.put64(PROXY, o.get('proxy_owner', ACTOR))
        self.put64(PROXY + 8, CONTROLLER if o.get('controller', True) else 0)
        self.put64(CONTROLLER + 0x50, o.get('controller_owner', ACTOR))
        self.put64(CONTROLLER + 0x5B0, o.get('controller_collision', COLLISION))
        self.put64(CONTROLLER + 0x58, RECORD if o.get('record', True) else 0)
        self.put32(RECORD, o.get('action_id', 857))
        self.cpu.mem_write(RECORD + 0x40, bytes([o.get('started', 1)]))
        self.put64(RECORD + 0x20, MOTION_PARAMETERS if o.get('parameters', True) else 0)
        self.put32(MOTION_PARAMETERS + 0x20, o.get('motion', 1101))
        first = o.get('first', 21)
        self.cpu.mem_write(RECORD + 0x50, struct.pack('<HH', first, o.get('count', 4)))
        self.put64(RECORD + 0x48, VECTOR if o.get('vector', True) else 0)
        for index, descriptor in enumerate(DESCRIPTORS):
            self.cpu.mem_write(descriptor, bytes((index * 17 + at * 7) & 0xFF for at in range(0x80)))
            self.put64(descriptor, o.get('descriptor_flags', 0x2800000000400404))
            self.cpu.mem_write(descriptor + 0x1D, bytes([o.get('coefficient', 0)]))
            self.cpu.mem_write(descriptor + 0x20, bytes([o.get('intrinsic', 0xFF)]))
            self.cpu.mem_write(descriptor + 0x4F, bytes([o.get('attribute', 0x29)]))
            self.cpu.mem_write(descriptor + 0x44, struct.pack('<H', o.get('direct_flags', 0x200D)))
            self.put64(VECTOR + (min(first, 4096) + index) * 8, descriptor if o.get('member', True) else 0)
        self.descriptor = DESCRIPTORS[o.get('descriptor_index', 0)]

    def registers(self): return {r: self.cpu.reg_read(r) for r in REGS}

    def run(self):
        self.cpu.emu_start(self.hook['target'], 0, count=4000)
        if self.stop != self.continuation:
            raise AssertionError('Hook did not reach native continuation')

    def pair(self): return self.get32(CONTEXT + 0x18), self.get32(CONTEXT + 0x1C)

    def context(self, *, body=False):
        o = self.options
        self.native_copy = struct.pack('<4I', o.get('original_element', -1) & 0xFFFFFFFF,
                                       o.get('original_power', 50 if body else 150) & 0xFFFFFFFF,
                                       o.get('paralysis', 43), o.get('physics', 0x3F99999A))
        self.cpu.mem_write(PARAMETERS + 7, self.native_copy)
        self.cpu.mem_write(CONTEXT, b'\x6D' * 0x180)
        self.put64(CONTEXT, o.get('context_descriptor', self.descriptor))
        self.put64(CONTEXT + 0x28, o.get('source_owner', ACTOR if body else PROJECTILE))
        self.put64(CONTEXT + 0xE0, self.descriptor)
        self.put32(PROJECTILE, o.get('projectile_template', 0x11F85))
        self.cpu.mem_write(PROJECTILE + 4, struct.pack('<HH', o.get('projectile_kind', 4), 87))
        self.put64(PROJECTILE + 0x200, o.get('parent', ACTOR))
        self.cpu.reg_write(reg.UC_X86_REG_RBP, PARAMETERS)
        self.cpu.reg_write(reg.UC_X86_REG_RDI, CONTEXT)
        self.cpu.reg_write(reg.UC_X86_REG_R15, ACTOR if body else PROJECTILE)
        self.cpu.reg_write(reg.UC_X86_REG_R12, o.get('descriptor_register', self.descriptor))
        return self

    def direct(self):
        o = self.options
        self.native_copy = struct.pack('<4I', o.get('original_element', -1) & 0xFFFFFFFF,
                                       o.get('original_power', 0) & 0xFFFFFFFF,
                                       o.get('paralysis', 43), o.get('physics', 0x3F99999A))
        self.cpu.mem_write(STACK + 0x30, self.native_copy)
        self.cpu.reg_write(reg.UC_X86_REG_RBP, STACK + 0x100)
        self.cpu.reg_write(reg.UC_X86_REG_RDI, o.get('direct_actor', ACTOR))
        self.cpu.reg_write(reg.UC_X86_REG_RSI, o.get('direct_controller', CONTROLLER))
        self.cpu.reg_write(reg.UC_X86_REG_R14, o.get('direct_target', COLLISION))
        # At 717F06 native RBX has already become the source actor. The saved
        # direct descriptor is the first qword of native context [RSP+70].
        self.cpu.reg_write(reg.UC_X86_REG_RBX, o.get('direct_source_actor', ACTOR))
        self.put64(STACK + 0x70, o.get('direct_descriptor', self.descriptor))
        return self

    def coefficient(self):
        o = self.options
        self.put64(CONTEXT, o.get('context_descriptor', self.descriptor))
        self.put64(CONTEXT + 0xE0, self.descriptor)
        self.put64(CONTEXT + 0x28, o.get('source_owner', ACTOR))
        self.put64(CONTEXT + 0xE8, o.get('attacker_owner', ACTOR))
        self.put64(CONTEXT + 0x100, o.get('context_collision', COLLISION))
        self.cpu.mem_write(CONTEXT + 0x145, bytes([o.get('special100', 0)]))
        element = o.get('buff_element', -1)
        power = o.get('buff_power', 0)
        if not 0 <= element <= 4 or power <= 0:
            element, power = o.get('cache_element', 2), o.get('cache_power', 8)
        self.put32(CONTEXT + 0x18, o.get('context_element', element))
        self.put32(CONTEXT + 0x1C, o.get('context_power', power))
        self.cpu.reg_write(reg.UC_X86_REG_R15, CONTEXT)
        self.cpu.reg_write(reg.UC_X86_REG_RAX, self.descriptor)
        return self

    def capture(self):
        preview = COMPONENT + 0x9D8
        saves = 'pushfq\npush rax\npush rcx\npush rdx\npush r9\n'
        restores = 'pop r9\npop rdx\npop rcx\npop rax\npopfq\njmp {return}\n'
        source = (saves + capture_cache_asm() + restores).format(data=hex(self.data), **{'return': hex(self.continuation)})
        encoded, _ = Ks(KS_ARCH_X86, KS_MODE_64).asm(source, self.hook['target'])
        self.cpu.mem_write(self.hook['target'], bytes(encoded))
        self.hook = dict(self.hook, name='CaptureFragment', payload=bytes(encoded))
        for register, value in ((reg.UC_X86_REG_R11, self.data), (reg.UC_X86_REG_R12, preview),
                                (reg.UC_X86_REG_RSI, COMPONENT), (reg.UC_X86_REG_R14, ACTOR)):
            self.cpu.reg_write(register, value)
        return self


def synthetic_stats(hp, ki, defense, attack):
    output = bytearray(0x198)
    struct.pack_into('<2I', output, 0, hp, ki)
    for index in range(5):
        struct.pack_into('<10I', output, 8 + index * 0x28,
                         attack + index, 1, 2, 3, 4, 0xFFFFFFFF, 6, 7, 8, 9)
    for offset in range(0xD0, 0x124, 4):
        struct.pack_into('<I', output, offset, 100)
    struct.pack_into('<I', output, 0xE0, defense)
    for offset in (0xDC, 0x174):
        struct.pack_into('<f', output, offset, 1.)
    for offset in range(0x124, 0x15C, 8):
        struct.pack_into('<H', output, offset, 15)
    return output


class OverlayMachine(Machine):
    """Full public overlay with constructed RET-stub native results."""
    def __init__(self, plan, *, layout=LAYOUTS[0], flag=1, ids=(11, 22)):
        super().__init__('HE_AttributeOverlay', layout=layout)
        self.plan = plan
        self.hook = next(h for h in assemble(plan, *layout) if h['name'] == 'HE_AttributeOverlay')
        self.cpu.mem_write(self.hook['target'], self.hook['payload'])
        self.continuation = self.hook['site'] + self.hook['length']
        self.stats = COMPONENT + 0x9D8
        self.growth, self.effects = ACTOR + 0x40000, ACTOR + 0x41000
        self.saved = ACTOR + 0x42000
        self.ids, self.player_calls = ids, 0
        self.boss = synthetic_stats(7000, 160, 95, 74)
        for index in range(5):
            at = 8 + index * 0x28
            self.boss[at+4:at+0x28] = bytes([0x20 + index]) * 0x24
        self.reference = synthetic_stats(1000, 100, 0, 50)
        self.real = synthetic_stats(1120, 110, 200, 150)
        for index, pair in enumerate(((2, 8), (3, 90))):
            struct.pack_into('<2I', self.real, 8 + index * 0x28 + 0x14, *pair)
        self.put64(self.stats + 0x198, self.effects)
        self.put64(self.stats + 0x1A0, self.saved)
        self.put64(self.stats + 0x1A8, self.growth)
        self.put64(self.stats + 0x1B0, self.saved)
        self.cpu.mem_write(self.saved, b'\x5A' * 0x1000)
        self.cpu.mem_write(COMPONENT + 0x9CC, bytes([flag]))
        self.put32(METADATA, 0x58E5E)
        manager = self.module + plan['targets']['hp_growth_saved_manager']
        self.cpu.mem_map(manager & ~0xFFF, 0x1000)
        self.put64(manager, 0)
        self.functions = {self.module + plan['targets'][key]: key for key in
                          ('boss_stats', 'equipment_construct', 'growth_reset',
                           'growth_load', 'equipment_load', 'player_stats')}
        for address in self.functions:
            self.cpu.mem_write(address, b'\xC3')
        for register, value in ((reg.UC_X86_REG_RSI, COMPONENT),
                                (reg.UC_X86_REG_R14, ACTOR),
                                (reg.UC_X86_REG_R12, self.stats),
                                (reg.UC_X86_REG_RCX, self.stats),
                                (reg.UC_X86_REG_RDX, ACTOR)):
            self.cpu.reg_write(register, value)
        self.boss_return_registers = None

    def trace(self, cpu, address, size, _):
        name = getattr(self, 'functions', {}).get(address)
        if name is None:
            return super().trace(cpu, address, size, _)
        rsp = cpu.reg_read(reg.UC_X86_REG_RSP)
        if rsp % 16 != 8:
            raise AssertionError('Overlay callee Win64 alignment')
        args = tuple(cpu.reg_read(r) for r in
                     (reg.UC_X86_REG_RCX, reg.UC_X86_REG_RDX,
                      reg.UC_X86_REG_R8, reg.UC_X86_REG_R9))
        self.calls.append((name, args))
        if name == 'boss_stats':
            if args[:2] != (self.stats, ACTOR):
                raise AssertionError('Foreign Boss baseline argument')
            cpu.mem_write(self.stats, bytes(self.boss))
        elif name == 'equipment_construct':
            cpu.mem_write(args[0], bytes(0x8B0))
        elif name == 'equipment_load':
            cpu.mem_write(args[0], b'\x11' * 0x8B0)
            for slot, item in enumerate(self.ids):
                self.put32(args[0] + slot * 0xC8, item)
        elif name in ('growth_reset', 'growth_load'):
            if args[0] != self.growth:
                raise AssertionError('Foreign growth output')
            self.put32(self.growth, 1 if name == 'growth_reset' else 5)
        elif name == 'player_stats':
            if args[0] != self.stats or args[2:] != (0, 0):
                raise AssertionError('Invalid player-preview arguments')
            self.player_calls += 1
            preview = self.reference if self.player_calls == 1 else self.real
            cpu.mem_write(self.stats, bytes(preview))
            cpu.mem_write(self.effects, b'\x00' if self.player_calls == 1 else b'\x42')
        cpu.mem_write(rsp + 8, b'\xA5' * 32)
        for register in (reg.UC_X86_REG_RAX, reg.UC_X86_REG_RCX,
                         reg.UC_X86_REG_RDX, reg.UC_X86_REG_R8,
                         reg.UC_X86_REG_R9, reg.UC_X86_REG_R10,
                         reg.UC_X86_REG_R11, *XMMS[:6]):
            cpu.reg_write(register, 0xFEED001122334455)
        cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0x202)
        if name == 'boss_stats':
            self.boss_return_registers = self.registers()
            self.boss_return_registers[reg.UC_X86_REG_RSP] = STACK


class InherentElementTests(unittest.TestCase):
    comparisons = 0
    baseline_comparisons = 0

    def test_public_payload_capacity_layout_and_unmodified55_preserved_at_three_aslr(self):
        self.assertEqual((len(PLAN['hooks']), PLAN['data_offset'], PLAN['allocation_size']),
                         (60, 0xF000, 0x20000))
        self.assertEqual(PLAN['tool_version'], '1.0.0-beta.5.2')
        for layout in LAYOUTS:
            old, current = assemble(BASELINE, *layout), assemble(PLAN, *layout)
            for left, right in zip(old, current):
                for field in ('name', 'rva', 'original', 'length', 'site'):
                    self.assertEqual(left[field], right[field])
                if left['name'] not in HOOK_NAMES:
                    self.assertEqual(left, right)
                    type(self).baseline_comparisons += 1
            for entry in current:
                self.assertLessEqual(len(entry['payload']), entry.get('code_capacity', 0x400))
                self.assertFalse(entry['code_offset'] < CACHE_OFFSET + 0x1000 and
                                 entry['code_offset'] + entry.get('code_capacity', 0x400) > CACHE_OFFSET)
            direct = current[-1]
            self.assertEqual((direct['name'], direct['rva'], direct['length']),
                             ('HE_InherentDirectElement', 0x717F06, 9))

    def test_full_overlay_capture_keeps_boss_growth_gear_and_native_temporary_state(self):
        cases = ((1, (11, 22), 0), (0, (11, 22), 1),
                 (1, (-1, 22), 1), (0, (11, -1), 0),
                 (1, (-1, -1), 0), (0, (-1, -1), 1))
        for layout in LAYOUTS:
            for flag, ids, slot in cases:
                outcomes = []
                for plan in (BASELINE, PLAN):
                    m = OverlayMachine(plan, layout=layout, flag=flag, ids=ids)
                    saved = bytes(m.cpu.mem_read(m.saved, 0x1000))
                    buff = bytes(m.cpu.mem_read(COMPONENT + 0x1118, 8))
                    m.run()
                    self.assertEqual(m.registers(), m.boss_return_registers)
                    self.assertEqual(bytes(m.cpu.mem_read(m.saved, 0x1000)), saved)
                    self.assertEqual(bytes(m.cpu.mem_read(COMPONENT + 0x1118, 8)), buff)
                    self.assertEqual(m.get32(m.stats), 7120)
                    self.assertEqual(m.get32(m.stats + 4), 170)
                    self.assertEqual(m.get32(m.stats + 0xE0), 295)
                    for index in range(5):
                        at = 8 + index * 0x28
                        self.assertEqual(bytes(m.cpu.mem_read(m.stats + at + 4, 0x24)),
                                         bytes(m.boss[at+4:at+0x28]))
                    outcomes.append((bytes(m.cpu.mem_read(ACTOR, 0xC0000)),
                                     bytes(m.cpu.mem_read(m.data, 0x1000)),
                                     m.registers(), m.calls))
                    if plan is PLAN:
                        pair = ((2, 8), (3, 90))[slot] if ids[slot] != -1 else (0xFFFFFFFF, 0)
                        self.assertEqual((m.get32(m.cache + 8), m.get32(m.cache + 0xC)), pair)
                        self.assertEqual(m.get32(m.cache + 0x28), slot)
                        self.assertEqual(m.get32(m.cache + 0x24), ids[slot] & 0xFFFFFFFF)
                        self.assertEqual(m.get32(m.cache), 4)
                    type(self).comparisons += 1
                self.assertEqual(outcomes[0], outcomes[1],
                                 'Capture must not alter Boss/growth/gear/buff/core result')

    def verify(self, m, pair=None, coefficient=None, capture=False):
        before = m.registers()
        actor = bytes(m.cpu.mem_read(ACTOR, 0xC0000))
        data = bytes(m.cpu.mem_read(m.data, 0x1000))
        cache = bytes(m.cpu.mem_read(m.cache, CACHE_SIZE))
        stack = bytearray(m.cpu.mem_read(STACK, 0x300))
        expected_actor = bytearray(actor)
        if m.hook['name'] == 'HE_ProjectileElementInheritance':
            at = CONTEXT - ACTOR + 0x18
            expected_actor[at:at + 16] = m.native_copy
            if pair is not None:
                expected_actor[at:at + 8] = struct.pack('<2I', *pair)
            before[reg.UC_X86_REG_XMM1] = int.from_bytes(m.native_copy, 'little')
        elif m.hook['name'] == 'HE_InherentDirectElement':
            at = 0x100 - 0x78
            stack[at:at + 16] = m.native_copy
            if pair is not None:
                stack[at:at + 8] = struct.pack('<2I', *pair)
            before[reg.UC_X86_REG_XMM1] = int.from_bytes(m.native_copy, 'little')
        elif m.hook['name'] in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
            target = reg.UC_X86_REG_XMM1 if m.hook['name'] == 'HE_GrabElementDamage' else reg.UC_X86_REG_XMM2
            before[reg.UC_X86_REG_RCX] = m.options.get('coefficient', 0)
            before[target] = m.options.get('coefficient', 0) if coefficient is None else coefficient
        m.run()
        self.assertEqual(m.registers(), before, 'all GPR/XMM/flags/MXCSR/native results')
        self.assertEqual(bytes(m.cpu.mem_read(ACTOR, 0xC0000)), bytes(expected_actor))
        self.assertEqual(bytes(m.cpu.mem_read(m.data, 0x1000)), data, 'Boss/private core state')
        if not capture:
            self.assertEqual(bytes(m.cpu.mem_read(m.cache, CACHE_SIZE)), cache, 'read-only cache consumers')
        self.assertEqual(bytes(m.cpu.mem_read(STACK, 0x300)), bytes(stack), 'native stack above RSP')
        allowed = [(STACK_BASE, STACK)]
        if m.hook['name'] == 'HE_ProjectileElementInheritance': allowed.append((CONTEXT + 0x18, CONTEXT + 0x28))
        if m.hook['name'] == 'HE_InherentDirectElement': allowed.append((STACK + 0x88, STACK + 0x98))
        if capture: allowed.append((m.cache, m.cache + CACHE_SIZE))
        self.assertTrue(all(any(lo <= at and at + n <= hi for lo, hi in allowed)
                            for at, n, _ in m.writes), 'writes limited to native output/cache/stack spills')
        self.assertFalse(m.calls)
        type(self).comparisons += 1
        return m


    def test_body_needle_dive_effect_fallback_preserves_other_descriptor_bytes_across_three_aslr(self):
        for layout in LAYOUTS:
            for body, template in ((True, None), (False, 0x11F85), (False, 0xADD70)):
                for actor_template in (0x58E5E, 0x51BE1):
                    for element in range(5):
                        with self.subTest(layout=layout, body=body, projectile=template, element=element):
                            o = dict(template=actor_template, cache_element=element)
                            if template is not None: o['projectile_template'] = template
                            self.verify(Machine('HE_ProjectileElementInheritance', layout=layout, **o).context(body=body), pair=(element, 8))


    def test_capture_selected_row_only_and_no_element_resets_previous_cache(self):
        for layout in LAYOUTS:
            for slot, item_id, elements, wanted in (
                    (0, 55904, ((2, 8), (3, 90)), (2, 8)),
                    (1, 55904, ((3, 90), (2, 8)), (2, 8)),
                    (0, -1, ((2, 8), (3, 90)), (0xFFFFFFFF, 0)),
                    (1, -1, ((3, 90), (2, 8)), (0xFFFFFFFF, 0)),
                    (0, 55904, ((-1, 0), (3, 90)), (0xFFFFFFFF, 0)),
                    (0, 55904, ((5, 8), (3, 90)), (0xFFFFFFFF, 0)),
                    (0, 55904, ((2, 0), (3, 90)), (0xFFFFFFFF, 0)),
                    (2, 55904, ((2, 8), (3, 90)), (0xFFFFFFFF, 0))):
                m = Machine('HE_InherentDirectElement', layout=layout, slot=slot, item_id=item_id)
                preview = COMPONENT + 0x9D8
                for index, pair in enumerate(elements):
                    m.cpu.mem_write(preview + 8 + index * 0x28 + 0x14, struct.pack('<2I', *(v & 0xFFFFFFFF for v in pair)))
                # Execute the capture at its real insertion ABI, with a wrapper
                # preserving all scratch state just as the overlay's outer save.
                m.capture()
                self.verify(m, capture=True)
                self.assertEqual((m.get32(m.cache + 8), m.get32(m.cache + 0xC)), wanted)
                self.assertEqual(m.get32(m.cache), 4)
                self.assertEqual(m.get64(m.cache + 0x10), ACTOR)
                self.assertEqual(m.get64(m.cache + 0x18), COMPONENT)
                self.assertEqual(tuple(m.get32(m.cache + at) for at in (0x20, 0x24, 0x28, 0x2C)),
                                 (19, item_id & 0xFFFFFFFF, slot, 11))


    def test_capture_busy_writer_preserves_every_cache_byte_and_normal_writers_end_even(self):
        for layout in LAYOUTS:
            for sequence in (0, 2, 4, 0xFFFFFFFE, 1, 3, 0xFFFFFFFF):
                m = Machine('HE_InherentDirectElement', layout=layout, cache_seq=sequence).capture()
                m.cpu.mem_write(COMPONENT + 0x9D8 + 0x1C, struct.pack('<2I', 2, 8))
                before = bytes(m.cpu.mem_read(m.cache, CACHE_SIZE))
                self.verify(m, capture=True)
                if sequence & 1:
                    self.assertEqual(bytes(m.cpu.mem_read(m.cache, CACHE_SIZE)), before)
                else:
                    self.assertEqual(m.get32(m.cache), (sequence + 2) & 0xFFFFFFFF)
                    self.assertEqual((m.get32(m.cache + 8), m.get32(m.cache + 0xC)), (2, 8))


    def test_capture_compare_exchange_lost_writer_race_does_not_overwrite_other_writer(self):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
        for layout in LAYOUTS:
            m = Machine('HE_InherentDirectElement', layout=layout).capture()
            m.cpu.mem_write(COMPONENT + 0x9D8 + 0x1C, struct.pack('<2I', 2, 8))
            capture_at = next(i.address for i in Cs(CS_ARCH_X86, CS_MODE_64).disasm(m.hook['payload'], m.hook['target'])
                              if i.mnemonic == 'lock cmpxchg')
            before = bytearray(m.cpu.mem_read(m.cache, CACHE_SIZE))
            struct.pack_into('<I', before, 0, 3)
            writes = []
            def other_writer(cpu, address, size, _):
                if address == capture_at:
                    m.put32(m.cache, 3)
                    writes.append(True)
            m.cpu.hook_add(UC_HOOK_CODE, other_writer)
            self.verify(m, capture=True)
            self.assertEqual(writes, [True])
            self.assertEqual(bytes(m.cpu.mem_read(m.cache, CACHE_SIZE)), bytes(before))


    def test_original_protected_roar_also_rejects_unset_descriptor_and_context(self):
        for temporary in ({}, {'buff_element': 2, 'buff_power': 30}):
            self.verify(Machine('HE_ProjectileElementInheritance', projectile_template=0xBEA31, **temporary).context())


    def test_invalid_temporary_pair_never_silently_falls_back_to_permanent_enchant(self):
        for o in ({'buff_element': 5, 'buff_power': 30}, {'buff_element': 6, 'buff_power': 150},
                  {'buff_element': -2, 'buff_power': 8}, {'buff_element': 2, 'buff_power': 0},
                  {'buff_element': 2, 'buff_power': -1}):
            self.verify(Machine('HE_ProjectileElementInheritance', **o).context(body=True))
            self.verify(Machine('HE_InherentDirectElement', **o).direct())
            for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                self.verify(Machine(name, **o).coefficient())


    def test_cache_sequence_changed_during_read_is_rejected_without_context_pair_write(self):
        m = Machine('HE_ProjectileElementInheritance').context(body=True)
        changed = []
        # Locate the second sequence comparison and force a recalc between
        # reading the first sequence and validating the completed pair.
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
        compare = next(i.address for i in Cs(CS_ARCH_X86, CS_MODE_64).disasm(m.hook['payload'], m.hook['target'])
                       if i.mnemonic == 'cmp' and i.op_str == 'r8d, dword ptr [r9]')
        def mutate(cpu, address, size, _):
            if address == compare:
                m.put32(m.cache, 4)
                changed.append(True)
        m.cpu.hook_add(UC_HOOK_CODE, mutate)
        # External fixture mutation is recorded separately; the consumer itself
        # must retain the original attack pair and native state.
        before = m.registers()
        actor = bytearray(m.cpu.mem_read(ACTOR, 0xC0000))
        actor[CONTEXT - ACTOR + 0x18:CONTEXT - ACTOR + 0x28] = m.native_copy
        before[reg.UC_X86_REG_XMM1] = int.from_bytes(m.native_copy, 'little')
        m.run()
        self.assertEqual(changed, [True])
        self.assertEqual(m.registers(), before)
        self.assertEqual(bytes(m.cpu.mem_read(ACTOR, 0xC0000)), bytes(actor))
        type(self).comparisons += 1


    def test_temporary_talisman_or_living_weapon_pair_has_priority_and_never_writes_buff(self):
        for layout in LAYOUTS:
            for body in (True, False):
                for element in range(5):
                    m = Machine('HE_ProjectileElementInheritance', layout=layout, buff_element=element, buff_power=30).context(body=body)
                    self.verify(m, pair=(element, 30))
            self.verify(Machine('HE_InherentDirectElement', layout=layout, buff_element=1, buff_power=30).direct(), pair=(1, 30))
            for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                self.verify(Machine(name, layout=layout, buff_element=1, buff_power=30).coefficient(), coefficient=10)


    def test_context_unset_checks_type_only_original_nonzero_unset_power_is_supported(self):
        for power in (0, 50, 150, 0x7FFFFFFF):
            self.verify(Machine('HE_ProjectileElementInheritance', original_power=power).context(body=True), pair=(2, 8))
        for element in (0, 1, 2, 3, 4, 5, 6, 9, 43, -2, 0x80000000):
            self.verify(Machine('HE_ProjectileElementInheritance', original_element=element).context())
            self.verify(Machine('HE_InherentDirectElement', original_element=element).direct())


    def test_protected_roar_and_intrinsic_dive_remain_native_with_cache_and_buff(self):
        for options in ({'projectile_template': 0xBEA31, 'original_element': 6, 'original_power': 150},
                        {'projectile_template': 0xADD70, 'original_element': 9, 'original_power': 0}):
            for temporary in ({}, {'buff_element': 2, 'buff_power': 30}):
                self.verify(Machine('HE_ProjectileElementInheritance', **options, **temporary).context())


    def test_verified_body_primary_type6_ordinary_kick_umbrella_and_charge_inherit(self):
        # These approved decimal attributes are the published J/I/charge
        # descriptors. Type 6 is their native primary channel, rather than the
        # independent needle status channel. We assert only the primary pair.
        for layout in LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for attribute in (42, 44, 45):
                    for source in ({'cache_element': 2, 'cache_power': 8},
                                   {'buff_element': 3, 'buff_power': 30}):
                        m = Machine('HE_ProjectileElementInheritance', layout=layout,
                                    template=template, intrinsic=6, coefficient=10,
                                    attribute=attribute, **source).context(body=True)
                        wanted = ((3, 30) if 'buff_element' in source else (2, 8))
                        self.verify(m, pair=wanted)


    def test_type6_body_requires_exact_ordinary_attributes_and_other_intrinsics_remain_protected(self):
        for source in ({}, {'buff_element': 3, 'buff_power': 30}):
            for attribute in (0, 41, 43, 46, 0x42, 0x44, 0x45, 0xFF):
                self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=6,
                                    coefficient=10, attribute=attribute, **source).context(body=True))
            for attribute in (42, 44, 45):
                self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=6,
                                    coefficient=0, attribute=attribute,
                                    **source).context(body=True))
                self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=6,
                                    coefficient=10, attribute=attribute, descriptor_flags=1 << 43,
                                    **source).context(body=True))
                for intrinsic in tuple(range(6)) + tuple(range(7, 16)):
                    self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=intrinsic,
                                        coefficient=10, attribute=attribute, **source).context(body=True))
                # Existing completed elemental contexts remain original even
                # when the descriptor is an approved ordinary primary type 6.
                for context_element in (0, 1, 2, 3, 4, 6, 9):
                    self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=6,
                                        coefficient=10, attribute=attribute, original_element=context_element,
                                        **source).context(body=True))
                for projectile in (0x11F85, 0xADD70, 0xBEA31):
                    self.verify(Machine('HE_ProjectileElementInheritance', intrinsic=6,
                                        coefficient=10, attribute=attribute, projectile_template=projectile,
                                        **source).context())


    def test_read_only_consumers_reject_stale_cache_foreign_owners_and_no_or_percent_only_element(self):
        cases = ({'cache_seq': 3}, {'cache_actor': ACTOR + 0x1000},
                 {'cache_component': COMPONENT + 0x1000}, {'cache_epoch': 20},
                 {'cache_item_id': 55905}, {'cache_slot': 1}, {'cache_recalc': 12},
                 {'cache_element': -1}, {'cache_element': 5}, {'cache_element': 0x80000000},
                 {'cache_power': 0}, {'cache_power': -1}, {'item_id': -1},
                 {'loaded': False}, {'captured': 0}, {'native_player': ACTOR + 0x1000},
                 {'template': 0x64}, {'instance': 0}, {'instance': 2}, {'state': 1},
                 {'metadata': False}, {'role': 0}, {'role': 2}, {'component': False},
                 {'kind': 1}, {'external_component': COMPONENT + 0x1000},
                 {'component_owner': ACTOR + 0x1000}, {'resource_owner': ACTOR + 0x1000},
                 {'hp': 0}, {'hp': -1})
        for o in cases:
            with self.subTest(**o):
                self.verify(Machine('HE_ProjectileElementInheritance', **o).context(body=True))
                self.verify(Machine('HE_ProjectileElementInheritance', **o).context())
                self.verify(Machine('HE_InherentDirectElement', **o).direct())
                for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                    self.verify(Machine(name, **o).coefficient())


    def test_body_context_and_owned_projectile_descriptor_rejections_replay_native_only(self):
        for o in ({'source_owner': 0}, {'source_owner': ACTOR + 0x1000},
                  {'context_descriptor': DESCRIPTORS[1]}, {'descriptor_register': DESCRIPTORS[1]},
                  {'intrinsic': 2}, {'descriptor_flags': 1 << 43}):
            self.verify(Machine('HE_ProjectileElementInheritance', **o).context(body=True))
        for o in ({'projectile_kind': 0}, {'projectile_kind': 1}, {'projectile_kind': 3},
                  {'projectile_kind': 5}, {'parent': 0}, {'parent': ACTOR + 0x1000},
                  {'projectile_template': 0x11F86}, {'source_owner': 0},
                  {'context_descriptor': DESCRIPTORS[1]}, {'intrinsic': 2},
                  {'descriptor_flags': 1 << 43}):
            self.verify(Machine('HE_ProjectileElementInheritance', **o).context())


    def test_all_four_successful_grab_direct_descriptors_and_coefficients_use_permanent_pair(self):
        for layout in LAYOUTS:
            for index in range(4):
                for element in range(5):
                    self.verify(Machine('HE_InherentDirectElement', layout=layout, descriptor_index=index, cache_element=element).direct(), pair=(element, 8))
                    for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                        self.verify(Machine(name, layout=layout, descriptor_index=index, cache_element=element).coefficient(), coefficient=10)


    def test_direct_context_requires_exact_paired_target_controller_and_descriptor_membership(self):
        for options in ({'direct_actor': ACTOR + 0x1000},
                        {'direct_controller': CONTROLLER + 0x1000},
                        {'direct_target': COLLISION + 0x1000},
                        {'controller_collision': COLLISION + 0x1000},
                        {'direct_descriptor': DESCRIPTORS[0] + 0x1000}):
            self.verify(Machine('HE_InherentDirectElement', **options).direct())
        for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
            self.verify(Machine(name, context_collision=COLLISION + 0x1000).coefficient())


    def test_grab_context_and_coefficient_scope_fail_closed_for_other_actions_and_resources(self):
        shared = ({'action_id': 858}, {'started': 0}, {'motion': 1102}, {'record': False},
                  {'parameters': False}, {'first': 4097}, {'count': 3}, {'count': 5},
                  {'vector': False}, {'member': False}, {'direct_flags': 0},
                  {'descriptor_flags': 1 << 43}, {'proxy': False},
                  {'proxy_owner': ACTOR + 0x1000}, {'controller': False},
                  {'controller_owner': ACTOR + 0x1000}, {'intrinsic': 2})
        for o in shared:
            with self.subTest(**o):
                self.verify(Machine('HE_InherentDirectElement', **o).direct())
                for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                    self.verify(Machine(name, **o).coefficient())
        self.verify(Machine('HE_InherentDirectElement', direct_target=0).direct())
        for o in ({'source_owner': ACTOR + 0x1000}, {'attacker_owner': ACTOR + 0x1000},
                  {'special100': 1}, {'controller_collision': 0}, {'context_collision': 0},
                  {'context_descriptor': DESCRIPTORS[1]}, {'context_element': 3},
                  {'context_power': 9}, {'coefficient': 1}, {'coefficient': 100}):
            for name in ('HE_GrabElementDamage', 'HE_GrabElementAccumulation'):
                self.verify(Machine(name, **o).coefficient())



if __name__ == '__main__':
    unittest.main()
