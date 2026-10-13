"""Execute the real public lookup wrapper with colliding action-bank fixtures.

The fallback search is a documented synthetic CPU implementation of bank
order 0 -> 1 -> 2, not a captured game binary. No action-lookup callback
returns the common pointer. Definition/motion/setter boundaries remain stubs;
native casts, events, stock, effects and rendered gameplay are not executed.
"""
from copy import deepcopy
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import load_beta563_plan as load_plan, assemble
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import apply_dung_fan
from hinoenma_four_throwables import apply_four_throwables
from hinoenma_arrow_sloth import apply_arrow_sloth, ITEM_SPECS, ALL_ITEM_SPECS, HELPER_OFFSET
from hinoenma_arrow_sloth_lookup import apply_arrow_sloth_lookup, LOOKUP_OFFSET
import test_arrow_sloth_portable as arrow_tests
import test_harakiri_portable as harakiri_tests
import test_special_items_portable as special_tests
from portable_machine import b
from unicorn.x86_const import *

PRIVATE_VECTOR = b.ACTOR + 0x27000
PRIVATE_RECORDS = {41: b.ACTOR + 0x35000, 42: b.ACTOR + 0x35200}
GROUP = b.ACTOR + 0xB3000
EXTRA = b.ACTOR + 0x36000
FALLBACK_OFFSET = 0xF000 + 0x43F00

# This fixture runs as CPU instructions after all retained public gateways.
# Every result comes from actual fixture bank vectors; neither the private
# collision nor the common result is supplied by a Python lookup callback.
NATIVE_BANK_SEARCH = '''
push rbx
push rsi
push rdi
mov rdi, rcx
mov esi, edx
xor ebx, ebx
fixture_bank:
mov r10, qword ptr [rdi+rbx*8]
test r10, r10
je fixture_next_bank
mov ecx, dword ptr [r10+0x130]
test ecx, ecx
je fixture_next_bank
mov r10, qword ptr [r10+0x128]
test r10, r10
je fixture_next_bank
xor edx, edx
fixture_record:
mov rax, qword ptr [r10+rdx*8]
test rax, rax
je fixture_next_record
cmp byte ptr [rax+0x40], 0
je fixture_next_record
cmp dword ptr [rax], esi
je fixture_found
fixture_next_record:
inc edx
cmp edx, ecx
jb fixture_record
fixture_next_bank:
inc ebx
cmp ebx, 3
jb fixture_bank
xor eax, eax
jmp fixture_return
fixture_found:
test r8, r8
je fixture_return
mov dword ptr [r8], ebx
fixture_return:
pop rdi
pop rsi
pop rbx
ret
'''


class LookupMachine(arrow_tests.ArrowSlothMachine):
    def __init__(self, plan, item=64367, layout=b.LAYOUTS[0]):
        super().__init__(plan, item, layout)
        self.visited = []
        self.fallback_registers = []
        self.native_search_count = 0
        self.cpu.mem_write(b.CURRENT + 0x40, b'\1')
        self.lookup_site = self.module + plan['targets']['signpost_action_lookup']
        self.callbacks.pop(self.lookup_site)
        hook = self.by_name['HE_LadderCommonLookup']
        self.cpu.mem_write(self.lookup_site, hook['patched'])
        native, _ = Ks(KS_ARCH_X86, KS_MODE_64).asm(NATIVE_BANK_SEARCH,
                                                addr=self.lookup_site + 5)
        self.cpu.mem_write(self.lookup_site + 5, bytes(native))
        self.put64(b.OWN_BANK + 0x128, PRIVATE_VECTOR)
        self.put32(b.OWN_BANK + 0x130, 2)
        for index, (action, record) in enumerate(PRIVATE_RECORDS.items()):
            self.put64(PRIVATE_VECTOR + index * 8, record)
            self.put32(record, action)
            self.put64(record + 0x20, record + 0x80)
            self.put64(record + 0x38, b.OWN_BANK)
            self.cpu.mem_write(record + 0x40, b'\1')
            self.put32(record + 0xA0, action + 969)  # Boss 41/1010 and 42/1011.
        self.cpu.mem_write(GROUP - 8, b'\xA7' * 24)
        self.events.clear(); self.writes.clear()

    def trace(self, cpu, address, size, user):
        self.visited.append(address)
        if address == self.code + FALLBACK_OFFSET:
            self.fallback_registers.append({r: cpu.reg_read(r) for r in b.REGISTERS})
        if address == self.lookup_site + 5:
            self.native_search_count += 1
        super().trace(cpu, address, size, user)

    def phase(self, name, pending=None):
        if name == 'idle':
            self.put64(b.CONTROLLER + 0x58, b.CURRENT)
        elif name == 'entry':
            self.put64(b.CONTROLLER + 0x58, self.lookup_results[172])
        elif name == 'cast':
            self.put64(b.CONTROLLER + 0x58, self.lookup_results[self.action])
        elif name == 'boss':
            self.put64(b.CONTROLLER + 0x58, PRIVATE_RECORDS[self.action])
        else:
            raise ValueError(name)
        if pending is not None:
            self.cpu.mem_write(b.CONTROLLER + 0x555, bytes([pending]))

    def lookup(self, action=None, group=GROUP, controller=None):
        saved = {}
        def setup():
            self.cpu.reg_write(UC_X86_REG_RCX, (controller or b.CONTROLLER) + 0x70)
            self.cpu.reg_write(UC_X86_REG_EDX, self.action if action is None else action)
            self.cpu.reg_write(UC_X86_REG_R8, group)
            saved.update({r: self.cpu.reg_read(r) for r in b.REGISTERS})
        self.visited.clear(); self.fallback_registers.clear(); self.native_search_count = 0
        result = self.invoke(self.lookup_site, setup)
        return result, saved


class ArrowSlothLookupPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = apply_arrow_sloth(apply_four_throwables(apply_dung_fan(apply_harakiri(load_plan()))))
        cls.plan = apply_arrow_sloth_lookup(cls.old)

    def checked_lookup(self, m, accepted, group=GROUP, action=None, controller=None):
        before = m.protected_snapshot()
        result, registers = m.lookup(action=action, group=group, controller=controller)
        expected = m.lookup_results[m.action] if accepted else PRIVATE_RECORDS[m.action if action is None else action]
        self.assertEqual(result, expected)
        if accepted:
            registers[UC_X86_REG_RSP] = b.STACK
            registers[UC_X86_REG_RAX] = expected
            self.assertEqual({r: m.cpu.reg_read(r) for r in b.REGISTERS}, registers)
            self.assertFalse(m.fallback_registers)
            self.assertEqual(m.native_search_count, 0)
        else:
            # The wrapper restores every input before entering the complete
            # retained chain; that chain and the search may clobber volatiles.
            self.assertTrue(m.fallback_registers)
            self.assertEqual(m.fallback_registers[0], registers)
            self.assertEqual(m.native_search_count, 1)
        expected_snapshot = deepcopy(before)
        if group:
            actor = bytearray(expected_snapshot[b.ACTOR])
            struct.pack_into('<I', actor, group - b.ACTOR, 2 if accepted else 1)
            expected_snapshot[b.ACTOR] = bytes(actor)
        self.assertEqual(m.protected_snapshot(), expected_snapshot)
        self.assertTrue(all(0x20000000 <= at < 0x20010000 or (group and at == group and size == 4)
                            for _, at, size in m.writes))
        return result

    def test_old_collision_returns_boss_and_blocks_preflight_new_real_wrapper_dispatches172(self):
        for row in ITEM_SPECS:
            m = LookupMachine(self.old, row[0]); result, _ = m.lookup()
            self.assertEqual(result, PRIVATE_RECORDS[row[7]])
            self.assertEqual(m.get32(GROUP), 1)
            self.assertEqual(m.get32(result + 0xA0), row[7] + 969)
            self.assertEqual(m.native_search_count, 1)
            m = LookupMachine(self.old, row[0]); m.invoke(m.code + HELPER_OFFSET)
            self.assertFalse(any(e[0] == 'dispatch' for e in m.events))
            m = LookupMachine(self.plan, row[0])
            arrow_tests.ArrowSlothPortableTests().checked_entry(m, True)
            self.assertIn(m.code + LOOKUP_OFFSET, m.visited)
            self.assertEqual([e for e in m.events if e[0] == 'dispatch'],
                             [('dispatch', b.CONTROLLER, 172)])

    def test_idle_entry_and_matching_cast_both_templates_three_layouts_full_abi(self):
        for layout in b.LAYOUTS:
            for template in (0x58E5E, 0x51BE1):
                for row in ITEM_SPECS:
                    for phase, pending in (('idle', 1), ('entry', 0), ('entry', 1), ('cast', 0)):
                        with self.subTest(layout=layout, template=template, item=row[0], phase=phase, pending=pending):
                            m = LookupMachine(self.plan, row[0], layout)
                            for at in (b.ACTOR, b.META, m.data + 4): m.put32(at, template)
                            m.phase(phase, pending)
                            self.checked_lookup(m, True)
        for row in ITEM_SPECS:
            self.checked_lookup(LookupMachine(self.plan, row[0]), True, group=0)

    def test_private_boss_actions_idle_cancel_and_unrelated_npc_are_not_hijacked(self):
        for row in ITEM_SPECS:
            for phase, pending in (('boss', 0), ('boss', 1), ('idle', 0)):
                m = LookupMachine(self.plan, row[0]); m.phase(phase, pending)
                self.checked_lookup(m, False)
            for at, value, width in ((b.ACTOR + 4, 0x20000, 4), (b.META + 0xC, 0, 4),
                (b.ACTOR + 0xEF0, 1, 4), (b.PROXY + 8, b.CONTROLLER + 0x100, 8),
                (b.COMP + 0x20, 0, 8), (b.CONTROLLER + 0x570, 1, 1)):
                m = LookupMachine(self.plan, row[0])
                m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                self.checked_lookup(m, False)
            m = LookupMachine(self.plan, row[0])
            self.checked_lookup(m, False, action=42 if row[7] == 41 else 41)
            # A different caller's bank-array address must never borrow the
            # captured player's common cast, even when bank records coincide.
            m = LookupMachine(self.plan, row[0]); npc_ctl = b.ACTOR + 0x37000
            m.put64(npc_ctl + 0x78, b.OWN_BANK); m.put64(npc_ctl + 0x80, b.BANK)
            self.checked_lookup(m, False, controller=npc_ctl)

    def test_exact_definitions_request_and_actor_identity_fail_closed(self):
        for row in ITEM_SPECS:
            for offset, width in ((0, 4), (4, 1), (5, 1), (0x104, 4), (0x10C, 4),
                                  (0x110, 4), (0x114, 4), (0x118, 4), (0x11C, 4)):
                m = LookupMachine(self.plan, row[0]); at = special_tests.DEFINITION + offset
                old = int.from_bytes(m.cpu.mem_read(at, width), 'little')
                m.cpu.mem_write(at, (old ^ 1).to_bytes(width, 'little'))
                self.checked_lookup(m, False)
            for at, value, width in ((b.CONTROLLER + 0x548, 999, 4),
                (b.CONTROLLER + 0x54C, 99, 4), (b.CONTROLLER + 0x550, 2, 4),
                (b.CONTROLLER + 0x555, 2, 1), (b.CONTROLLER + 0x558, 1, 8)):
                m = LookupMachine(self.plan, row[0])
                m.cpu.mem_write(at, value.to_bytes(width, 'little'))
                self.checked_lookup(m, False)
            for which in ('native', 'recorded', 'epoch'):
                m = LookupMachine(self.plan, row[0])
                if which == 'native': m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                elif which == 'recorded': m.put64(m.data + 0x10, b.ACTOR + 0x100)
                else: m.put32(m.data + 0x1C, 0)
                self.checked_lookup(m, False)

    def test_missing_motion_bad_schedule_duplicate_record_and_wrong_bank_fail_closed(self):
        for row in ITEM_SPECS:
            for kind in ('missing', 'wrong-owner', 'duplicate', 'schedule', 'descriptor', 'slot2', 'slot6'):
                with self.subTest(item=row[0], mutation=kind):
                    m = LookupMachine(self.plan, row[0]); record = m.lookup_results[row[7]]
                    if kind == 'missing': m.put64(b.VECTOR + 8, 0)
                    elif kind == 'wrong-owner': m.put64(record + 0x38, b.OWN_BANK)
                    elif kind == 'duplicate':
                        m.cpu.mem_write(EXTRA, bytes(m.cpu.mem_read(record, 0x100)))
                        m.put64(b.VECTOR + 16, EXTRA); m.put32(b.BANK + 0x130, 3)
                    elif kind == 'schedule': m.put32(record + 0xC0, 0)
                    elif kind == 'descriptor':
                        m.cpu.mem_write(b.ACTOR + 0xA1000 + 17 * 0x80 + 0x17, b'\xFF')
                    else: m.put64(b.CLIPS[2 if kind == 'slot2' else 6], 0)
                    self.checked_lookup(m, False)
            # Native vectors may contain null slots; uniqueness concerns only
            # enabled matching records, not unrelated holes.
            m = LookupMachine(self.plan, row[0]); m.put32(b.BANK + 0x130, 3)
            m.put64(b.VECTOR + 16, 0)
            self.checked_lookup(m, True)

    def test_epoch_owner_and_request_changes_during_resource_lookup_reject(self):
        for row in ITEM_SPECS:
            for kind in ('epoch', 'owner', 'request', 'cancel', 'definition',
                         'schedule', 'duplicate', 'record-owner'):
                m = LookupMachine(self.plan, row[0])
                def mutate(m, name):
                    if name != 'clip' or m.events[-1][1] != 6: return
                    if kind == 'epoch': m.put32(m.data + 0x1C, 12)
                    elif kind == 'owner': m.put64(m.module + self.plan['targets']['player_slot'], b.ACTOR + 0x100)
                    elif kind == 'request': m.put32(b.CONTROLLER + 0x548, 999)
                    elif kind == 'cancel': m.cpu.mem_write(b.CONTROLLER + 0x555, b'\0')
                    elif kind == 'definition': m.put32(special_tests.DEFINITION + 0x104, 0)
                    elif kind == 'schedule': m.put32(m.lookup_results[m.action] + 0xC0, 0)
                    elif kind == 'record-owner': m.put64(m.lookup_results[m.action] + 0x38, b.OWN_BANK)
                    else:
                        m.cpu.mem_write(EXTRA, bytes(m.cpu.mem_read(m.lookup_results[m.action], 0x100)))
                        m.put64(b.VECTOR + 16, EXTRA); m.put32(b.BANK + 0x130, 3)
                m.mutate_on_call = mutate
                result, _ = m.lookup()
                self.assertEqual(result, PRIVATE_RECORDS[row[7]])
                self.assertTrue(m.fallback_registers)

    def test_unrelated_action_ids_keep_full_fallback_behavior_and_registers(self):
        for action in (0, 17, 40, 43, 172, 165, 609, 1225, 9999):
            outcomes = []
            for plan in (self.old, self.plan):
                m = LookupMachine(plan)
                result, _ = m.lookup(action=action)
                outcomes.append((result, m.get32(GROUP), m.protected_snapshot(),
                                 {r: m.cpu.reg_read(r) for r in b.REGISTERS}))
                self.assertEqual(m.native_search_count, 1)
                self.assertIn(m.code + FALLBACK_OFFSET, m.visited)
            self.assertEqual(*outcomes, action)

    def test_existing_nine_item_entries_and_harakiri_keep_routes(self):
        for row in ALL_ITEM_SPECS:
            m = LookupMachine(self.plan, row[0])
            arrow_tests.ArrowSlothPortableTests().checked_entry(m, True)
        for row in special_tests.ITEM_SPECS:
            arrow_tests.ArrowSlothPortableTests().checked_entry(
                special_tests.ItemMachine(self.plan, row[0]), True, special_tests.HELPER_OFFSET)
        checker = harakiri_tests.HarakiriTests()
        for layout in b.LAYOUTS:
            checker.check(harakiri_tests.GateMachine(self.plan, layout), True)

    def test_only_two_payloads_change_all_native_sites_and_fixed_old_lookup_tail_preserved(self):
        saved = deepcopy(self.old)
        self.assertEqual(apply_arrow_sloth_lookup(self.old), self.plan)
        self.assertEqual(self.old, saved)
        for layout in b.LAYOUTS:
            old, new = assemble(self.old, *layout), assemble(self.plan, *layout)
            self.assertEqual([a['name'] for a, c in zip(old, new) if a['payload'] != c['payload']],
                             ['HE_LivingWeaponDigitNine', 'HE_LadderCommonLookup'])
            for a, c in zip(old, new):
                for field in ('name', 'site', 'target', 'original', 'patched', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])
                if a['name'] == 'HE_LadderCommonLookup':
                    self.assertEqual(a['payload'][5:], c['payload'][5:])
                elif a['name'] == 'HE_LivingWeaponDigitNine':
                    self.assertEqual(a['payload'], c['payload'][:len(a['payload'])])
                    self.assertLessEqual(len(c['payload']), c['code_capacity'])
        with self.assertRaises(ValueError): apply_arrow_sloth_lookup(self.plan)


if __name__ == '__main__':
    unittest.main()
