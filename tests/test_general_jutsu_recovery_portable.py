"""Replay the observed movement-to-Boss-injury collision and its guarded fix.

The native records/schedules come from a read-only catalogue. Calls and memory
owners are synthetic; actual assembly executes. Damage and rendered motion
remain gameplay checks, not assertions made by this CPU fixture.
"""
import base64
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import assemble, relocation_specs
import hinoenma_general_jutsu_recovery as h
import test_general_jutsu_timing_portable as timing
import test_item_hurt_lookup_portable as hurt
import test_item_recast_lookup_portable as recast
from portable_machine import b

PARENT = timing.PLAN
PLAN = h.apply_general_jutsu_recovery(PARENT)
NATIVE = json.loads((ROOT/'tests/fixtures/general-jutsu-movement-native.json').read_text('utf8'))
SCHEDULES = {a:h.EMPTY_SCHEDULE.hex() for a in h.MOVEMENT_MOTIONS}


def machine(plan=PLAN, action=1015, layout=b.LAYOUTS[0]):
    with patch.object(hurt, 'MOTIONS', {**hurt.MOTIONS, **h.MOVEMENT_MOTIONS}), \
            patch.object(hurt.h, 'SCHEDULES', {**hurt.h.SCHEDULES, **SCHEDULES}):
        m = hurt.ItemHurtMachine(plan, layout, action)
    for ident in h.MOVEMENT_MOTIONS:
        m.put32(m.records[ident]+0x134, -1)
    return m


