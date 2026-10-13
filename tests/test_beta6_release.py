"""Release integration retains the validated item-repair payload chain."""
from copy import deepcopy
import base64
import hashlib
import importlib
import json
from pathlib import Path
import sys
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from build_profile import (load_beta6_plan as load_plan, load_beta563_plan, source_plan,
                           source_plan_beta563, assemble, validate_layout, relocation_specs)
from verify_beta56 import expected_layouts
from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import apply_dung_fan
from hinoenma_four_throwables import apply_four_throwables
from hinoenma_arrow_sloth import apply_arrow_sloth
from hinoenma_arrow_sloth_lookup import apply_arrow_sloth_lookup

BASELINE_SHA256 = '7bfd8636d28db7e67196c201979b4d2522fd8e6133c637e698c3b554efb54695'
LAYOUTS = ((0x140000000, 0x144000000), (0x7FF600000000, 0x7FF604000000),
           (0x180000000, 0x176000000))
STAGES = (('harakiri', apply_harakiri), ('dung_fan', apply_dung_fan),
          ('four_throwables', apply_four_throwables), ('arrow_sloth', apply_arrow_sloth),
          ('arrow_sloth_lookup', apply_arrow_sloth_lookup))
CHANGED_HOOKS = {'HE_InputA', 'HE_InputB', 'HE_HimorogiFragment', 'HE_Consumables',
                 'HE_InherentDirectElement', 'HE_LivingWeaponDigitNine', 'HE_LadderCommonLookup'}


