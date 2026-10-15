"""Package the verified Beta 6.1.3 EXE and complete local source; no network/game access."""
from datetime import datetime, timezone
import argparse
import hashlib
from pathlib import Path
import shutil

from build_profile import ROOT
from package_beta561_local import entries, raw_json, read, sha, write_zip
from run_beta613_regressions import EXPECTED_TESTS, source_files
from verify_beta613_items import BASE_SHA, CHANGED, ADDED, SOURCE_FILES, TRIAL_SHA, verify_gameplay

VERSION = '1.0.0-beta.6.1.3'
FILE_VERSION = '1.0.0.83'
STEM = 'Nioh-HinoEnma-' + VERSION
EXE = STEM + '-windows-x64.exe'


def package(destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Preserve an existing nonempty release folder')
    version = read(ROOT / 'version.json')
    if (version['version'], version['file_version']) != (VERSION, FILE_VERSION):
        raise ValueError('Exact Beta 6.1.3 version metadata required')
    profile_sha = sha(ROOT / 'profiles/steam-1.24.8.json')
    generated_sha = sha(ROOT / 'launcher/Profile.generated.cs')
    equivalent = read(ROOT / 'artifacts/beta613/item-equivalence.json')
    if (not equivalent['success'] or equivalent['game_access']
            or equivalent['version'] != VERSION or not equivalent['warm_payload_equivalence']
            or equivalent['exact_executable_gameplay_validated']
            or equivalent['live_payload_comparisons'] != 1008
            or equivalent['unchanged_previous_payloads'] != 72
            or equivalent['unchanged_payload_comparisons'] != 864
            or equivalent['unchanged_native_patch_comparisons'] != 984
            or set(equivalent['changed_hooks']) != CHANGED
            or equivalent['trial_profile_sha256'] != TRIAL_SHA
            or equivalent['baseline_profile_sha256'] != BASE_SHA
            or equivalent['source_files'] != SOURCE_FILES
            or set(equivalent['added_hooks']) != ADDED
            or equivalent['added_native_patch_comparisons'] != 24
            or equivalent['profile_sha256'] != profile_sha
            or equivalent['generated_source_sha256'] != generated_sha
            or equivalent['verifier_sha256'] != sha(ROOT / 'tools/verify_beta613_items.py')
            or equivalent['evidence_sha256'] != sha(ROOT / 'docs/beta613-live-payload-identities.json')):
        raise ValueError('Current warm-tested item payload equivalence required')
    for name, digest in equivalent['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Tested runtime source changed: ' + name)
    regressions = read(ROOT / 'artifacts/beta613/regression-tests.json')
    if (not regressions['success'] or regressions['version'] != VERSION or regressions['game_access']
            or regressions['tests_run'] != EXPECTED_TESTS or regressions['failures'] or regressions['errors']
            or regressions['skipped'] or not regressions['tested_source_unchanged']
            or regressions['source_files'] != source_files()):
        raise ValueError('Complete unchanged-source Beta 6.1.3 regressions required')
    builds, checks = {}, {}
    launcher_sources = {path.relative_to(ROOT).as_posix(): sha(path)
        for path in sorted((ROOT / 'launcher').glob('*')) if path.suffix in ('.cs', '.manifest')}
    for config in ('Debug', 'Release'):
        binary = ROOT / 'artifacts/beta613' / config / EXE
        proof = read(binary.parent / 'verification.json')
        build = read(binary.parent / 'build.json')
        if (not proof['success'] or proof['game_access'] or proof['version'] != VERSION
                or proof['self_checks'] != 30 or proof['hook_count'] != 84
                or proof['payload_comparisons'] != 1008 or proof['layout_count'] != 12
                or proof['legacy_payload_comparisons'] != 7536 or proof['legacy_layout_count'] != 108
                or proof['executable_sha256'] != sha(binary) or proof['profile_sha256'] != profile_sha
                or proof['generated_source_sha256'] != generated_sha
                or proof['verifier_sha256'] != sha(ROOT / 'tools/verify_beta613.py')
                or proof['build_script_sha256'] != sha(ROOT / 'tools/build.ps1')
                or proof['launcher_source_files'] != launcher_sources
                or proof['executable_versions'] != dict(product_version=VERSION, file_version=FILE_VERSION)
                or build['configuration'] != config or build['product_version'] != VERSION
                or build['file_version'] != FILE_VERSION or build['offline_self_checks'] != 30):
            raise ValueError('Exact compiled-payload verification required: ' + config)
        builds[config], checks[config] = build, proof
    ct = ROOT / 'ct' / version['ct_file']
    ct_proof = read(ROOT / 'artifacts/beta613/ct-verification.json')
    if (not ct_proof['success'] or ct_proof['game_access'] or ct_proof['version'] != VERSION
            or ct_proof['three_way_payload_comparisons'] != 1008 or ct_proof['native_patch_comparisons'] != 1008
            or ct_proof['ct_sha256'] != sha(ct) or ct_proof['profile_sha256'] != profile_sha
            or ct_proof['generated_source_sha256'] != generated_sha
            or ct_proof['converter_sha256'] != sha(ROOT / 'src/living_weapon_start_ct.py')
            or ct_proof['verifier_sha256'] != sha(ROOT / 'tools/verify_beta613_ct.py')):
        raise ValueError('Current source CT verification required')
    names = ('spell-event-catchup-gameplay.json', 'item-cast-interruption-trial.json',
             'item-recast-lookup-trial.json', 'guardian-sludge-items-trial.json',
             'elemental-resistance-items-trial.json')
    gameplay = {name: read(ROOT / 'docs' / name) for name in names}
    expected_statuses = (
        'warm_runtime_spell_effects_confirmed',
        'warm_trial_user_confirmed_sampled_native_injury_verified',
        'warm_trial_continuous_use_user_confirmed',
        'warm_trial_gameplay_user_confirmed',
        'warm_trial_five_buffs_and_sampled_cast_interruptions_user_confirmed')
    for name, status in zip(names, expected_statuses):
        record = gameplay[name]
        if (record['status'] != status or record.get('user_confirmation_pending', False)
                or record['cold_launch_tested'] or record['release_exe_updated']
                or sha(ROOT / record['source_file']) != record['source_sha256']):
            raise ValueError('Exact retained gameplay evidence required: ' + name)
    if (not gameplay[names[0]]['effects_confirmed_by_user']
            or not gameplay[names[1]]['interrupted_cast_gameplay_confirmed']
            or not gameplay[names[3]]['post_test_all_82_hooks_verified']
            or gameplay[names[3]]['after_recorder_complete']
            or not gameplay[names[4]]['all_five_native_aggregate_changes_observed']
            or not gameplay[names[4]]['all_82_hooks_verified_after_recording']
            or len(gameplay[names[4]]['sampled_injury_evidence']) != 3):
        raise ValueError('Confirmed gameplay and incomplete-recorder boundary required')
    latest_gameplay = verify_gameplay()
    for name in latest_gameplay:
        if equivalent['gameplay_evidence_sha256'].get(name) != sha(ROOT / 'docs' / name):
            raise ValueError('Current gameplay receipt changed: ' + name)
    gameplay.update(latest_gameplay)
    selected = entries()
    selected_by_path = {entry['path']: entry for entry in selected}
    if any(selected_by_path.get(name, {}).get('sha256') != digest
           for name, digest in regressions['source_files'].items()):
        raise ValueError('Source selection differs from the regression-tested snapshot')
    if (selected_by_path[ct.relative_to(ROOT).as_posix()]['sha256'] != ct_proof['ct_sha256']
            or selected_by_path['docs/beta613-live-payload-identities.json']['sha256'] != equivalent['evidence_sha256']):
        raise ValueError('Source archive proof inputs changed during packaging')
    inventory = [{k: v for k, v in row.items() if k != 'raw'} for row in selected]
    inventory_sha = hashlib.sha256(raw_json(inventory)).hexdigest()
    provenance = dict(schema=1, version=VERSION, file_version=FILE_VERSION,
        prepared_utc=datetime.now(timezone.utc).isoformat(), build_origin='local-source-build',
        source_commit=None, source_tree=None, source_inventory_sha256=inventory_sha,
        github_published=False, warm_payload_gameplay_confirmed=True,
        exact_executable_gameplay_validated=False, native_hook_count=84,
        runtime_dependencies=['Windows x64', '.NET Framework 4.x'],
        excluded=['game executable/assets', 'saves', 'raw memory snapshots', 'credentials', 'local Python dependencies'])
    verification = dict(version=VERSION, builds=builds, checks=checks, item_equivalence=equivalent,
        regressions=regressions, ct=ct_proof, gameplay=gameplay,
        original_gameplay_reports_preserved=True)
    info = {
        'source-manifest.json': raw_json(dict(schema=1, version=VERSION,
            source_inventory_sha256=inventory_sha, source_commit=None, source_tree=None, files=inventory)),
        'verification.json': raw_json(verification),
        'build-provenance.json': raw_json(provenance),
    }
    destination.mkdir(parents=True, exist_ok=True)
    published = destination / EXE
    shutil.copyfile(ROOT / 'artifacts/beta613/Release' / EXE, published)
    if sha(published) != checks['Release']['executable_sha256']:
        raise ValueError('Copied EXE differs')
    archive = destination / (STEM + '-source.zip')
    write_zip(archive, [(entry['path'], entry['raw']) for entry in selected]
        + [('build-info/' + name, raw) for name, raw in info.items()], STEM + '-source/')
    for name, source in [('使用说明.txt', ROOT / 'docs/使用说明.txt'),
                         ('键位说明.md', ROOT / 'docs/键位说明.md'),
                         ('release-notes.md', ROOT / 'docs/releases' / (VERSION + '.md'))]:
        (destination / name).write_bytes(source.read_bytes())
    assets = [dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path)) for path in (published, archive)]
    manifest = dict(**provenance, assets=assets, source_files=len(selected),
        source_archive_every_member_verified=True, regressions=EXPECTED_TESTS,
        ct_in_source_only=True, ct_direct_activation_gameplay_tested=False)
    (destination / 'release-manifest.json').write_bytes(raw_json(manifest))
    checksum_paths = [published, archive, destination / '使用说明.txt', destination / '键位说明.md',
        destination / 'release-notes.md', destination / 'release-manifest.json']
    (destination / 'SHA256SUMS.txt').write_text(''.join(sha(path) + '  ' + path.name + '\n'
        for path in checksum_paths), 'utf-8')
    print(raw_json(manifest).decode('utf-8'))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    package(parser.parse_args().destination.resolve())
