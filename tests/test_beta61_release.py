"""Frozen spell identities, release provenance and relocation regressions."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import (load_beta61_plan as load_plan, load_beta6_plan, source_plan, assemble,
                           validate_layout, relocation_specs, legacy_plans)
from hinoenma_beta61_release import apply_release, validate_release
from hinoenma_wind_weakness_dragon import apply_wind_weakness_dragon
from verify_beta56 import expected_layouts

BETA6_SHA = '7f8e4fa3dc9144ebd8d65ab06826fb447a8691c341abab904223c33e13e38f86'
SOURCE_SHA = 'f4546def16fadca6d7a270c57cf2873658e8c5e406d70df48f10d324f91cd7cc'
CHANGED = {'HE_InputA', 'HE_InputB', 'HE_LivingWeaponDigitNine'}


class Beta61ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_beta6_plan()
        cls.trial = apply_wind_weakness_dragon(cls.base)
        cls.plan = load_plan()

    def test_release_metadata_is_distinct_from_warm_trial_and_frozen_parent(self):
        meta = json.loads((ROOT / 'profiles/baseline-beta6.1-version.json').read_text('utf-8'))
        self.assertEqual((meta['version'], meta['file_version']),
                         ('1.0.0-beta.6.1', '1.0.0.80'))
        for path, expected in (('profiles/baseline-beta6.json', BETA6_SHA),
                               ('src/hinoenma_wind_weakness_dragon.py', SOURCE_SHA)):
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        self.assertEqual(self.base['tool_version'], '1.0.0-beta.6')
        self.assertTrue(self.trial['wind_weakness_dragon_gameplay_confirmation_pending'])
        self.assertFalse(self.plan['wind_weakness_dragon_gameplay_confirmation_pending'])
        self.assertTrue(self.plan['beta61_runtime_gameplay_validated'])
        self.assertFalse(self.plan['beta61_exact_executable_gameplay_validated'])
        self.assertEqual(self.plan['beta61_confirmed_item_ids'], [26116, 44930, 44607])
        self.assertFalse(self.plan['wind_weakness_dragon_direct_inventory_effect_hp_save_writes'])

    def test_promoted_payloads_match_trial_and_change_only_three_owned_hooks(self):
        for module, allocation in sorted(expected_layouts(self.plan)):
            before = assemble(self.base, module, allocation)
            trial = assemble(self.trial, module, allocation)
            actual = assemble(self.plan, module, allocation)
            self.assertEqual(len(actual), 82)
            self.assertEqual({a['name'] for a, b in zip(before, actual)
                              if a['payload'] != b['payload']}, CHANGED)
            for old, expected, current in zip(before, trial, actual):
                self.assertEqual(expected['payload'], current['payload'])
                for key in ('name', 'patched', 'original', 'site', 'target',
                            'code_offset', 'code_capacity'):
                    self.assertEqual(old[key], current[key])

    def test_carrier_extended_relocation_matches_assembler_at_all_twelve_layouts(self):
        specs = relocation_specs(self.plan)
        carrier = next(s for s in specs if s['name'] == 'HE_LivingWeaponDigitNine')
        self.assertTrue(any(f['offset'] >= 0x6C00 for f in carrier['fixups']))
        self.assertEqual(self.plan['abyss_assembly_code_intervals'][carrier['name']][-1],
                         [16384, 32164])
        for module, allocation in sorted(expected_layouts(self.plan)):
            for spec, reference in zip(specs, assemble(self.plan, module, allocation)):
                payload = bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind'] == 0:
                        value = struct.pack('<Q', allocation + self.plan['data_offset'])
                    elif fix['kind'] == 2:
                        value = struct.pack('<Q', module + fix['target'])
                    else:
                        self.assertEqual(fix['kind'], 1)
                        value = struct.pack('<i', module + fix['target'] -
                                            allocation - spec['code_offset'] - fix['next'])
                    payload[fix['offset']:fix['offset'] + len(value)] = value
                self.assertEqual(bytes(payload), reference['payload'])

    def test_rebuild_and_parent_validation_are_pure_and_keep_nine_legacy_sets(self):
        before = deepcopy(self.plan)
        validate_release(self.plan)
        validate_layout(self.plan)
        self.assertEqual(self.plan, before)
        self.assertEqual(source_plan(self.plan), self.plan)
        self.assertEqual(source_plan(source_plan(self.plan)), self.plan)
        old_legacy, new_legacy = legacy_plans(self.base), legacy_plans(self.plan)
        self.assertEqual(len(old_legacy), 9)
        self.assertEqual(new_legacy, old_legacy)
        self.assertEqual(sum(len(p['hooks']) for p in new_legacy) * 12, 7536)
        for key in ('targets', 'allocation_size', 'data_offset', 'protected_data_pages'):
            self.assertEqual(self.base[key], self.plan[key])

    def test_invalid_release_claims_intervals_and_parent_identity_are_rejected(self):
        for key, value in (('beta61_confirmed_item_ids', [26116, 44930]),
                           ('beta61_exact_executable_gameplay_validated', True),
                           ('beta61_runtime_gameplay_validated', False),
                           ('wind_weakness_dragon_gameplay_confirmation_pending', True),
                           ('wind_weakness_dragon_auxiliary_timing_guard_pending', True)):
            bad = deepcopy(self.plan)
            bad[key] = value
            with self.assertRaises(ValueError):
                validate_release(bad)
        bad = deepcopy(self.plan)
        bad['abyss_assembly_code_intervals']['HE_LivingWeaponDigitNine'][-1] = [16384, 26103]
        with self.assertRaises(ValueError):
            validate_release(bad)
        for key, value in (('rva', 0), ('original', '9090909090'), ('code_offset', 0)):
            bad = deepcopy(self.plan)
            bad['hooks'][6][key] = value
            with self.assertRaises(ValueError):
                source_plan(bad)
        with self.assertRaises(ValueError):
            apply_release(self.plan)

    def test_historical_spell_trial_remains_rebuildable_without_changing_release(self):
        from build_wind_weakness_dragon_trial import build
        profile = (ROOT / 'profiles/steam-1.24.8.json').read_bytes()
        with tempfile.TemporaryDirectory(prefix='nioh-beta61-trial-') as directory:
            target = Path(directory) / 'trial.json'
            result = build(target)
            actual = json.loads(target.read_text('utf-8'))
            expected = json.loads(json.dumps(self.trial))
            self.assertEqual(actual, expected)
            self.assertEqual(result['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertTrue(result['release_artifacts_unchanged'])
        self.assertEqual((ROOT / 'profiles/steam-1.24.8.json').read_bytes(), profile)


if __name__ == '__main__':
    unittest.main()
