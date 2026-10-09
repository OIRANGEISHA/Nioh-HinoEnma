"""Synthetic CPU regressions for bounded Salt recovery and event catch-up.

Only public assembly executes. Native motion lookup/scheduling are Win64 RET
stubs, and all action/descriptor records are constructed here from the public
ABI. Native damage, query predicates, resource hash, inventory and animation
do not execute. No private fixtures, game bytes or process are accessed.
"""
import json
from copy import deepcopy
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import source_plan, assemble, relocation_specs, ROUTES_OFFSET, ROUTE_BYTES
from hinoenma_special_item_actions import SCHEDULE_HEX
from hinoenma_salt_damage205_draft import ROUTES
from hinoenma_salt_hurt_compatibility import HELPER_OFFSET, TOKEN_OFFSET, TOKEN_SIZE
from hinoenma_salt_event_catchup import OFFSET as EVENT_OFFSET, STATE_OFFSET
from portable_machine import PortableMachine, b
from unicorn.x86_const import *

TABLE, UNIQUE, ENTRIES, OUTPUT = (b.ACTOR + x for x in (0xF0000, 0xE0000, 0xE1000, 0xD8000))
FIRST, NEXT, QUALIFICATION = 0x711A09, 0x711B1B, 0x7216D7
MOTIONS = {982: 120, 224: -1, 147: -1, 151: -1, 152: -1,
           205: 30310, 85: 30002, 96: 30014, 106: 30102, 107: 30102, 108: 30108, 109: 30108}


def descriptor(target, query2=0xFFFF):
    """Build the declared 48-byte ABI pattern; no saved game record is used."""
    query1 = 0xFFFF if target == 205 else 52
    return struct.pack('<6Q', 0xFFFFFFFF00000000 | (query2 << 16) | query1,
                       0x00FFFFFFFF00FFFF, target << 32,
                       0x00000000646480FF if target == 205 else 0x00200040646480FF,
                       0xFFFFFFFF7FFF8000, 0xFFFFFFFFFFFFFFFF)