class Beta6ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = load_beta563_plan()
        cls.trial = deepcopy(cls.baseline)
        for _, transform in STAGES:
            cls.trial = transform(cls.trial)
        cls.plan = load_plan()

    def test_release_metadata_and_frozen_beta563_identity_are_independent(self):
        historical = (ROOT / 'profiles/baseline-beta6.json').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(),
                         '7f8e4fa3dc9144ebd8d65ab06826fb447a8691c341abab904223c33e13e38f86')
        self.assertEqual(self.plan['tool_version'], '1.0.0-beta.6')
        frozen = (ROOT / 'profiles/baseline-beta5.6.3.json').read_bytes()
        self.assertEqual(hashlib.sha256(frozen).hexdigest(), BASELINE_SHA256)
        self.assertEqual(self.baseline['tool_version'], '1.0.0-beta.5.6.3')
        self.assertFalse(any(self.baseline.get(name + '_revision') for name, _ in STAGES))
        rebuilt = source_plan_beta563(json.loads(frozen.decode('utf-8')))
        for a, b in zip(assemble(self.baseline, *LAYOUTS[0]), assemble(rebuilt, *LAYOUTS[0])):
            self.assertEqual(a['payload'], b['payload'])

    def test_all_82_release_payloads_equal_the_validated_trial_chain_at_three_layouts(self):
        self.assertEqual(len(self.plan['hooks']), 82)
        for layout in LAYOUTS:
            expected, current = assemble(self.trial, *layout), assemble(self.plan, *layout)
            self.assertEqual(len(current), 82)
            for a, b in zip(expected, current):
                for field in ('name', 'payload', 'patched', 'original', 'site', 'target',
                              'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], b[field], (layout, a['name'], field))

    def test_compiled_relocation_covers_new_carrier_tail_in_all_12_layouts(self):
        def relocated(spec, module, allocation, data_offset):
            # Independently apply the launcher's three fixup encodings to the
            # fixed template; never reassemble it to obtain the actual side.
            result = bytearray(base64.b64decode(spec['template']))
            for fix in spec['fixups']:
                if fix['kind'] == 0:
                    value = struct.pack('<Q', allocation + data_offset)
                elif fix['kind'] == 2:
                    value = struct.pack('<Q', module + fix['target'])
                elif fix['kind'] == 1:
                    value = struct.pack('<i', module + fix['target'] -
                                        (allocation + spec['code_offset'] + fix['next']))
                else:
                    self.fail('Unknown relocation kind')
                result[fix['offset']:fix['offset'] + len(value)] = value
            return bytes(result)

        specs = relocation_specs(self.plan)
        self.assertEqual(len(specs), 82)
        self.assertEqual([spec['name'] for spec in specs],
                         [hook['name'] for hook in self.plan['hooks']])
        layouts = sorted(expected_layouts(self.plan))
        self.assertEqual(len(layouts), 12)
        self.assertEqual(len({module for module, _ in layouts}), 3)
        carrier = next(s for s in specs if s['name'] == 'HE_LivingWeaponDigitNine')
        self.assertTrue(any(f['offset'] >= 0x4000 for f in carrier['fixups']))
        self.assertTrue(any(f['offset'] >= 0x5800 for f in carrier['fixups']))
        for module, allocation in layouts:
            for spec, actual in zip(specs, assemble(self.plan, module, allocation)):
                self.assertEqual(relocated(spec, module, allocation, self.plan['data_offset']),
                                 actual['payload'], (actual['name'], hex(module), hex(allocation)))

        # Reproduce the shipped-template failure mechanism: old scan ranges
        # omit both appended helpers, leaving their fixed absolute pointers.
        broken = deepcopy(self.plan)
        name = 'HE_LivingWeaponDigitNine'
        broken['abyss_assembly_code_intervals'][name] = deepcopy(
            self.baseline['abyss_assembly_code_intervals'][name])
        bad = next(s for s in relocation_specs(broken) if s['name'] == name)
        self.assertFalse(any(f['offset'] >= 0x4000 for f in bad['fixups']))
        module, allocation = layouts[-1]
        expected = next(h for h in assemble(self.plan, module, allocation) if h['name'] == name)
        incorrect = relocated(bad, module, allocation, self.plan['data_offset'])
        self.assertEqual(incorrect[:0x4000], expected['payload'][:0x4000])
        self.assertNotEqual(incorrect[0x4000:], expected['payload'][0x4000:])

    def test_only_seven_owned_payloads_change_no_native_sites_or_data_layout_changes(self):
        for key in ('targets', 'data_offset', 'allocation_size', 'protected_data_pages',
                    'disk_sha256', 'image_size'):
            self.assertEqual(self.plan[key], self.baseline[key], key)
        validate_layout(self.plan)
        for layout in LAYOUTS:
            old, current = assemble(self.baseline, *layout), assemble(self.plan, *layout)
            self.assertEqual({a['name'] for a, b in zip(old, current) if a['payload'] != b['payload']},
                             CHANGED_HOOKS)
            for a, b in zip(old, current):
                for field in ('name', 'site', 'target', 'patched', 'original', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[field], b[field])
                self.assertLessEqual(len(b['payload']), b['code_capacity'])

    def test_default_source_rebuild_is_repeatable_and_preserves_all_repair_revisions(self):
        saved = deepcopy(self.plan)
        rebuilt = source_plan(self.plan)
        again = source_plan(rebuilt)
        self.assertEqual(self.plan, saved)
        for name, _ in STAGES:
            self.assertEqual(rebuilt[name + '_revision'], 1)
        for candidate in (rebuilt, again):
            self.assertEqual(candidate['tool_version'], '1.0.0-beta.6')
            self.assertEqual(candidate['targets'], self.plan['targets'])
            for a, b in zip(assemble(self.plan, *LAYOUTS[0]), assemble(candidate, *LAYOUTS[0])):
                self.assertEqual(a['payload'], b['payload'])

    def test_historical_trial_builders_still_reproduce_frozen_baseline_stages(self):
        expected = deepcopy(self.baseline)
        release_bytes = (ROOT / 'profiles/steam-1.24.8.json').read_bytes()
        version_bytes = (ROOT / 'version.json').read_bytes()
        with tempfile.TemporaryDirectory(prefix='nioh-beta6-trials-') as directory:
            for name, transform in STAGES:
                expected = transform(expected)
                builder = importlib.import_module('build_' + name + '_trial')
                output = Path(directory) / (name + '.json')
                receipt = builder.build(output)
                actual = json.loads(output.read_text('utf-8'))
                self.assertEqual(actual, expected, name)
                self.assertEqual(receipt['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
                self.assertEqual(receipt['hook_count'], 82)
                self.assertTrue(receipt['release_artifacts_unchanged'])
        self.assertEqual((ROOT / 'profiles/steam-1.24.8.json').read_bytes(), release_bytes)
        self.assertEqual((ROOT / 'version.json').read_bytes(), version_bytes)


if __name__ == '__main__':
    unittest.main()
