"""Exercise the final packaged image and reject changes to its verified scope."""
from copy import deepcopy
from pathlib import Path
import base64, json, struct, sys, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'src')]
from build_profile import load_plan, load_beta614_plan, source_plan, assemble, relocation_specs, legacy_plans, validate_layout
from hinoenma_beta62_release import apply_release, trial_plan, validate_release, CONFIRMED
from verify_beta62_items import CHANGED, ADDED, verify_gameplay
from verify_beta56 import expected_layouts
import test_soul_purge_portable as soul
import test_kodama_transform_portable as kodama


class Beta62ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_beta614_plan(); cls.trial = trial_plan(cls.base); cls.plan = load_plan()

    def test_identity_and_precise_gameplay_claims(self):
        meta = json.loads((ROOT/'version.json').read_text('utf8'))
        self.assertEqual((meta['version'], meta['file_version']), ('1.0.0-beta.6.2', '1.0.0.85'))
        for key in CONFIRMED:
            self.assertTrue(self.trial[key]['live_confirmation_pending'])
            self.assertFalse(self.plan[key]['live_confirmation_pending'])
        self.assertTrue(self.plan['beta62_runtime_gameplay_validated'])
        self.assertFalse(self.plan['beta62_exact_executable_gameplay_validated'])
        self.assertFalse(self.plan['beta62_kodama_live_injury_validated'])
        self.assertEqual(len(verify_gameplay()), 6)

    def test_all_payloads_equal_installed_trial_and_existing_native_sites_unchanged(self):
        for module, allocation in sorted(expected_layouts(self.plan)):
            old = {h['name']: h for h in assemble(self.base, module, allocation)}
            trial, final = [assemble(p, module, allocation) for p in (self.trial, self.plan)]
            self.assertEqual(len(final), 86)
            self.assertEqual({h['name'] for h in final if h['name'] not in old}, ADDED)
            self.assertEqual({h['name'] for h in final if h['name'] in old and h['payload'] != old[h['name']]['payload']}, CHANGED)
            for a, z in zip(trial, final):
                for key in ('name', 'payload', 'patched', 'original', 'target', 'code_offset', 'code_capacity'):
                    self.assertEqual(a[key], z[key])
                if z['name'] in old:
                    for key in ('rva', 'length', 'original', 'patched', 'code_offset'):
                        self.assertEqual(old[z['name']][key], z[key])

    def test_relocations_separate_code_and_embedded_native_tables(self):
        specs = relocation_specs(self.plan)
        for module, alloc in sorted(expected_layouts(self.plan)):
            for spec, reference in zip(specs, assemble(self.plan, module, alloc)):
                raw = bytearray(base64.b64decode(spec['template']))
                for f in spec['fixups']:
                    if f['kind'] == 0: value = struct.pack('<Q', alloc+self.plan['data_offset'])
                    elif f['kind'] == 2: value = struct.pack('<Q', module+f['target'])
                    else:
                        self.assertEqual(f['kind'], 1)
                        value = struct.pack('<i', module+f['target']-alloc-spec['code_offset']-f['next'])
                    raw[f['offset']:f['offset']+len(value)] = value
                self.assertEqual(bytes(raw), reference['payload'])

    def test_layout_parent_purity_and_historical_payloads(self):
        before = deepcopy(self.base)
        self.assertEqual(apply_release(self.base), self.plan)
        self.assertEqual(self.base, before)
        self.assertEqual(source_plan(self.plan), self.plan)
        self.assertEqual(legacy_plans(self.base), legacy_plans(self.plan))
        validate_layout(self.plan)
        ranges = sorted((h['code_offset'], h['code_offset']+h['code_capacity']) for h in self.plan['hooks'])
        self.assertTrue(all(a[1] <= z[0] for a,z in zip(ranges, ranges[1:])))
        for a,z in ranges:
            self.assertLessEqual(z, self.plan['allocation_size'])
            for c,d in self.plan['protected_data_pages']:
                self.assertFalse(max(a,c) < min(z,d))
        for wrong in (self.plan, self.trial, dict(self.base, tool_version='other')):
            with self.assertRaises(ValueError): apply_release(wrong)

    def test_changed_bytes_or_exaggerated_validation_scope_reject(self):
        changes = [lambda p:p.update(beta62_runtime_gameplay_validated=False),
            lambda p:p.update(beta62_exact_executable_gameplay_validated=True),
            lambda p:p.update(beta62_kodama_live_injury_validated=True),
            lambda p:p['hooks'][-1].update(asm=p['hooks'][-1]['asm']+'\nnop'),
            lambda p:p['hooks'][-1].update(code_offset=0xF000),
            lambda p:p['targets'].update(soul_familiarity_min=0)]
        for change in changes:
            bad = deepcopy(self.plan); change(bad)
            with self.assertRaises(ValueError): validate_release(bad)
            with self.assertRaises(ValueError): source_plan(bad)

    def test_final_cpu_image_preserves_native_familiarity_transform_and_injury_gates(self):
        for cls, excluded in ((soul.SoulPurgeTests, 'test_layout_exact_parent_and_native_consumers_remain_intact'),
                (kodama.KodamaTests, 'test_parent_sites_fixed_entrypoints_and_aslr_relocations_unchanged')):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                if name == excluded: continue
                with self.subTest(case=name):
                    case = cls(name); case.plan = self.plan
                    getattr(case, name)()


if __name__ == '__main__':
    unittest.main()
