"""Release identity, split native-reader slots and execution of the final image."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import base64, hashlib, json, struct, sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta613_plan as load_plan,load_beta612_plan,source_plan,assemble,relocation_specs,legacy_plans,validate_layout
from hinoenma_beta613_release import apply_release,trial_plan,validate_release,CONFIRMED,TRIAL_CANONICAL_SHA256,digest
from verify_beta613_items import BASE_SHA,CHANGED,ADDED,verify_gameplay
from verify_beta56 import expected_layouts
import test_nine_talismans_portable as nine
import test_soul_release_portable as soul
import test_dispersal_reuse_portable as reuse

class Beta613ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=load_beta612_plan();cls.trial=trial_plan(cls.base);cls.plan=load_plan()

    def test_release_and_original_gameplay_evidence_identities(self):
        meta=json.loads((ROOT/'profiles/baseline-beta6.1.3-version.json').read_text('utf8'))
        self.assertEqual((meta['version'],meta['file_version']),('1.0.0-beta.6.1.3','1.0.0.83'))
        self.assertEqual(hashlib.sha256((ROOT/'profiles/baseline-beta6.1.2.json').read_bytes()).hexdigest(),BASE_SHA)
        self.assertEqual(digest(self.trial),TRIAL_CANONICAL_SHA256)
        for key in CONFIRMED:
            self.assertTrue(self.trial[key]['live_confirmation_pending']);self.assertFalse(self.plan[key]['live_confirmation_pending'])
        self.assertFalse(self.plan['beta613_exact_executable_gameplay_validated'])
        self.assertTrue(self.plan['beta613_runtime_gameplay_validated'])
        self.assertEqual(len(verify_gameplay()),3)

    def test_all_84_payloads_match_tested_trial_at_twelve_layouts(self):
        for module,allocation in sorted(expected_layouts(self.plan)):
            old={h['name']:h for h in assemble(self.base,module,allocation)}
            trial,new=(assemble(p,module,allocation) for p in (self.trial,self.plan))
            self.assertEqual(len(new),84)
            self.assertEqual({h['name'] for h in new if h['name'] in old and h['payload']!=old[h['name']]['payload']},CHANGED)
            self.assertEqual({h['name'] for h in new if h['name'] not in old},ADDED)
            for a,b in zip(trial,new):
                for field in ('name','payload','patched','original','site','target','code_offset','code_capacity'):self.assertEqual(a[field],b[field])

    def test_all_generated_relocations_exclude_data_tables(self):
        specs=relocation_specs(self.plan)
        for module,allocation in sorted(expected_layouts(self.plan)):
            for spec,reference in zip(specs,assemble(self.plan,module,allocation)):
                raw=bytearray(base64.b64decode(spec['template']))
                for fix in spec['fixups']:
                    if fix['kind']==0:value=struct.pack('<Q',allocation+self.plan['data_offset'])
                    elif fix['kind']==2:value=struct.pack('<Q',module+fix['target'])
                    else:
                        self.assertEqual(fix['kind'],1)
                        value=struct.pack('<i',module+fix['target']-allocation-spec['code_offset']-fix['next'])
                    raw[fix['offset']:fix['offset']+len(value)]=value
                self.assertEqual(bytes(raw),reference['payload'])

    def test_rebuild_is_pure_and_all_slots_are_nonoverlapping(self):
        before=deepcopy(self.plan);validate_release(self.plan);validate_layout(self.plan)
        self.assertEqual(self.plan,before);self.assertEqual(source_plan(self.plan),self.plan)
        self.assertEqual(legacy_plans(self.base),legacy_plans(self.plan))
        ranges=sorted((h['code_offset'],h['code_offset']+h['code_capacity']) for h in self.plan['hooks'])
        self.assertTrue(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])))
        for a,b in ranges:
            self.assertLessEqual(b,self.plan['allocation_size'])
            for c,d in self.plan['protected_data_pages']:self.assertFalse(max(a,c)<min(b,d))

    def test_wrong_confirmation_or_native_view_is_rejected(self):
        changes=[lambda p:p.update(beta613_exact_executable_gameplay_validated=True),
            lambda p:p.update(beta613_runtime_gameplay_validated=False),
            lambda p:p['hooks'][-1].update(original='90'*10),
            lambda p:p['hooks'][-2].update(code_offset=0xF000),
            lambda p:p['hooks'][52].update(code_capacity=0x1000),
            lambda p:p['targets'].update(soul_familiarity_min=0),
            lambda p:p['hooks'][0].update(asm=p['hooks'][0]['asm']+'\nnop'),
            lambda p:p[CONFIRMED[-1]].update(live_confirmation_pending=True)]
        for change in changes:
            bad=deepcopy(self.plan);change(bad)
            with self.assertRaises(ValueError):validate_release(bad)
            with self.assertRaises(ValueError):source_plan(bad)

    def test_promotion_requires_exact_parent_and_is_not_repeatable(self):
        before=deepcopy(self.base);self.assertEqual(apply_release(self.base),self.plan);self.assertEqual(before,self.base)
        for wrong in (self.plan,self.trial,dict(self.base,tool_version='other')):
            with self.assertRaises(ValueError):apply_release(wrong)

    def test_final_release_executes_all_soul_and_existing_item_contracts(self):
        # Historical layout assertions belong to their frozen trial, while all
        # behavior/ABI cases below execute the complete final 84-hook image.
        for cls,excluded in ((soul.SoulTests,()),(nine.NineTalismansTests,('test_native_sites_and_owned_capacity_unchanged',)),
                             (reuse.DispersalReuseTests,('test_layout_and_fixed_carrier_regions',))):
            cls.setUpClass()
            with patch.object(cls,'plan',self.plan), patch.object(reuse,'GapFixture',nine.Gap):
                for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                    if name in excluded or 'layout' in name or 'capacity' in name or 'source_guard' in name:continue
                    with self.subTest(suite=cls.__name__,case=name):getattr(cls(name),name)()

if __name__=='__main__':unittest.main()
