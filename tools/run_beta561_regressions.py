"""Run every public regression against one unchanged Beta5.6.1 source tree.

The inherited runner and its Beta5.6 count remain historical identities.
This runner never accesses a game process and refuses skips or source changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0-beta.5.6.1'
EXPECTED_TESTS = 240


def source_files():
    paths = []
    for directory in ('src', 'tools', 'tests', 'launcher', 'profiles'):
        paths.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix.lower() in ('.py', '.json', '.cs', '.ps1', '.manifest'))
    paths.append(ROOT / 'version.json')
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths))}


def run(report):
    for directory in ('tools', 'src', 'tests'):
        sys.path.insert(0, str(ROOT / directory))
    metadata = json.loads((ROOT / 'version.json').read_text('utf-8'))
    if metadata.get('version') != VERSION:
        raise ValueError('Exact Beta5.6.1 source metadata required')
    hashes = source_files()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
    declared_tests = suite.countTestCases()
    if declared_tests != EXPECTED_TESTS:
        raise ValueError('Complete current regression inventory required: ' + str(declared_tests))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    unchanged = hashes == source_files()
    success = (result.wasSuccessful() and result.testsRun == EXPECTED_TESTS
               and not result.skipped and unchanged)
    receipt = dict(schema=1, version=VERSION, success=success, game_access=False,
                   tests_run=result.testsRun, expected_tests=EXPECTED_TESTS,
                   failures=len(result.failures), errors=len(result.errors),
                   skipped=len(result.skipped), tested_source_unchanged=unchanged,
                   source_files=hashes,
                   failure_details=[dict(test=str(test), traceback=details)
                                    for test, details in result.failures],
                   error_details=[dict(test=str(test), traceback=details)
                                  for test, details in result.errors])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                      encoding='utf-8', newline='\n')
    print(json.dumps({key: value for key, value in receipt.items()
                      if key not in ('source_files', 'failure_details', 'error_details')}))
    if not success:
        raise SystemExit('Complete unchanged-source regression run required')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path,
                        default=ROOT / 'artifacts/beta561-regression-tests.json')
    run(parser.parse_args().report)
