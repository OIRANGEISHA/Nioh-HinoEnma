"""Verify the exact Beta5.5 local build and its gameplay-tested patch basis."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def verify():
    version = read(ROOT / 'version.json')
    plan = load_plan()
    basis = read(ROOT / 'docs/gameplay-basis-beta5.5.json')
    tested = read(ROOT / 'profiles/gameplay-tested-beta5.4.3.json')
    if version['version'] != '1.0.0-beta.5.5' or plan['tool_version'] != version['version']:
        raise ValueError('Exact Beta5.5 identity required')
    if len(plan['hooks']) != 82 or sha(ROOT / 'profiles/gameplay-tested-beta5.4.3.json') != basis['profile_sha256']:
        raise ValueError('Incomplete or changed gameplay basis')
    changed = [key for key in set(plan) | set(tested) if plan.get(key) != tested.get(key)]
    if sorted(changed) != ['stage', 'tool_version']:
        raise ValueError('Unexpected gameplay-tested profile change')
    for name, digest in basis['runtime_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Gameplay-tested runtime source changed: ' + name)
    for name, digest in basis['metadata_only_files'].items():
        text = (ROOT / name).read_text('utf-8')
        text = text.replace('1.0.0-beta.5.5', '1.0.0-beta.5.4.3')
        text = text.replace('local_beta55_abyss_resource_lifetime', 'local_beta543_abyss_resource_lifetime')
        text = text.replace('Beta5.5', 'Beta5.4.3 Local Trial').replace('1.0.0.71', '1.0.0.70')
        if hashlib.sha256(text.strip().encode('utf-8')).hexdigest() != digest:
            raise ValueError('Change exceeds version metadata: ' + name)
    if (ROOT / 'launcher/Profile.generated.cs').read_text('utf-8') != generate(plan):
        raise ValueError('Generated launcher does not match source')
    if (ROOT / 'ct' / version['ct_file']).read_text('utf-8') != ct_source(plan, version['display_version']):
        raise ValueError('Generated CT does not match source')
    layouts = [(base, base + offset)
               for base in (0x140000000, 0x180000000, 0x7FF600000000)
               for offset in (-0x2000000, 0x100000, 0x4000000)]
    comparisons = 0
    for base, allocation in layouts:
        old = assemble(tested, base, allocation)
        new = assemble(plan, base, allocation)
        for left, right in zip(old, new):
            if left['payload'] != right['payload'] or left['patched'] != right['patched']:
                raise ValueError('Gameplay-tested payload or native jump changed: ' + left['name'])
            comparisons += 1
    regression = read(ROOT / 'artifacts/regression-tests.json')
    if (not regression['success'] or regression['game_access'] or regression['tests_run'] != EXPECTED_TESTS
            or regression['failures'] or regression['errors'] or regression['source_files'] != source_files()):
        raise ValueError('Complete unchanged-source regressions required')
    builds = {}
    for configuration in ('Debug', 'Release'):
        directory = ROOT / 'artifacts' / configuration
        selftests = read(directory / 'self-tests.json')
        build = read(directory / 'build.json')
        if (not selftests['success'] or selftests['game_access'] or selftests['count'] != 30
                or len(selftests['checks']) != 30 or build['offline_self_checks'] != 30
                or build['product_version'] != version['version'] or build['file_version'] != version['file_version']
                or build['configuration'] != configuration or build['pe_machine'] != 'x64'):
            raise ValueError('Exact compiled build/self-checks required: ' + configuration)
        executable = directory / ('Nioh-HinoEnma-' + version['version'] + '-windows-x64.exe')
        builds[configuration] = dict(build=build, self_tests=selftests, executable_sha256=sha(executable))
    return dict(success=True, game_access=False, version=version['version'], hook_count=82,
                source_files=source_files(), regression=regression, builds=builds,
                baseline=verify_baseline(),
                tested_candidate_executable_sha256=basis['executable_sha256'],
                payload_equivalence=dict(success=True, hook_specs=82, layout_count=len(layouts),
                                         payload_comparisons=comparisons, patch_comparisons=comparisons,
                                         runtime_source_identical_except_version=True),
                limits=['The versioned Beta5.5 EXE has not repeated candidate gameplay.',
                        'CPU native-call stubs do not substitute for gameplay.',
                        'Abyss boat remains unverified and deferred.'])


if __name__ == '__main__':
    result = verify()
    target = ROOT / 'artifacts/beta55-local-verification.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=str(target), success=True, tests=result['regression']['tests_run'],
                         hooks=82, layouts=9, payload_comparisons=738,
                         release_sha256=result['builds']['Release']['executable_sha256'])))