class SaltMachine(PortableMachine):
    def __init__(self, plan, layout=b.LAYOUTS[0]):
        super().__init__(plan, layout)
        self.records, self.entries = {}, {}
        headers = {source: (first, count) for _, source, _, _, first, count in ROUTES}
        for i, (action, motion) in enumerate(MOTIONS.items()):
            at = b.ACTOR + 0xC0000 + i * 0x200
            self.records[action] = at
            self.put64(b.VECTOR + i * 8, at)
            self.put32(at, action)
            self.put64(at + 0x20, at + 0x100)
            self.put64(at + 0x38, b.BANK)
            self.cpu.mem_write(at + 0x40, b'\x01')
            self.put64(at + 0x78, TABLE)
            first, count = headers.get(action, (0, 1))
            self.cpu.mem_write(at + 0x80, struct.pack('<HH', first, count))
            self.put32(at + 0x120, motion)
            if action == 982:
                self.cpu.mem_write(at + 0x140, bytes.fromhex(SCHEDULE_HEX[982]))
        self.put32(b.BANK + 0x130, len(self.records))
        self.put64(b.BANK + 0x50, TABLE)
        self.cpu.mem_write(b.BANK + 0x58, struct.pack('<HH', 0x4000, 0x3FFF))
        self.put64(b.BANK + 0x60, UNIQUE)
        aliases = {}
        for target, source, index, query, _, _ in ROUTES:
            raw = descriptor(target, query)
            at = aliases.get(raw)
            if at is None:
                at = ENTRIES + len(aliases) * 0x30
                aliases[raw] = at
                self.cpu.mem_write(at, raw)
            self.entries[source, index] = at
            self.put64(TABLE + index * 8, at)
        for source, index, target in ((224, 7935, 151), (151, 2593, 107)):
            at = ENTRIES + len(aliases) * 0x30
            aliases[('rear', source, index)] = at
            self.cpu.mem_write(at, descriptor(target))
            self.entries[source, index] = at
            self.put64(TABLE + index * 8, at)
        unique = sorted(set(aliases.values()))
        for i, at in enumerate(unique):
            self.put64(UNIQUE + i * 8, at)
        self.cpu.mem_write(b.BANK + 0x68, struct.pack('<HH', len(unique), len(unique)))
        self.put32(b.CONTROLLER + 0x40, 2)
        self.put32(b.CONTROLLER + 0x2C8, 0)
        self.put32(b.CONTROLLER + 0x68, 2)
        self.put32(b.CONTROLLER + 0x548, 7739)
        for slot in (2, 6):
            self.put64(b.RES[slot] + 0x470, b.CLIPS[slot] + 8)
        self.current(982)
        self.select(982, 5170)

    @property
    def token(self):
        return bytes(self.cpu.mem_read(self.code + TOKEN_OFFSET, TOKEN_SIZE))

    def current(self, action):
        self.put64(b.CONTROLLER + 0x58, self.records[action])

    def select(self, source, index):
        self.put64(b.CONTROLLER + 0x90, self.entries[source, index])

    def lookup(self, target, caller=NEXT, output=True, foreign=False):
        before = self.protected_snapshot()
        def setup():
            self.cpu.reg_write(UC_X86_REG_RCX, b.CONTROLLER + (0x1070 if foreign else 0x70))
            self.cpu.reg_write(UC_X86_REG_RBX, target)
            self.cpu.reg_write(UC_X86_REG_RSI, OUTPUT if output else 0)
            self.put64(b.STACK + 0x78, self.module + caller)
            self.put32(OUTPUT, 0xA5A5A5A5)
        # The main helper is called by the native-hook envelope after its
        # saves. +0x80 is that envelope's original return-address contract.
        result = self.invoke(self.code + HELPER_OFFSET, setup)
        after = self.protected_snapshot()
        actor = bytearray(before[b.ACTOR])
        actor[OUTPUT - b.ACTOR:OUTPUT - b.ACTOR + 4] = self.cpu.mem_read(OUTPUT, 4)
        if after[b.ACTOR] != bytes(actor) or any(after[x] != before[x] for x in (b.INPUT, self.data)):
            raise AssertionError('Salt lookup wrote native damage, Ki, item, actor, resources or shared data')
        for pc, at, size in self.writes:
            allowed = (0x20000000 <= at < at + size <= 0x20010000 or
                       self.code + TOKEN_OFFSET <= at < at + size <= self.code + TOKEN_OFFSET + TOKEN_SIZE or
                       output and at == OUTPUT and size == 4)
            if not allowed:
                raise AssertionError(('Unexpected Salt write', hex(pc), hex(at), size))
        return result


class SaltRecoveryPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = source_plan(json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8')))

    def machine(self, **options):
        return SaltMachine(self.plan, **options)

    def arm(self, m):
        self.assertEqual(m.lookup(224, FIRST), m.records[224])
        self.assertEqual(struct.unpack_from('<2I4Q', m.token),
                         (1, 11, b.ACTOR, b.CONTROLLER, m.records[982], b.BANK))

    def common(self, m, target, caller=NEXT, output=True):
        self.assertEqual(m.lookup(target, caller, output), m.records[target])
        self.assertEqual(m.get32(OUTPUT), 2 if output else 0xA5A5A5A5)

    def first205(self, m):
        self.arm(m)
        m.select(224, 7892); self.common(m, 147)
        m.current(147); m.select(147, 2548); self.common(m, 205)
        m.current(205)

    def test_initial_arm_and_qualification_is_read_only_at_three_aslr_layouts(self):
        for layout in b.LAYOUTS:
            m = self.machine(layout=layout)
            self.assertEqual(m.lookup(224, QUALIFICATION, False), 0)
            self.assertEqual(m.token, bytes(TOKEN_SIZE))
            self.arm(m)
            token = m.token
            m.select(224, 7892)
            self.common(m, 147, QUALIFICATION, False)
            self.assertEqual(m.token, token)

    def test_consecutive205_then85_injury_reuses_token_and_exact_two_clip_slots(self):
        for layout in b.LAYOUTS:
            for index in (2599, 2600, 2601):
                m = self.machine(layout=layout); self.first205(m); token = m.token
                m.select(205, 4540); self.common(m, 224, FIRST)
                self.assertEqual(m.token, token)
                m.current(224); m.select(224, 7935); self.common(m, 151)
                m.current(151); m.select(151, index); self.common(m, 85)
                self.assertEqual([e for e in m.events if e[0] == 'clip'],
                                 [('clip', 2, 30002), ('clip', 6, 30002)])
                self.assertEqual(m.token, token)
                m.current(85)
                self.assertEqual(m.lookup(3001), 0)
                self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_existing96_and_rear107_paths_remain_owned(self):
        m = self.machine(); self.arm(m)
        m.current(224); m.select(224, 7932); self.common(m, 152)
        m.current(152); m.select(152, 2634); self.common(m, 96)
        self.assertEqual([e for e in m.events if e[0] == 'clip'],
                         [('clip', 2, 30014), ('clip', 6, 30014)])
        m = self.machine(); self.arm(m)
        m.current(224); m.select(224, 7935); self.common(m, 151)
        m.current(151); m.select(151, 2593); self.common(m, 107)
        self.assertEqual([e for e in m.events if e[0] == 'clip'],
                         [('clip', 2, 30102), ('clip', 2, 30108), ('clip', 6, 30102), ('clip', 6, 30108)])

    def test_shared_q52_requires_current_source_slot_and_no_inactive_rearm(self):
        for action, index in ((147, 2552), (205, 4540), (85, 1715), (96, 1869)):
            m = self.machine(); m.current(action); m.select(action, index)
            self.assertEqual(m.lookup(224), 0)
            self.assertEqual(m.token, bytes(TOKEN_SIZE))
        m = self.machine(); self.first205(m); m.select(982, 5170)
        m.put64(TABLE + 4540 * 8, 0)
        self.assertEqual(m.lookup(224), 0)
        self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_all48_signature_bytes_and_source_range_are_checked(self):
        for target, source, index, current in ((147, 224, 7892, 982), (205, 147, 2548, 147),
                                                (85, 151, 2601, 151), (224, 205, 4540, 205)):
            for offset in range(48):
                m = self.machine(); self.arm(m); m.current(current); m.select(source, index)
                at = m.entries[source, index] + offset
                m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0] ^ 1]))
                self.assertEqual(m.lookup(target), 0, (target, offset))
                self.assertEqual(m.token, bytes(TOKEN_SIZE))
            m = self.machine(); self.arm(m); m.current(current); m.select(source, index)
            m.put32(m.records[source] + 0x80, 0x10001)
            self.assertEqual(m.lookup(target), 0)
            self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_actor_epoch_pending_class_hp_and_owner_fail_closed(self):
        for address, value, width in ((b.ACTOR + 0xEF0, 1, 4), (b.COMP + 0x20, 0, 8),
                                      (b.PROXY, b.ACTOR + 4096, 8), (b.CONTROLLER + 0x40, 0, 4),
                                      (b.CONTROLLER + 0x2C8, 49, 4)):
            m = self.machine(); self.first205(m); m.select(205, 4540)
            m.cpu.mem_write(address, value.to_bytes(width, 'little'))
            self.assertEqual(m.lookup(224), 0); self.assertEqual(m.token, bytes(TOKEN_SIZE))
        m = self.machine(); self.first205(m); m.select(205, 4540)
        m.put32(m.data + 0x1C, 12)
        self.assertEqual(m.lookup(224), 0); self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_clip_bounds_require_both_slots_and_never_fall_back_to_clip_zero(self):
        for slot in (2, 6):
            for invalid in (-1, 1, 0x10000):
                m = self.machine(); self.arm(m); m.current(147); m.select(147, 2548)
                m.motion_results[slot] = invalid
                self.assertEqual(m.lookup(205), 0); self.assertEqual(m.token, bytes(TOKEN_SIZE))
            m = self.machine(); self.arm(m); m.current(147); m.select(147, 2548)
            m.put64(b.CLIPS[slot], 0)
            self.assertEqual(m.lookup(205), 0); self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_foreign_and_qualification_context_cannot_clear_owned_token(self):
        m = self.machine(); self.first205(m); token = m.token
        self.assertEqual(m.lookup(206, QUALIFICATION), 0); self.assertEqual(m.token, token)
        self.assertEqual(m.lookup(224, foreign=True), 0); self.assertEqual(m.token, token)
        self.assertEqual(m.lookup(224, caller=0x1100605), 0); self.assertEqual(m.token, token)
        self.assertEqual(m.lookup(206), 0); self.assertEqual(m.token, bytes(TOKEN_SIZE))

    def test_table_bytes_have_no_relocations_at_three_layouts_and_corruption_rejects(self):
        specs = relocation_specs(self.plan)
        self.assertFalse(any(ROUTES_OFFSET <= f['offset'] < ROUTES_OFFSET + len(ROUTE_BYTES)
                             for f in specs[0]['fixups']))
        for layout in b.LAYOUTS:
            hooks = assemble(self.plan, *layout)
            self.assertEqual(hooks[0]['payload'][ROUTES_OFFSET:], ROUTE_BYTES)
        bad = deepcopy(self.plan)
        prefix, raw = bad['hooks'][0]['asm'].rsplit('.byte ', 1)
        data = raw.strip().split(',')
        data[0] = str(int(data[0]) ^ 1)
        bad['hooks'][0]['asm'] = prefix + '.byte ' + ','.join(data) + '\n'
        with self.assertRaises(ValueError):
            relocation_specs(bad)


class SaltEventPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = source_plan(json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8')))

    def machine(self):
        return SaltMachine(self.plan)

    def test_exact_frame0_to16_catchup_once_and_rejection_disarms(self):
        m = self.machine()
        native = m.module + self.plan['targets']['salt_catchup_native_schedule']
        m.page(native); m.cpu.mem_write(native, b'\xC3')
        # Explicit continuation stub; the game's caller tail is not executed.
        m.cpu.mem_write(m.module + 0x718955, b'\xC3')
        observed = []
        def trace(cpu, address, size, user):
            if address == native:
                observed.append(cpu.reg_read(UC_X86_REG_R9) & 255)
        # Existing bound callback remains registered; add a dedicated observer.
        from unicorn import UC_HOOK_CODE
        m.cpu.hook_add(UC_HOOK_CODE, trace)
        def call(frame, r9=0, step=0x3F800000):
            m.put32(b.CONTROLLER + 0x24, step)
            def setup():
                m.cpu.reg_write(UC_X86_REG_RCX, b.CONTROLLER)
                m.cpu.reg_write(UC_X86_REG_RDX, m.records[982])
                m.cpu.reg_write(UC_X86_REG_R9, r9)
                m.cpu.reg_write(UC_X86_REG_XMM2, frame)
            m.invoke(m.code + EVENT_OFFSET, setup)
        call(0, 1); self.assertEqual(m.get32(m.code + STATE_OFFSET), 1)
        call(0x41800000); self.assertEqual(observed[-1], 1)
        self.assertEqual(m.get32(m.code + STATE_OFFSET), 0)
        call(0x41800000); self.assertEqual(observed[-1], 0)
        call(0, 1); call(0x41800000, step=0x40000000)
        self.assertEqual(observed[-1], 0); self.assertEqual(m.get32(m.code + STATE_OFFSET), 0)


if __name__ == '__main__':
    unittest.main()
