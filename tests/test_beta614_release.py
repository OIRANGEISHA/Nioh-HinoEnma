"""Verify the final release, not a second application of its trial transforms."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import base64
import hashlib
import json
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import (load_plan, load_beta613_plan, source_plan, assemble,
    relocation_specs, legacy_plans, validate_layout)
from hinoenma_beta614_release import apply_release, trial_plan, validate_release, TRIAL_CANONICAL_SHA256
from hinoenma_general_jutsu import digest
from verify_beta614_items import BASE_SHA, CHANGED, verify_gameplay
from verify_beta56 import expected_layouts
import test_general_jutsu_timing_portable as timing
import test_general_jutsu_recovery_portable as recovery


class Beta614ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_beta613_plan()
        cls.trial = trial_plan(cls.base)
        cls.plan = load_plan()

    def test_identity_and_limited_gameplay_claims(self):
        meta = json.loads((ROOT/'version.json').read_text('utf8'))
        self.assertEqual((meta['version'], meta['file_version']), ('1.0.0-beta.6.1.4', '1.0.0.84'))
        self.assertEqual(hashlib.sha256((ROOT/'profiles/baseline-beta6.1.3.json').read_bytes()).hexdigest(), BASE_SHA)
        self.assertEqual(digest(self.trial), TRIAL_CANONICAL_SHA256)
        self.assertTrue(self.plan['beta614_sampled_kunai_gameplay_validated'])
        self.assertFalse(self.plan['beta614_all_jutsu_gameplay_validated'])
        self.assertFalse(self.plan['beta614_exact_executable_gameplay_validated'])
        self.assertEqual(len(verify_gameplay()), 4)

    def test_all_payloads_equal_trial_and_native_sites_remain_unchanged(self):
        for module, allocation in sorted(expected_layouts(self.plan)):
            old = {h['name']: h for h in assemble(self.base, module, allocation)}
            trial, new = (assemble(p, module, allocation) for p in (self.trial, self.plan))
            self.assertEqual(len(new), 84)
            self.assertEqual({h['name'] for h in new if h['payload'] != old[h['name']]['payload']}, CHANGED)
            for a, b in zip(trial, new):
                for field in ('name', 'payload', 'patched', 'original', 'site', 'target', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], b[field])
                for field in ('rva', 'length', 'original', 'patched', 'code_offset', 'code_capacity'):
                    self.assertEqual(old[b['name']][field], b[field])

    def test_final_relocations_match_assembly_at_twelve_layouts(self):
        specs = relocation_specs(self.plan)
        for module, allocation in sorted(expected_layouts(self.plan)):
            for spec, reference in zip(specs, assemble(self.plan, module, allocation)):
                raw = bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind'] == 0:
                        value = struct.pack('<Q', allocation + self.plan['data_offset'])
                    elif fix['kind'] == 2:
                        value = struct.pack('<Q', module + fix['target'])
                    else:
                        self.assertEqual(fix['kind'], 1)
                        value = struct.pack('<i', module + fix['target'] - allocation - spec['code_offset'] - fix['next'])
                    raw[fix['offset']:fix['offset']+len(value)] = value
                self.assertEqual(bytes(raw), reference['payload'])

    def test_parent_transform_layout_and_legacy_remain_pure(self):
        before = deepcopy(self.base)
        self.assertEqual(apply_release(self.base), self.plan)
        self.assertEqual(before, self.base)
        validate_layout(self.plan)
        self.assertEqual(source_plan(self.plan), self.plan)
        self.assertEqual(legacy_plans(self.base), legacy_plans(self.plan))
        for key in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets'):
            self.assertEqual(self.base[key], self.plan[key])
        ranges = sorted((h['code_offset'], h['code_offset']+h['code_capacity']) for h in self.plan['hooks'])
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])))
        for a, b in ranges:
            self.assertLessEqual(b, self.plan['allocation_size'])
            for c, d in self.plan['protected_data_pages']:
                self.assertFalse(max(a, c) < min(b, d))
        for wrong in (self.plan, self.trial, dict(self.base, tool_version='other')):
            with self.assertRaises(ValueError):
                apply_release(wrong)

    def test_wrong_scope_or_runtime_bytes_reject(self):
        changes = [lambda p: p.update(beta614_all_jutsu_gameplay_validated=True),
            lambda p: p.update(beta614_exact_executable_gameplay_validated=True),
            lambda p: p.update(beta614_sampled_kunai_gameplay_validated=False),
            lambda p: p['hooks'][0].update(asm=p['hooks'][0]['asm']+'\nnop'),
            lambda p: p['hooks'][0].update(code_capacity=4),
            lambda p: p['targets'].update(soul_familiarity_min=0)]
        for change in changes:
            bad = deepcopy(self.plan)
            change(bad)
            with self.assertRaises(ValueError):
                validate_release(bad)
            with self.assertRaises(ValueError):
                source_plan(bad)

    def test_final_image_projectile_recast_injury_and_retained_special_paths(self):
        with patch.object(timing, 'PLAN', self.plan), \
                patch.object(timing, 'HOOKS', assemble(self.plan, timing.old.BASE, timing.old.ALLOC)):
            for name in ('test_observed_kunai_gap_and_all_family_boundaries_once',
                         'test_alternating_native_casts_rearm_and_do_not_duplicate',
                         'test_generic_entry_lookup_injury_and_moving_recast_still_work',
                         'test_consecutive_throw_input_and_injury_native_routes'):
                with self.subTest(case=name):
                    getattr(timing.TimingTests(name), name)()
        checker = recovery.RecoveryTests()
        checker.check(recovery.machine(plan=self.plan), True)
        checker.check(recovery.machine(plan=self.plan), False, foreign=True)


if __name__ == '__main__':
    unittest.main()
