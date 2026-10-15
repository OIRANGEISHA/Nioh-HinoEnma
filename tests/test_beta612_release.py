"""Exact release identity, relocations and the confirmed item/injury chain."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import (load_beta612_plan as load_plan, load_beta611_plan, source_plan, assemble,
    validate_layout, relocation_specs, legacy_plans)
from hinoenma_beta612_release import (apply_release, trial_plan, validate_release,
    CONFIRMED, TRIAL_CANONICAL_SHA256, digest)
from verify_beta56 import expected_layouts
from verify_beta612_items import BASE_SHA, CHANGED
import test_elemental_resistance_items_portable as resistance
import test_item_hurt_lookup_portable as hurt


class Beta612ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_beta611_plan()
        cls.trial = trial_plan(cls.base)
        cls.plan = load_plan()

    def test_exact_release_and_gameplay_evidence_have_distinct_identities(self):
        meta = json.loads((ROOT/'profiles/baseline-beta6.1.2-version.json').read_text('utf-8'))
        self.assertEqual((meta['version'], meta['file_version']),
                         ('1.0.0-beta.6.1.2', '1.0.0.82'))
        self.assertEqual(hashlib.sha256((ROOT/'profiles/baseline-beta6.1.1.json').read_bytes()).hexdigest(), BASE_SHA)
        self.assertEqual(digest(self.trial), TRIAL_CANONICAL_SHA256)
        self.assertTrue(self.trial[CONFIRMED]['live_confirmation_pending'])
        self.assertFalse(self.plan[CONFIRMED]['live_confirmation_pending'])
        self.assertFalse(self.plan['beta612_exact_executable_gameplay_validated'])
        self.assertTrue(self.plan['beta612_runtime_gameplay_validated'])
        self.assertTrue(self.plan['beta612_quantity_decrement_not_required'])
        evidence = json.loads((ROOT/'docs/elemental-resistance-items-trial.json').read_text('utf-8'))
        self.assertTrue(evidence['all_five_native_aggregate_changes_observed'])
        self.assertEqual(len(evidence['sampled_injury_evidence']), 3)
        self.assertFalse(evidence['all_five_individually_interrupted'])
        self.assertFalse(evidence['release_exe_updated'])

    def test_all_release_payloads_match_live_trial_at_twelve_layouts(self):
        for module, allocation in sorted(expected_layouts(self.plan)):
            old, trial, new = (assemble(p, module, allocation)
                               for p in (self.base, self.trial, self.plan))
            self.assertEqual(len(new), 82)
            self.assertEqual({a['name'] for a,b in zip(old,new) if a['payload'] != b['payload']}, CHANGED)
            for a,b,c in zip(old,trial,new):
                self.assertEqual(b['payload'], c['payload'])
                for field in ('name', 'patched', 'original', 'site', 'target', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], c[field])

    def test_all_exe_relocations_include_guard_and_exclude_injury_data(self):
        specs = relocation_specs(self.plan)
        table = next(s for s in specs if s['name'] == 'HE_MapVisualResourcePrivate')
        self.assertTrue(all(f['offset'] < 458 for f in table['fixups']))
        for module, allocation in sorted(expected_layouts(self.plan)):
            for spec, reference in zip(specs, assemble(self.plan, module, allocation)):
                payload = bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind'] == 0: value = struct.pack('<Q', allocation+self.plan['data_offset'])
                    elif fix['kind'] == 2: value = struct.pack('<Q', module+fix['target'])
                    else:
                        self.assertEqual(fix['kind'], 1)
                        value = struct.pack('<i', module+fix['target']-allocation-spec['code_offset']-fix['next'])
                    payload[fix['offset']:fix['offset']+len(value)] = value
                self.assertEqual(bytes(payload), reference['payload'])

    def test_pure_rebuild_keeps_legacy_profiles_and_protected_geometry(self):
        before = deepcopy(self.plan)
        validate_release(self.plan)
        validate_layout(self.plan)
        self.assertEqual(self.plan, before)
        self.assertEqual(source_plan(self.plan), self.plan)
        self.assertEqual(source_plan(source_plan(self.plan)), self.plan)
        self.assertEqual(legacy_plans(self.base), legacy_plans(self.plan))
        self.assertEqual(sum(len(p['hooks']) for p in legacy_plans(self.plan))*12, 7536)
        for key in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets'):
            self.assertEqual(self.base[key], self.plan[key])

    def test_wrong_scope_claims_code_and_layout_are_rejected(self):
        mutations = [lambda p:p.update(beta612_exact_executable_gameplay_validated=True),
            lambda p:p.update(beta612_runtime_gameplay_validated=False),
            lambda p:p.update(beta612_quantity_decrement_not_required=False),
            lambda p:p.update(tool_version='1.0.0-beta.6.1.1'),
            lambda p:p['hooks'][0].update(asm=p['hooks'][0]['asm']+'\nnop'),
            lambda p:p['hooks'][0].update(code_offset=0xF000),
            lambda p:p['targets'].update(spell_schedule_return=0),
            lambda p:p['abyss_assembly_code_intervals'].pop('HE_LivingWeaponDigitNine'),
            lambda p:p[CONFIRMED].update(live_confirmation_pending=True)]
        for mutate in mutations:
            bad = deepcopy(self.plan); mutate(bad)
            with self.assertRaises(ValueError): validate_release(bad)
            with self.assertRaises(ValueError): source_plan(bad)

    def test_transform_is_not_repeatable_or_accepted_on_another_baseline(self):
        before = deepcopy(self.base)
        self.assertEqual(apply_release(self.base), self.plan)
        self.assertEqual(before, self.base)
        for wrong in (self.plan, self.trial, dict(self.base, tool_version='other')):
            with self.assertRaises(ValueError): apply_release(wrong)

    def test_release_native_cast_moving_recast_and_injury_abi_paths(self):
        check = resistance.ElementalResistanceTests()
        for layout in resistance.b.LAYOUTS:
            for row in resistance.OBSERVED:
                check.entry(resistance.ResistanceLookup(self.plan, row[0], layout), True)
                machine = resistance.ResistanceRecast(self.plan, row[0], layout)
                resistance.recast.ItemRecastLookupTests().checked(machine, True)
            for source,target,index,first,count,raw in hurt.h.ROUTES:
                machine = hurt.ItemHurtMachine(self.plan, layout, action=41)
                machine.select(source,index)
                hurt.ItemHurtLookupTests().checked(machine, True, target=target)
                machine.current(target)
                machine.select(151,2602)
                hurt.ItemHurtLookupTests().checked(machine, True, target=87)


if __name__ == '__main__':
    unittest.main()
