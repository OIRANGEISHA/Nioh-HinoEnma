"""Reject stale or incomplete offline evidence before immutable publication."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package import source_hashes, validate_build_check, validate_source_proofs


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.hashes = source_hashes()
        self.build = dict(success=True, game_access=False, version='1.0.0-beta.5.3.1',
            generated_source_matches=True, self_checks=28, hook_count=71,
            payload_comparisons=852, layout_count=12, legacy_hook_counts=[55,59,60,70],
            legacy_payload_comparisons=2928, legacy_layout_count=48, pe_machine='x64',
            profile_sha256=self.hashes['profile_sha256'],
            generated_source_sha256=self.hashes['generated_source_sha256'])
        baseline = dict(success=True, game_access=False, hook_count=60,
            template_comparisons=60, fixup_comparisons=60, layout_count=12,
            payload_comparisons=720, patch_comparisons=720,
            baseline_commit='b5a4d9811efa64042587a9b01c71712cc9283a8c',
            baseline_git_blob='4d3efc5d57146fc323ec8e7fbbfbd049eaa1033e',
            baseline_profile_sha256=self.hashes['baseline_profile_sha256'],
            verifier_sha256=self.hashes['baseline_verifier_sha256'])
        menu = dict(success=True, game_access=False, tests_run=41,
            byte_comparisons=4280, cpu_comparisons=15880, aslr_layouts=12,
            reload_source_files=self.hashes['reload_source_files'],
            source_sha256=self.hashes['source_sha256'], test_sha256=self.hashes['test_sha256'],
            verifier_sha256=self.hashes['menu_verifier_sha256'])
        for report in (baseline, menu):
            report.update({key:self.hashes[key] for key in ('profile_sha256','generated_source_sha256')})
        self.proofs = dict(beta52_baseline=baseline, menu_preview=menu)

    def check_build(self, report):
        validate_build_check(report, '1.0.0-beta.5.3.1',
            {key:self.hashes[key] for key in ('profile_sha256','generated_source_sha256')})

    def test_complete_exact_source_evidence(self):
        self.check_build(self.build)
        validate_source_proofs(self.proofs, self.hashes)

    def test_old_60_hook_release_counts_rejected(self):
        self.build.update(self_checks=26, hook_count=60, payload_comparisons=720)
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_missing_beta52_legacy_rejected(self):
        self.build.update(legacy_hook_counts=[55,59], legacy_payload_comparisons=1368, legacy_layout_count=24)
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_wrong_version_rejected(self):
        self.build['version']='1.0.0-beta.5.2'
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_stale_generated_source_rejected(self):
        self.build['generated_source_sha256']='0'*64
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_partial_layout_build_rejected(self):
        self.build['layout_count']=3
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_game_access_build_rejected(self):
        self.build['game_access']=True
        with self.assertRaises(ValueError): self.check_build(self.build)

    def test_baseline_blob_or_commit_rejected(self):
        for key in ('baseline_commit','baseline_git_blob','baseline_profile_sha256'):
            proofs=deepcopy(self.proofs);proofs['beta52_baseline'][key]='0'*40
            with self.assertRaises(ValueError): validate_source_proofs(proofs,self.hashes)

    def test_partial_baseline_comparisons_rejected(self):
        self.proofs['beta52_baseline']['patch_comparisons']=719
        with self.assertRaises(ValueError): validate_source_proofs(self.proofs,self.hashes)

    def test_menu_count_or_cpu_proof_rejected(self):
        for key in ('tests_run','byte_comparisons','cpu_comparisons','aslr_layouts'):
            proofs=deepcopy(self.proofs);proofs['menu_preview'][key]-=1
            with self.assertRaises(ValueError): validate_source_proofs(proofs,self.hashes)

    def test_menu_source_test_or_verifier_hash_rejected(self):
        for key in ('source_sha256','test_sha256','verifier_sha256'):
            proofs=deepcopy(self.proofs);proofs['menu_preview'][key]='0'*64
            with self.assertRaises(ValueError): validate_source_proofs(proofs,self.hashes)

    def test_source_proof_profile_or_game_access_rejected(self):
        for proof in ('beta52_baseline','menu_preview'):
            for key,value in (('profile_sha256','0'*64),('game_access',True)):
                proofs=deepcopy(self.proofs);proofs[proof][key]=value
                with self.assertRaises(ValueError): validate_source_proofs(proofs,self.hashes)

    def test_changed_reload_source_hash_rejected(self):
        proofs=deepcopy(self.proofs)
        key=next(iter(proofs['menu_preview']['reload_source_files']))
        proofs['menu_preview']['reload_source_files'][key]='0'*64
        with self.assertRaises(ValueError):validate_source_proofs(proofs,self.hashes)


if __name__ == '__main__':
    unittest.main()