class RecoveryTests(unittest.TestCase):
    def check(self, m, accepted, **args):
        hurt.ItemHurtLookupTests().checked(m, accepted, **args)

    def test_observed_1015_to_boss89_reproduced_then_resolves_common89(self):
        # Actual captured selected descriptor, source 151 / index 2604.
        observed = '34003a00ffffffffffff00ffffffff000000000059000000ff806464400020000080ff7fffffffffffffffffffffffff'
        self.assertEqual(next(r[5].hex() for r in hurt.h.ROUTES if r[2] == 2604), observed)
        self.check(machine(PARENT), False)
        self.check(machine(), True)

    def test_complete_native_movement_contract_and_each_injury_leaf(self):
        self.assertEqual(set(map(int, NATIVE['actions'])), set(h.MOVEMENT_MOTIONS))
        for action, motion in h.MOVEMENT_MOTIONS.items():
            raw = bytes.fromhex(NATIVE['actions'][str(action)]['params_raw'])
            self.assertEqual(struct.unpack_from('<i', raw, 0x20)[0], motion)
            self.assertEqual(struct.unpack_from('<i', raw, 0x34)[0], -1)
            self.assertEqual(raw[0x40:0xA0], h.EMPTY_SCHEDULE)
            for source, target, index, first, count, descriptor in hurt.h.ROUTES:
                m = machine(action=action); m.select(source, index)
                self.check(m, True, target=target)

    def test_full_abi_both_templates_callers_aslr_and_optional_output(self):
        for layout in b.LAYOUTS:
            for caller in hurt.h.CALLERS:
                for template in (0x58E5E, 0x51BE1):
                    for output in (False, True):
                        m = machine(layout=layout)
                        for at in (b.ACTOR, b.META, m.data+4): m.put32(at, template)
                        self.check(m, True, caller=caller, output=output)

    def test_unknown_motion_alternate_schedule_and_transition_fail_closed(self):
        for action in h.MOVEMENT_MOTIONS:
            for offset, value in ((0x120, 999), (0x134, 0)):
                m = machine(action=action); m.put32(m.records[action]+offset, value)
                self.check(m, False)
        for off in range(96):
            m = machine(); at = m.records[1015]+0x140+off
            m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0]^1]))
            self.check(m, False)
        for off in range(48):
            m = machine(); at = m.entries[151, 2604]+off
            m.cpu.mem_write(at, bytes([m.cpu.mem_read(at, 1)[0]^1]))
            self.check(m, False)
        for action in (1000, 1001, 1005, 1008, 1014, 1022):
            m = machine(); m.put32(m.records[1015], action)
            self.check(m, False)

    def test_owned_bank_current_membership_clips_and_selected_native_route_required(self):
        m = machine(); self.check(m, False, caller=0x1100800)
        m = machine(); self.check(m, False, foreign=True)
        for kind in ('boss-bank', 'owner', 'disabled', 'missing', 'duplicate',
                     'role', 'foreign-player', 'wrong-index', 'not-unique', 'no-clip2', 'no-clip6'):
            m = machine(); current = m.records[1015]
            if kind == 'boss-bank': m.put32(b.CONTROLLER+0x68, 1)
            elif kind == 'owner': m.put64(current+0x38, b.OWN_BANK)
            elif kind == 'disabled': m.cpu.mem_write(current+0x40, b'\0')
            elif kind == 'missing': m.put64(b.VECTOR+list(m.records).index(1015)*8, 0)
            elif kind == 'duplicate':
                m.put64(b.VECTOR+len(m.records)*8, current); m.put32(b.BANK+0x130, len(m.records)+1)
            elif kind == 'role': m.put32(b.META+0xC, 0)
            elif kind == 'foreign-player': m.put64(m.module+PLAN['targets']['player_slot'], 0)
            elif kind == 'wrong-index': m.put64(hurt.TABLE+2604*8, 0)
            elif kind == 'not-unique': m.put64(b.BANK+0x60, hurt.EXTRA)
            else: m.put64(b.CLIPS[2 if kind == 'no-clip2' else 6], 0)
            self.check(m, False)

    def test_existing_cast_consecutive_injury_and_idle_are_unchanged(self):
        checker = hurt.ItemHurtLookupTests()
        with patch.object(checker, 'plan', PLAN, create=True):
            for name in ('test_each_supported_item_cast_uses_all_selected_native_leaves',
                         'test_consecutive_native_injury_can_continue_without_persistent_token',
                         'test_normal_skills_idle_unrelated_callers_and_role_mismatches_fall_through'):
                getattr(checker, name)()
        with patch.object(timing, 'PLAN', PLAN), patch.object(timing, 'HOOKS', assemble(PLAN, timing.old.BASE, timing.old.ALLOC)):
            for name in ('test_consecutive_throw_input_and_injury_native_routes',
                         'test_observed_kunai_gap_and_all_family_boundaries_once',
                         'test_alternating_native_casts_rearm_and_do_not_duplicate',
                         'test_generic_entry_lookup_injury_and_moving_recast_still_work'):
                getattr(timing.TimingTests(name), name)()

    def test_repacked_fixed_recast_entry_preserves_repeat_and_rejection(self):
        checker = recast.ItemRecastLookupTests()
        with patch.object(checker, 'plan', PLAN, create=True):
            for name in ('test_native_callers_three_aslr_layouts_full_abi',
                         'test_unrelated_caller_private_motion_and_missing_request_rejected',
                         'test_after_callback_movement_guard_rechecked'):
                getattr(checker, name)()

    def test_only_owned_carrier_changes_native_sites_and_relocations_match(self):
        saved = deepcopy(PARENT)
        self.assertEqual(h.apply_general_jutsu_recovery(PARENT), PLAN)
        self.assertEqual(PARENT, saved)
        bad = deepcopy(PARENT); bad['tool_version'] = 'unexpected'
        with self.assertRaises(ValueError): h.apply_general_jutsu_recovery(bad)
        specs = relocation_specs(PLAN)
        for module, alloc in b.LAYOUTS:
            changed = []
            for old, new, spec in zip(assemble(PARENT,module,alloc), assemble(PLAN,module,alloc), specs):
                for field in ('site','patched','target','code_capacity','original'):
                    self.assertEqual(old[field], new[field])
                self.assertLessEqual(len(new['payload']), new['code_capacity'])
                if old['payload'] != new['payload']:
                    changed.append(new['name'])
                    self.assertEqual(old['payload'][:0x200], new['payload'][:0x200])
                    self.assertEqual(old['payload'][0xA25:], new['payload'][0xA00:])
                raw = bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind'] == 0: value = struct.pack('<Q', alloc+PLAN['data_offset'])
                    elif fix['kind'] == 2: value = struct.pack('<Q', module+fix['target'])
                    else: value = struct.pack('<i', module+fix['target']-alloc-spec['code_offset']-fix['next'])
                    raw[fix['offset']:fix['offset']+len(value)] = value
                self.assertEqual(bytes(raw), new['payload'])
            self.assertEqual(changed, [h.CODE_CARRIER])


if __name__ == '__main__': unittest.main()
