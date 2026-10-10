"""Meaningful rejection checks for immutable original60 preservation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify_beta52_baseline import verify,verify_plans


class Beta52BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=json.loads((ROOT/'profiles/baseline-beta5.2.json').read_text('utf-8'))
        cls.current=json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf-8'))

    def test_published_blob_and_720_payloads(self):
        result=verify()
        self.assertEqual(result['payload_comparisons'],720)
        self.assertEqual(result['patch_comparisons'],720)

    def reject(self,change):
        current=deepcopy(self.current);change(current)
        with self.assertRaises(ValueError):verify_plans(self.original,current)

    def test_changed_old_assembly_refused(self):
        self.reject(lambda p:p['hooks'][0].__setitem__('asm',p['hooks'][0]['asm']+'\nnop'))

    def test_changed_old_native_signature_refused(self):
        self.reject(lambda p:p['hooks'][5].__setitem__('original','90'+p['hooks'][5]['original'][2:]))

    def test_changed_old_slot_refused(self):
        self.reject(lambda p:p['hooks'][0].__setitem__('code_offset',1))

    def test_changed_native_target_refused(self):
        key=next(iter(self.original['targets']))
        self.reject(lambda p:p['targets'].__setitem__(key,self.original['targets'][key]+1))

    def test_wrong_count_refused(self):
        self.reject(lambda p:p['hooks'].pop())

    def test_core_layout_change_refused(self):
        self.reject(lambda p:p.__setitem__('data_offset',0xE000))

    def test_native_identity_change_refused(self):
        self.reject(lambda p:p.__setitem__('disk_sha256','0'*64))


if __name__=='__main__':unittest.main()
