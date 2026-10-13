"""Run the complete public Beta6 regression inventory on unchanged source.

Historical tests retain their frozen input profiles. New release checks also
execute the published Beta6 payload chain. No test accesses a game process.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0-beta.6'
EXPECTED_TESTS = 291


def source_files():
    paths = []
    for directory in ('src', 'tools', 'tests', 'launcher', 'profiles'):
        paths.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix.lower() in ('.py', '.json', '.cs', '.ps1', '.manifest'))
    paths.append(ROOT / 'version.json')
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths))}


def test_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_ids(item)
        else:
            yield item.id()


def run(report):
    for directory in ('tools', 'src', 'tests'):
        sys.path.insert(0, str(ROOT / directory))
    metadata = json.loads((ROOT / 'version.json').read_text('utf-8'))
    if (metadata.get('version'), metadata.get('file_version')) != (VERSION, '1.0.0.79'):
        raise ValueError('Exact Beta6 source metadata required')
    hashes = source_files()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
    inventory = sorted(test_ids(suite))
    if len(inventory) != EXPECTED_TESTS or len(set(inventory)) != EXPECTED_TESTS:
        raise ValueError('Complete nonduplicate regression inventory required: ' + str(len(inventory)))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    unchanged = hashes == source_files()
    success = (result.wasSuccessful() and result.testsRun == EXPECTED_TESTS
               and not result.skipped and unchanged)
    source_digest = hashlib.sha256(json.dumps(hashes, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()
    receipt = dict(schema=1, version=VERSION, success=success, game_access=False,
        tests_run=result.testsRun, expected_tests=EXPECTED_TESTS,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        tested_source_unchanged=unchanged, source_tree_sha256=source_digest,
        source_files=hashes, test_inventory=inventory,
        module_counts=dict(sorted(Counter(name.split('.')[0] for name in inventory).items())),
        scope='Public source transforms, x64 CPU fixtures, ABI/fallback/owner/resource guards, '
              'frozen historical regressions, Beta6 payload integration and publication evidence rejection; '
              'no native game process, item effects, inventory or rendered gameplay executed.',
        failure_details=[dict(test=str(test), traceback=details) for test, details in result.failures],
        error_details=[dict(test=str(test), traceback=details) for test, details in result.errors])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                      encoding='utf-8', newline='\n')
    print(json.dumps({key: value for key, value in receipt.items()
        if key not in ('source_files', 'test_inventory', 'failure_details', 'error_details')}))
    if not success:
        raise SystemExit('Complete unchanged-source regression run required')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'artifacts/beta6-regression-tests.json')
    run(parser.parse_args().report)
