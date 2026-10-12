"""Reject incomplete compiled exports, stale evidence and unsafe publication inputs."""
from copy import deepcopy
from pathlib import Path
import base64
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_beta56 as verifier
import package_beta56 as packager


class PublicationTests(unittest.TestCase):
    def fixture(self):
        current = dict(tool_version=verifier.VERSION, image_size=0x2000000,
                       hooks=[dict(name='current' + str(i)) for i in range(82)])
        older = [dict(tool_version='old' + str(i), image_size=current['image_size'],
                      hooks=[dict(name='hook' + str(j)) for j in range(n)])
                 for i, n in enumerate(verifier.LEGACY[0])]
        def assembly(plan, module, allocation):
            return [dict(h, payload=b'\x90\xC3', patched=b'\xE9\x01\x02\x03\x04') for h in plan['hooks']]
        exports = [dict(module=m, allocation=a, name=h['name'],
                        payload=base64.b64encode(b'\x90\xC3').decode(),
                        patch=base64.b64encode(b'\xE9\x01\x02\x03\x04').decode())
                   for m, a in verifier.expected_layouts(current) for h in current['hooks']]
        historical = [dict(version=p['tool_version'], module=m, allocation=a,
                        name=h['name'], payload=base64.b64encode(b'\x90\xC3').decode(),
                        patch=base64.b64encode(b'\xE9\x01\x02\x03\x04').decode())
                      for p in older for m, a in verifier.expected_layouts(current) for h in p['hooks']]
        return current, older, assembly, exports, historical

    def check_exports(self, current, older, assembler, exports, historical):
        with patch.object(verifier, 'legacy_plans', return_value=older), patch.object(verifier, 'assemble', side_effect=assembler):
            return verifier.validate_exports(current, exports, historical)

    def test_complete_current_and_all_nine_prior_exports(self):
        result = self.check_exports(*self.fixture())
        self.assertEqual((result['payload_comparisons'], result['layout_count']), (984, 12))
        self.assertEqual((result['legacy_payload_comparisons'], result['legacy_layout_count']), (7536, 108))

    def test_missing_or_duplicate_current_export_refused(self):
        p, old, assembler, current, historical = self.fixture()
        for broken in (current[:-1], current[:-1] + [current[0]]):
            with self.assertRaises(ValueError):
                self.check_exports(p, old, assembler, broken, historical)

    def test_missing_or_duplicate_historical_export_refused(self):
        p, old, assembler, current, historical = self.fixture()
        for broken in (historical[:-1], historical[:-1] + [historical[0]]):
            with self.assertRaises(ValueError):
                self.check_exports(p, old, assembler, current, broken)

    def test_wrong_bytes_name_or_layout_refused(self):
        p, old, assembler, current, historical = self.fixture()
        for key, value in (('payload', 'kA=='), ('patch', 'kA=='), ('name', 'unknown'), ('allocation', 1)):
            broken = deepcopy(current)
            broken[0][key] = value
            with self.assertRaises(ValueError):
                self.check_exports(p, old, assembler, broken, historical)

    def test_unselected_historical_version_refused(self):
        p, old, assembler, current, historical = self.fixture()
        historical[0]['version'] = 'future'
        with self.assertRaises(ValueError):
            self.check_exports(p, old, assembler, current, historical)

    def test_stale_or_partial_regression_receipt_refused(self):
        hashes = {'src/actual.py': 'a' * 64}
        good = dict(success=True, game_access=False, tests_run=verifier.EXPECTED_TESTS,
                    failures=0, errors=0, source_files=hashes)
        with patch.object(verifier, 'source_files', return_value=hashes):
            verifier.validate_regressions(good)
            for field, value in (('tests_run', verifier.EXPECTED_TESTS - 1), ('source_files', {}),
                                 ('game_access', True), ('failures', 1), ('errors', 1)):
                bad = dict(good, **{field: value})
                with self.assertRaises(ValueError):
                    verifier.validate_regressions(bad)

    def test_old_build_or_product_identity_refused(self):
        version = dict(file_version='1.0.0.73')
        good = dict(configuration='Release', product_version=verifier.VERSION,
                    file_version=version['file_version'], offline_self_checks=30, pe_machine='x64')
        with patch.object(packager, 'metadata', return_value=version):
            packager.validate_build(good, 'Release')
            for field, value in (('product_version', '1.0.0-beta.5.5.1'), ('file_version', '1.0.0.72'),
                                 ('offline_self_checks', 29), ('configuration', 'Debug'), ('pe_machine', 'x86')):
                with self.assertRaises(ValueError):
                    packager.validate_build(dict(good, **{field: value}), 'Release')

    def test_dirty_or_wrong_commit_refused(self):
        commit = 'a' * 40
        with patch.object(packager, 'git', side_effect=[commit, '', 'b' * 40]):
            self.assertEqual(packager.require_commit(commit), 'b' * 40)
        for values in ([commit, ' M src/changed.py'], ['c' * 40]):
            with patch.object(packager, 'git', side_effect=values), self.assertRaises(ValueError):
                packager.require_commit(commit)
        with self.assertRaises(ValueError):
            packager.require_commit('HEAD')

    def test_overstated_gameplay_or_missing_build_receipt_refused(self):
        good = dict(game_access=False, version=verifier.VERSION, source_commit='a' * 40,
            source_tree='b' * 40, beta56_exact_executable_gameplay_repeated=False,
            checks={'Debug': {}, 'Release': {}}, builds={'Debug': {}, 'Release': {}}, regressions={})
        with patch.object(packager, 'validate_report'), patch.object(packager, 'validate_build'), patch.object(packager, 'validate_regressions'):
            packager.validate_verification(good, 'a' * 40, 'b' * 40, Path('release.exe'), {})
            for field, value in (('beta56_exact_executable_gameplay_repeated', True),
                                 ('source_commit', 'c' * 40), ('source_tree', 'c' * 40),
                                 ('game_access', True), ('checks', {'Release': {}})):
                with self.assertRaises(ValueError):
                    packager.validate_verification(dict(good, **{field: value}), 'a' * 40, 'b' * 40, Path('release.exe'), {})


if __name__ == '__main__':
    unittest.main()
