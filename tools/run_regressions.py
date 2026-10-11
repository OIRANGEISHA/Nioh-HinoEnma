"""Run all public source regressions and record the exact tested source hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TESTS = 203


def source_files():
    paths = [path for directory in ('src', 'tools', 'tests')
             for path in (ROOT/directory).glob('*.py')]
    paths += list((ROOT/'launcher').glob('*.cs'))
    paths += [ROOT/'version.json', ROOT/'profiles/steam-1.24.8.json', ROOT/'profiles/legacy-beta5.4.json']
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def run(report):
    for directory in ('tools', 'src', 'tests'):
        sys.path.insert(0, str(ROOT/directory))
    hashes = source_files()
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_*.py'))
    success = result.wasSuccessful() and result.testsRun == EXPECTED_TESTS and hashes == source_files()
    receipt = dict(success=success, game_access=False, tests_run=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors), source_files=hashes)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='source_files'}))
    if not success:
        raise SystemExit('Complete unchanged-source regression run required')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT/'artifacts/regression-tests.json')
    run(parser.parse_args().report)
