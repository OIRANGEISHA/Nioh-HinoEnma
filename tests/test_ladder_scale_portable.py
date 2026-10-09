"""Portable ladder CPU regressions using constructed records only.

No game executable, resources, private snapshots, native-code excerpts or
process access are required. The generated public payloads run in Unicorn;
all memory and input state below is synthetic. These checks cover ownership,
clip selection, register preservation and bounded stack writes, not gameplay.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]
from build_profile import assemble, load_plan, source_plan_v059
from hinoenma_ladder_scale import (ALLOCATION_SIZE, CODE_CAPACITY, CODE_OFFSETS,
    DATA_OFFSET, NATIVE_SIGNATURES, PLAYER_SLOT_RVA, PROTECTED_DATA_PAGES, apply_ladder_scale)
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_MEM
from capstone.x86_const import X86_REG_RSP
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
import unicorn.x86_const as reg

PLAN = load_plan()
INTEGRATED = PLAN
BASELINE = source_plan_v059(PLAN)
BASELINE['allocation_size'] = 0x19000
MODULE, CODE, PRODUCTION = 0x140000000, 0x144000000, 0x144000000
DATA, PROD = CODE + DATA_OFFSET, PRODUCTION + 0xF000
ACTOR, META, MOTION, PROXY = 0x30000000, 0x30004000, 0x30006000, 0x30008000
CTL, RECORD, PARAMS = 0x3000A000, 0x3000B000, 0x3000C000
COMMON, OBJECT, INFO, LAYER = 0x3000D000, 0x3000E000, 0x3000F000, 0x30010000
OTHER = 0x30012000
STACK = 0x20008000
GPRS = tuple(getattr(reg, 'UC_X86_REG_' + name) for name in (
    'RAX', 'RBX', 'RCX', 'RDX', 'RBP', 'RSI', 'RDI', 'R8', 'R9', 'R10',
    'R11', 'R12', 'R13', 'R14', 'R15', 'RSP'))
XMMS = tuple(getattr(reg, 'UC_X86_REG_XMM' + str(index)) for index in range(16))
REGISTERS = GPRS + XMMS + (reg.UC_X86_REG_EFLAGS, reg.UC_X86_REG_MXCSR)
ORIGINAL_SCALE = struct.unpack('<I', struct.pack('<f', 0.733))[0]
PAYLOADS = assemble(PLAN, MODULE, CODE)[55:]
PENDING, PENDING_PARAMS = ACTOR+0x22000, ACTOR+0x23000

class BaseMachine:
    def __init__(self, index=0, *, stack_offset=0):
        self.index = index
        self.plan = PLAN
        self.hook = PAYLOADS[index]
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_64)
        for address, size in ((MODULE, 0xA00000), (MODULE + 0x18A0000, 0x1000),
                (CODE, ALLOCATION_SIZE),
                (ACTOR, 0x40000), (0x20000000, 0x10000)):
            self.cpu.mem_map(address, size)
        self.cpu.mem_write(self.hook['target'], self.hook['payload'])
        self.put32(PROD + 4, 0x58E5E)
        self.put64(PROD + 0x10, ACTOR)
        self.put64(MODULE + PLAYER_SLOT_RVA, ACTOR)
        self.put32(ACTOR, 0x58E5E)
        self.put32(ACTOR + 4, 0x10000)
        self.put64(ACTOR + 0x38, MOTION)
        self.put64(ACTOR + 0xE90, META)
        self.put32(META + 0xC, 1)
        self.put64(ACTOR + 0x230, PROXY)
        self.put64(PROXY, ACTOR)
        self.put64(PROXY + 8, CTL)
        self.put64(CTL + 0x50, ACTOR)
        self.put64(CTL + 0x58, RECORD)
        self.put64(CTL + 0x80, COMMON)
        self.put64(CTL + 0x510, OBJECT)
        self.put64(CTL + 0x528, INFO)
        self.put64(RECORD + 0x20, PARAMS)
        self.put64(RECORD + 0x38, COMMON)
        self.put8(RECORD + 0x40, 1)
        self.action(57, 251)
        self.put32(PARAMS, 0x800)
        self.put64(MOTION, ACTOR)
        self.put32(MOTION + 0x320, ORIGINAL_SCALE)
        self.put32(MOTION + 0x328, 0x3F123456)
        self.put32(OBJECT + 4, 0x10002)
        self.put64(INFO, OBJECT)
        self.put8(INFO + 8, 1)
        self.put8(INFO + 9, 1)
        self.put8(INFO + 0xA, 1)
        self.put32(INFO + 0x48, 8)
        self.put32(INFO + 0x4C, 10)
        self.put32(INFO + 0x50, 20)
        self.put8(LAYER + 0x28, 1)
        for ordinal, register in enumerate(GPRS):
            self.cpu.reg_write(register, 0xBEEF0000 + ordinal * 17)
        for ordinal, register in enumerate(XMMS):
            self.cpu.reg_write(register, 0xBBAA99887766554433221100FFEEDD00 + ordinal)
        owner_register = getattr(reg, 'UC_X86_REG_' + NATIVE_SIGNATURES[index][3].upper())
        self.cpu.reg_write(owner_register, MOTION)
        self.cpu.reg_write(reg.UC_X86_REG_R9, LAYER)
        self.cpu.reg_write(reg.UC_X86_REG_RSP, STACK + stack_offset)
        self.cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0xAD7)
        self.cpu.reg_write(reg.UC_X86_REG_MXCSR, 0x1F80)
        self.stop = None
        self.writes = []
        self.cpu.hook_add(UC_HOOK_CODE, self.trace)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE, self.write)

    def put8(self, at, value):
        self.cpu.mem_write(at, bytes([value]))

    def put32(self, at, value):
        self.cpu.mem_write(at, struct.pack('<I', value & 0xFFFFFFFF))

    def put64(self, at, value):
        self.cpu.mem_write(at, struct.pack('<Q', value & 0xFFFFFFFFFFFFFFFF))

    def action(self, action, motion):
        self.put32(RECORD, action)
        self.put32(PARAMS + 0x20, motion)
        self.put32(MOTION + 0xEC, motion)

    def trace(self, cpu, address, size, _):
        if address == self.hook['site'] + self.hook['length']:
            self.stop = address
            cpu.emu_stop()

    def write(self, cpu, access, address, size, value, _):
        self.writes.append((address, size, value))

    def registers(self):
        return {register: self.cpu.reg_read(register) for register in REGISTERS}

    def run(self):
        self.cpu.emu_start(self.hook['target'], 0, count=500)


class Machine(BaseMachine):
    def __init__(self, index=0, *, stack_offset=0):
        self.stack_offset = stack_offset
        super().__init__(index, stack_offset=stack_offset)
        self.plan = PLAN
        self.hook = PAYLOADS[index]
        self.cpu.mem_write(self.hook['target'], self.hook['payload'])
        self.put32(MOTION + 0x48, 2)
        self.put32(STACK + self.stack_offset + 0x20, 251)

    def action(self, action, motion):
        super().action(action, motion)
        self.put32(STACK + self.stack_offset + 0x20, motion)

    def pending(self, action=58, motion=252):
        self.put64(CTL + 0x60, PENDING)
        self.put32(PENDING, action)
        self.put64(PENDING + 0x20, PENDING_PARAMS)
        self.put64(PENDING + 0x38, COMMON)
        self.put8(PENDING + 0x40, 0)
        self.put32(PENDING_PARAMS, 0x800)
        self.put32(PENDING_PARAMS + 0x20, motion)
        self.put32(STACK + self.stack_offset + 0x20, motion)


class LadderScaleTests(unittest.TestCase):
    comparisons = 0
    baseline_payload_comparisons = 0
    baseline_layouts = []

    def check(self, machine, replaced=False):
        expected = machine.registers()
        destination = getattr(reg, 'UC_X86_REG_' + NATIVE_SIGNATURES[machine.index][4].upper())
        expected[destination] = 0x3F800000 if replaced else ORIGINAL_SCALE
        native = bytes(machine.cpu.mem_read(ACTOR, 0x40000))
        production = bytes(machine.cpu.mem_read(PRODUCTION, ALLOCATION_SIZE))
        slot = bytes(machine.cpu.mem_read(MODULE + PLAYER_SLOT_RVA, 8))
        private = bytes(machine.cpu.mem_read(DATA, 0x1000))
        stack_at = machine.cpu.reg_read(reg.UC_X86_REG_RSP)
        stack_above = bytes(machine.cpu.mem_read(stack_at, 0x100))
        machine.run()
        self.assertEqual(machine.stop, machine.hook['site'] + machine.hook['length'])
        self.assertEqual(machine.registers(), expected)
        self.assertEqual(bytes(machine.cpu.mem_read(ACTOR, 0x40000)), native)
        self.assertEqual(bytes(machine.cpu.mem_read(PRODUCTION, ALLOCATION_SIZE)), production)
        self.assertEqual(bytes(machine.cpu.mem_read(MODULE + PLAYER_SLOT_RVA, 8)), slot)
        self.assertEqual(bytes(machine.cpu.mem_read(DATA, 0x1000)), private)
        self.assertEqual(bytes(machine.cpu.mem_read(stack_at, 0x100)), stack_above)
        self.assertTrue(all(0x20000000 <= address < stack_at for address, _, _ in machine.writes),
                        'Integrated hooks may only spill below the native stack pointer')
        type(self).comparisons += 1


    def each(self, mutator, replaced=False):
        for index in range(3):
            with self.subTest(index=index):
                machine = Machine(index)
                mutator(machine)
                self.check(machine, replaced)


    def test_native_hino_ladder_preserves_all_registers_flags_stack_and_other_simd(self):
        self.each(lambda machine: None, True)


    def test_second_hino_template_remains_scoped(self):
        self.each(lambda m: (m.put32(ACTOR, 0x51BE1), m.put32(PROD + 4, 0x51BE1)), True)


    def test_william_template_keeps_native_scale(self):
        self.each(lambda m: (m.put32(ACTOR, 0x64), m.put32(PROD + 4, 0x64)))


    def test_enemy_and_npc_instances_keep_native_scale(self):
        for identity in (0x20000, 0x10001, 0, 0x30000):
            self.each(lambda m: m.put32(ACTOR + 4, identity))


    def test_capture_native_slot_and_loaded_template_bindings_cannot_diverge(self):
        for at, value, size in ((PROD + 0x10, OTHER, 8),
                (MODULE + PLAYER_SLOT_RVA, OTHER, 8), (PROD + 4, 0, 4),
                (PROD + 4, 0x51BE1, 4)):
            self.each(lambda m: (m.put64 if size == 8 else m.put32)(at, value))


    def test_metadata_role_and_live_native_state_required(self):
        for at, value in ((META + 0xC, 0), (META + 0xC, 2), (ACTOR + 0xEF0, 1)):
            self.each(lambda m: m.put32(at, value))


    def test_motion_owner_and_actor_motion_identity_required(self):
        for at, value in ((ACTOR + 0x38, OTHER), (MOTION, OTHER)):
            self.each(lambda m: m.put64(at, value))


    def test_proxy_and_controller_double_ownership_required(self):
        for at, value in ((PROXY, OTHER), (PROXY + 8, 0), (CTL + 0x50, OTHER)):
            self.each(lambda m: m.put64(at, value))


    def test_owned_proxy_controller_is_valid_without_global_controller_assumption(self):
        def mutate(m):
            # The native controller can live at another address, provided every
            # owner link is coherent. There is no hardcoded fixture controller.
            m.cpu.mem_write(OTHER, bytes(m.cpu.mem_read(CTL, 0x600)))
            m.put64(PROXY + 8, OTHER)
        self.each(mutate, True)


    def test_common_bank_record_activity_flags_and_motion_must_match(self):
        for at, value, size in ((RECORD + 0x38, OTHER, 8), (CTL + 0x80, 0, 8),
                (RECORD + 0x40, 0, 1), (PARAMS, 0, 4),
                (PARAMS + 0x20, 328, 4)):
            self.each(lambda m: {1:m.put8, 4:m.put32, 8:m.put64}[size](at, value))
        for index in range(3):
            machine = Machine(index)
            machine.put32(MOTION + 0xEC, 252)
            self.check(machine, index == 0)


    def test_extra_native_flags_preserved_when_ladder_bit_is_set(self):
        self.each(lambda m: m.put32(PARAMS, 0x1801), True)


    def test_every_ladder_common_record_and_real_motion_boundary(self):
        for action in range(56, 71):
            for motion in (250, 251, 267):
                self.each(lambda m: m.action(action, motion), True)


    def test_battle_drop_idle_and_other_common_records_keep_native_scale(self):
        for action in (0, 55, 71, 170, 180, 208, 209, 328, 1005, 857):
            self.each(lambda m: m.action(action, 251))
        for motion in (0, 249, 268, 328, 1101, 0xFFFFFFFF):
            self.each(lambda m: m.action(57, motion))


    def test_up_and_down_request_with_ladder_flag_boundaries(self):
        for request in (8, 9):
            for flag9 in (0, 1):
                for flag_a in (0, 1):
                    self.each(lambda m: (m.put32(INFO + 0x48, request),
                        m.put8(INFO + 9, flag9), m.put8(INFO + 0xA, flag_a)), True)


    def test_wrong_request_object_type_and_info_owner_never_replace(self):
        for request in (0, 1, 7, 10, 0xFFFFFFFF):
            self.each(lambda m: m.put32(INFO + 0x48, request))
        self.each(lambda m: m.put64(INFO, OTHER))
        for object_type in (0, 1, 3, 0xFFFF):
            self.each(lambda m: m.put32(OBJECT + 4, object_type))


    def test_invalid_ladder_active_started_and_ready_flags(self):
        for offset, values in ((8, (0, 2, 255)), (9, (2, 255)), (0xA, (2, 255))):
            for value in values:
                self.each(lambda m: m.put8(INFO + offset, value))


    def test_real_ladder_bone_bounds(self):
        for offset in (0x4C, 0x50):
            for value in (1, 0x1000):
                self.each(lambda m: m.put32(INFO + offset, value), True)
            for value in (0, 0x1001, 0xFFFFFFFF):
                self.each(lambda m: m.put32(INFO + offset, value))


    def test_cleared_object_or_info_only_allows_current_verified_exit(self):
        for action in (61, 62, 66):
            for missing in ((CTL + 0x510,), (CTL + 0x528,), (CTL + 0x510, CTL + 0x528)):
                self.each(lambda m: (m.action(action, 257),
                    [m.put64(at, 0) for at in missing]), True)


    def test_cleared_entry_climb_drop_and_unproven_exit70_keep_native(self):
        for action in (56, 57, 58, 60, 63, 64, 65, 67, 68, 69, 70):
            self.each(lambda m: (m.action(action, 257), m.put64(CTL + 0x528, 0)))


    def test_present_but_bad_binding_cannot_take_exit_exception(self):
        for action in (61, 62, 66):
            self.each(lambda m: (m.action(action, 257), m.put64(INFO, OTHER)))
            self.each(lambda m: (m.action(action, 257), m.put32(INFO + 0x48, 7)))


    def test_cleared_exit_still_requires_current_bank_motion_and_ownership(self):
        for at, value, size in ((RECORD + 0x38, OTHER, 8), (PARAMS, 0, 4),
                (CTL + 0x50, OTHER, 8)):
            self.each(lambda m: (m.action(62, 257), m.put64(CTL + 0x528, 0),
                (m.put64 if size == 8 else m.put32)(at, value)))
        machine = Machine(0)
        machine.action(62, 257)
        machine.put64(CTL + 0x528, 0)
        machine.put32(STACK + 0x20, 256)
        self.check(machine)


    def test_render_only_common_blend_layer_and_never_boss_layer(self):
        for value in (0, 1, 2, 255):
            m = Machine(2)
            m.put8(LAYER + 0x28, value)
            self.check(m, value != 0)
        for index in (0, 1):
            m = Machine(index)
            m.put8(LAYER + 0x28, 0)
            self.check(m, True)


    def test_added_pointer_checks_short_circuit_null_low_and_noncanonical_values(self):
        for at in (PROD + 0x10, ACTOR + 0xE90, ACTOR + 0x230,
                PROXY + 8, CTL + 0x58, RECORD + 0x20, CTL + 0x510, CTL + 0x528):
            for value in (0, 1, 0xFFFF, 0x800000000000, 0xFFFFFFFFFFFFFFFF):
                self.each(lambda m: m.put64(at, value))
        for value in (0, 1, 0xFFFF, 0x800000000000):
            m = Machine(2)
            m.cpu.reg_write(reg.UC_X86_REG_R9, value)
            self.check(m)


    def test_stack_alignment_independent_without_win64_calls(self):
        for index in range(3):
            for offset in (0, 8, 3, 15):
                self.check(Machine(index, stack_offset=offset), True)


    def test_native_scalar_nan_and_other_scale_bits_replayed_exactly(self):
        for bits in (0, 0x80000000, 0x7FC12345, 0x3F800000, 0x40400000):
            for index in range(3):
                machine = Machine(index)
                machine.put32(MOTION + 0x320, bits)
                machine.put32(PROD + 4, 0)
                expected = machine.registers()
                destination = getattr(reg, 'UC_X86_REG_' + NATIVE_SIGNATURES[index][4].upper())
                expected[destination] = bits
                native = bytes(machine.cpu.mem_read(ACTOR, 0x40000))
                machine.run()
                self.assertEqual(machine.registers(), expected)
                self.assertEqual(bytes(machine.cpu.mem_read(ACTOR, 0x40000)), native)
                self.assertEqual(machine.writes[-1][0], STACK - 64)
                type(self).comparisons += 1


    def test_sampler_accepts_current_exact_sample_when_raw_motion_is_still_old(self):
        for motion in (0, 250, 252, 328, 1031, 0xFFFFFFFF):
            machine = Machine(0)
            machine.put32(MOTION + 0xEC, motion)
            self.check(machine, True)


    def test_sampler_requires_common_resource_bank2(self):
        for bank in (0, 1, 3, 0xFFFFFFFF):
            machine = Machine(0)
            machine.put32(MOTION + 0x48, bank)
            self.check(machine)
        for index in (1, 2):
            machine = Machine(index)
            machine.put32(MOTION + 0x48, 0)
            self.check(machine, True)


    def test_requested_sample_clip_boundaries_and_current_match_are_exact(self):
        for clip in (0, 249, 250, 252, 268, 328, 0xFFFFFFFF):
            machine = Machine(0)
            machine.put32(STACK + 0x20, clip)
            self.check(machine)


    def test_precommit_pending_entry_step_and_exit_match_native_requested_clip(self):
        for action, clip in ((56, 250), (58, 252), (60, 254), (61, 255),
                             (62, 256), (63, 257), (64, 258), (66, 260)):
            machine = Machine(0)
            machine.action(0, 1031)
            machine.pending(action, clip)
            self.check(machine, True)


    def test_pending_match_does_not_depend_on_current_record_existence(self):
        for current in (0, 1, 0x800000000000):
            machine = Machine(0)
            machine.put64(CTL + 0x58, current)
            machine.pending()
            self.check(machine, True)


    def test_pending_requires_valid_common_enabled_ladder_params_and_sample(self):
        for at, value, size in ((PENDING + 0x38, OTHER, 8),
                (PENDING + 0x40, 2, 1), (PENDING_PARAMS, 0, 4),
                (PENDING_PARAMS + 0x20, 253, 4), (PENDING, 55, 4), (PENDING, 71, 4),
                (PENDING + 0x20, 0, 8), (CTL + 0x60, 0, 8)):
            machine = Machine(0)
            machine.pending()
            {1:machine.put8, 4:machine.put32, 8:machine.put64}[size](at, value)
            self.check(machine)


    def test_pending_precommit_requires_live_info_and_cannot_use_cleared_exit_exception(self):
        for action in (56, 58, 61, 62, 66):
            for missing in (CTL + 0x510, CTL + 0x528):
                machine = Machine(0)
                machine.pending(action, 257)
                machine.put64(missing, 0)
                self.check(machine)


    def test_pending_before_commit_accepts_inactive_or_active_native_record(self):
        for active in (0, 1):
            machine = Machine(0)
            machine.pending()
            machine.put8(PENDING + 0x40, active)
            self.check(machine, True)


    def test_inactive_pending_matches_sample_with_old_raw_motion0_or250(self):
        for old_motion in (0, 250):
            machine = Machine(0)
            machine.action(56, old_motion)
            machine.pending(58, 252)
            machine.put8(PENDING + 0x40, 0)
            self.check(machine, True)


    def test_pending_tampered_pointer_short_circuits_before_added_dereference(self):
        for at in (CTL + 0x60, PENDING + 0x20):
            for value in (0, 1, 0xFFFF, 0x800000000000, 0xFFFFFFFFFFFFFFFF):
                machine = Machine(0)
                machine.pending()
                machine.put64(at, value)
                self.check(machine)


    def test_pending_precommit_keeps_full_info_type_owner_and_flag_guards(self):
        for at, value, size in ((INFO, OTHER, 8), (OBJECT + 4, 1, 4),
                (INFO + 8, 0, 1), (INFO + 9, 2, 1), (INFO + 0xA, 2, 1),
                (INFO + 0x48, 7, 4), (INFO + 0x4C, 0, 4),
                (INFO + 0x50, 0x1001, 4)):
            machine = Machine(0)
            machine.pending()
            {1:machine.put8, 4:machine.put32, 8:machine.put64}[size](at, value)
            self.check(machine)


    def test_current_exit_exact_sample_may_continue_after_object_or_info_clear(self):
        for action in (61, 62, 66):
            machine = Machine(0)
            machine.action(action, 257)
            machine.put32(MOTION + 0xEC, 250)
            machine.put64(CTL + 0x528, 0)
            self.check(machine, True)


    def test_capture_replays_native_sign_extension_rbp_and_preserves_all_other_state(self):
        for native_bank in (0, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            machine = BaseMachine(0)
            machine.plan = PLAN
            machine.hook = PAYLOADS[3]
            machine.cpu.mem_write(machine.hook['target'], machine.hook['payload'])
            machine.cpu.reg_write(reg.UC_X86_REG_RCX, MOTION)
            machine.cpu.reg_write(reg.UC_X86_REG_R8, 0xFEDCBA98000000FB)
            machine.put32(MOTION + 0x50, native_bank)
            machine.put32(STACK + 0x20, 0xCCCCCCCC)
            expected = machine.registers()
            expected[reg.UC_X86_REG_R10] = native_bank if native_bank < 0x80000000 else native_bank | 0xFFFFFFFF00000000
            expected[reg.UC_X86_REG_RBP] = expected[reg.UC_X86_REG_R9]
            native = bytes(machine.cpu.mem_read(ACTOR, 0x40000))
            production = bytes(machine.cpu.mem_read(PRODUCTION, 0x10000))
            stack = bytearray(machine.cpu.mem_read(STACK, 0x100))
            struct.pack_into('<I', stack, 0x20, 251)
            machine.run()
            self.assertEqual(machine.registers(), expected)
            self.assertEqual(bytes(machine.cpu.mem_read(ACTOR, 0x40000)), native)
            self.assertEqual(bytes(machine.cpu.mem_read(PRODUCTION, 0x10000)), production)
            self.assertEqual(bytes(machine.cpu.mem_read(STACK, 0x100)), bytes(stack))
            self.assertEqual(machine.writes, [(STACK + 0x20, 4, 251)])
            self.assertEqual(machine.stop, machine.hook['site'] + 7)
            type(self).comparisons += 1


    def test_capture_then_sampler_uses_exact_stack_clip_when_current_changed_later(self):
        machine = Machine(0)
        capture = PAYLOADS[3]
        machine.cpu.mem_write(capture['target'], capture['payload'])
        machine.put32(STACK + 0x20, 0)
        machine.cpu.reg_write(reg.UC_X86_REG_RCX, MOTION)
        machine.cpu.reg_write(reg.UC_X86_REG_R8, 252)
        original_hook = machine.hook
        machine.hook = capture
        machine.run()
        self.assertEqual(struct.unpack('<I', machine.cpu.mem_read(STACK + 0x20, 4))[0], 252)
        machine.hook = original_hook
        machine.stop = None
        machine.writes = []
        machine.cpu.reg_write(reg.UC_X86_REG_RDI, MOTION)
        machine.put32(MOTION + 0xEC, 1031)
        machine.pending(58, 252)
        self.check(machine, True)


    def test_integration_is_pure_and_keeps_every_original_specification_and_target(self):
        incoming = deepcopy(BASELINE)
        before = deepcopy(incoming)
        plan = apply_ladder_scale(incoming)
        self.assertEqual(incoming, before)
        self.assertEqual(plan['hooks'][:55], before['hooks'])
        self.assertEqual(plan['targets'], before['targets'])
        self.assertEqual((len(plan['hooks']), plan['data_offset'], plan['allocation_size']),
                         (59, 0xF000, 0x1B000))
        plan['hooks'][0]['asm'] = 'mutated copy'
        plan['targets']['player_slot'] = 1
        self.assertEqual(incoming, before)


    def test_original55_assembled_payloads_and_patches_are_identical_across12_aslr_layouts(self):
        for module in (0x140000000, 0x150000000, 0x7FF600000000):
            for displacement in (0x4000000, 0x200000, -0x4000000, -0x200000):
                allocation = module + displacement
                before = assemble(BASELINE, module, allocation)
                after = assemble(INTEGRATED, module, allocation)
                for left, right in zip(before, after[:55]):
                    for field in ('name', 'site', 'target', 'original', 'patched', 'payload', 'asm'):
                        self.assertEqual(left[field], right[field], (left['name'], field))
                    type(self).baseline_payload_comparisons += 1
                type(self).baseline_layouts.append(dict(module_base=module, allocation=allocation))


    def test_added_code_spans_native_sites_and_rw_pages_are_disjoint(self):
        slots = sorted((hook['code_offset'], hook['code_offset'] + hook.get('code_capacity', 0x400))
                       for hook in INTEGRATED['hooks'])
        sites = sorted((hook['rva'], hook['rva'] + hook['length']) for hook in INTEGRATED['hooks'])
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(slots, slots[1:])))
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(sites, sites[1:])))
        for start, end in slots:
            self.assertGreaterEqual(start, 0)
            self.assertLessEqual(end, ALLOCATION_SIZE)
            for data_first, data_last in PROTECTED_DATA_PAGES:
                self.assertGreaterEqual(max(start, data_first), min(end, data_last))
        self.assertEqual([hook['code_offset'] for hook in INTEGRATED['hooks'][55:]], list(CODE_OFFSETS))
        self.assertEqual([hook['code_capacity'] for hook in INTEGRATED['hooks'][55:]], [CODE_CAPACITY] * 4)


    def test_new_payload_has_no_native_memory_write_or_call(self):
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        md.detail = True
        for hook in PAYLOADS:
            instructions = list(md.disasm(hook['payload'], hook['target']))
            self.assertEqual(sum(instruction.size for instruction in instructions), len(hook['payload']))
            self.assertLessEqual(len(hook['payload']), CODE_CAPACITY)
            for instruction in instructions:
                self.assertNotIn(instruction.mnemonic, ('call', 'inc', 'lock inc'))
                if instruction.operands and instruction.operands[0].type == CS_OP_MEM:
                    # All explicit memory operands are read by scalar replay,
                    # guards or ownership checks; implicit push spills are stack.
                    if hook['name'] == 'HE_LadderSampleClipCapture' and instruction.mnemonic == 'mov':
                        self.assertEqual(instruction.operands[0].mem.base, X86_REG_RSP)
                        self.assertEqual(instruction.operands[0].mem.disp, 0x20)
                        self.assertEqual(instruction.operands[0].size, 4)
                    else:
                        self.assertIn(instruction.mnemonic, ('cmp', 'test'))


    def test_existing_ladder_native_patch_or_protected_data_page_rejected(self):
        for mutation in ('site', 'data', 'overlap', 'beyond'):
            plan = deepcopy(BASELINE)
            if mutation == 'site':
                plan['hooks'][0]['rva'] = NATIVE_SIGNATURES[0][1]
            elif mutation == 'data':
                plan['hooks'][-1]['code_offset'] = 0x13000
            elif mutation == 'overlap':
                plan['hooks'][-1]['code_offset'] = 0x17000
            else:
                plan['hooks'][-1]['code_offset'] = 0x19000
            with self.assertRaises(ValueError):
                apply_ladder_scale(plan)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LadderScaleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(success=result.wasSuccessful(), game_access=False,
        game_files_read=False, fixtures='constructed records only', tests=result.testsRun,
        errors=len(result.errors), failures=len(result.failures), skipped=len(result.skipped),
        cpu_comparisons=LadderScaleTests.comparisons,
        baseline_payload_comparisons=LadderScaleTests.baseline_payload_comparisons,
        baseline_layouts=len(LadderScaleTests.baseline_layouts), hook_count=59,
        new_hook_count=4, baseline_hooks_preserved=55)
    print(json.dumps(report))
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
