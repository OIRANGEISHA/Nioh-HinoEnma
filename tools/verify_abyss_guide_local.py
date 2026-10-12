"""Verify restart EXE/CT against the gameplay-tested guide candidate."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from build_profile import load_plan, generate, ct_source
from hinoenma_abyss_assembly import assemble
from run_regressions import source_files, EXPECTED_TESTS
from verify_beta52_baseline import verify as verify_baseline


def read(path):
    return json.loads(path.read_text('utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    version = read(ROOT / 'version.json')
    plan = load_plan()
    tested_path = ROOT / 'profiles/gameplay-tested-kodama-guide.json'
    tested = read(tested_path)
    if version['version'] != '1.0.0-beta.5.5.1' or plan['tool_version'] != version['version'] or len(plan['hooks']) != 82:
        raise ValueError('Exact isolated restart build required')
    if sha(tested_path) != '280a83ad7e7e1bf2b13ba7f73a8f236336665921b311a1a27fc4304f7b530ab1':
        raise ValueError('Gameplay-tested candidate profile changed')
    for key in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets'):
        if plan[key] != tested[key]:
            raise ValueError('Gameplay-tested layout changed: ' + key)
    if (ROOT / 'launcher/Profile.generated.cs').read_text('utf-8') != generate(plan):
        raise ValueError('Compiled source generation differs from the current plan')
    if (ROOT / 'ct' / version['ct_file']).read_text('utf-8') != ct_source(plan, version['display_version']):
        raise ValueError('Current CT generation differs from the current plan')
    comparisons = 0
    layouts = [(base, base + delta) for base in (0x140000000, 0x180000000, 0x7FF600000000)
               for delta in (-0x2000000, 0x100000, 0x4000000)]
    for base, allocation in layouts:
        old, new = assemble(tested, base, allocation), assemble(plan, base, allocation)
        for a, b in zip(old, new):
            if a['payload'] != b['payload'] or a['patched'] != b['patched']:
                raise ValueError('Restart build changes a gameplay-tested payload: ' + a['name'])
            comparisons += 1
    regression = read(ROOT / 'artifacts/regression-tests.json')
    if (not regression['success'] or regression['game_access'] or regression['tests_run'] != EXPECTED_TESTS
            or regression['failures'] or regression['errors'] or regression['source_files'] != source_files()):
        raise ValueError('Full unchanged-source regressions required')
    builds = {}
    for configuration in ('Debug', 'Release'):
        directory = ROOT / 'artifacts' / configuration
        tests, build = read(directory / 'self-tests.json'), read(directory / 'build.json')
        if (not tests['success'] or tests['game_access'] or tests['count'] != 30
                or build['offline_self_checks'] != 30 or build['configuration'] != configuration
                or build['product_version'] != version['version'] or build['file_version'] != version['file_version']):
            raise ValueError('Compiled restart identity/self-test mismatch')
        exe = directory / ('Nioh-HinoEnma-' + version['version'] + '-windows-x64.exe')
        builds[configuration] = dict(build=build, self_tests=tests, executable_sha256=sha(exe))
    return dict(success=True, game_access=False, version=version['version'], hook_count=82,
        source_files=source_files(), regression=regression, builds=builds, baseline=verify_baseline(),
        tested_profile_sha256=sha(tested_path), actual_restart_gameplay_validated=False,
        payload_equivalence=dict(success=True, layout_count=9, payload_comparisons=comparisons,
                                 patch_comparisons=comparisons, source_reconstructed=True))


if __name__ == '__main__':
    result = verify()
    output = ROOT / 'artifacts/guide-restart-local-verification.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(report=str(output), success=True, tests=result['regression']['tests_run'],
        release_sha256=result['builds']['Release']['executable_sha256'],
        actual_restart_gameplay_validated=False)))
