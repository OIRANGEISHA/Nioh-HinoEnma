"""Package verified local Beta5.6.3 files; no GitHub or game process access."""
from datetime import datetime, timezone
import argparse
import hashlib
from pathlib import Path
import shutil
from build_profile import ROOT
from run_beta563_regressions import source_files
from package_beta561_local import entries, raw_json, read, sha, write_zip

VERSION = '1.0.0-beta.5.6.3'
STEM = 'Nioh-HinoEnma-' + VERSION
EXE = STEM + '-windows-x64.exe'


def package(destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Preserve existing nonempty release folder')
    version = read(ROOT / 'version.json')
    if (version['version'], version['file_version']) != (VERSION, '1.0.0.78'):
        raise ValueError('Exact Beta5.6.3 version metadata required')
    profile_sha = sha(ROOT / 'profiles/steam-1.24.8.json')
    generated_sha = sha(ROOT / 'launcher/Profile.generated.cs')
    growth = read(ROOT / 'artifacts/growth750-equivalence.json')
    if (not growth['success'] or growth['game_access'] or not growth['warm_payload_equivalence']
            or growth['live_payload_comparisons'] != 984 or growth['unchanged_payload_comparisons'] != 972
            or growth['profile_sha256'] != profile_sha or growth['generated_source_sha256'] != generated_sha
            or growth['source_sha256'] != sha(ROOT / 'src/hinoenma_growth750.py')
            or growth['verifier_sha256'] != sha(ROOT / 'tools/verify_beta563_growth.py')):
        raise ValueError('Exact live-tested payload equivalence required')
    regressions = read(ROOT / 'artifacts/beta563-regression-tests.json')
    if (not regressions['success'] or regressions['version'] != VERSION or regressions['game_access']
            or regressions['tests_run'] != 248 or regressions['failures'] or regressions['errors']
            or regressions['skipped'] or not regressions['tested_source_unchanged']
            or regressions['source_files'] != source_files()):
        raise ValueError('Complete unchanged-source248 regressions required')
    builds, checks = {}, {}
    for config in ('Debug', 'Release'):
        binary = ROOT / 'artifacts' / config / EXE
        proof = read(binary.parent / 'verification.json')
        build = read(binary.parent / 'build.json')
        if (not proof['success'] or proof['game_access'] or proof['version'] != VERSION
                or proof['self_checks'] != 30 or proof['hook_count'] != 82
                or proof['payload_comparisons'] != 984 or proof['layout_count'] != 12
                or proof['legacy_payload_comparisons'] != 7536 or proof['legacy_layout_count'] != 108
                or proof['executable_sha256'] != sha(binary) or proof['profile_sha256'] != profile_sha
                or proof['generated_source_sha256'] != generated_sha
                or proof['executable_versions'] != dict(product_version=VERSION, file_version='1.0.0.78')
                or build['configuration'] != config or build['product_version'] != VERSION
                or build['file_version'] != '1.0.0.78' or build['offline_self_checks'] != 30):
            raise ValueError('Current compiled-payload verification required: ' + config)
        builds[config], checks[config] = build, proof
    ct = ROOT / 'ct' / version['ct_file']
    ct_proof = read(ROOT / 'artifacts/ct-verification.json')
    if (not ct_proof['success'] or ct_proof['game_access'] or ct_proof['version'] != VERSION
            or ct_proof['three_way_payload_comparisons'] != 984 or ct_proof['native_patch_comparisons'] != 984
            or ct_proof['ct_sha256'] != sha(ct) or ct_proof['profile_sha256'] != profile_sha
            or ct_proof['generated_source_sha256'] != generated_sha
            or ct_proof['converter_sha256'] != sha(ROOT / 'src/living_weapon_start_ct.py')
            or ct_proof['verifier_sha256'] != sha(ROOT / 'tools/verify_beta563_ct.py')):
        raise ValueError('Current CT verification required')
    game = read(ROOT / 'docs/growth750-beta563-gameplay.json')
    if (not game['user_confirmed_movement_and_J_I'] or game['exact_executable_gameplay_validated']
            or game['growth_source_sha256'] != growth['source_sha256']
            or game['validated_trial_profile_sha256'] != growth['trial_profile_sha256']):
        raise ValueError('Accurate warm gameplay evidence required')
    selected = entries()
    inventory = [{k: v for k, v in row.items() if k != 'raw'} for row in selected]
    inventory_sha = hashlib.sha256(raw_json(inventory)).hexdigest()
    provenance = dict(schema=1, version=VERSION, file_version='1.0.0.78',
        prepared_utc=datetime.now(timezone.utc).isoformat(), build_origin='local-source-build',
        source_commit=None, source_tree=None, source_inventory_sha256=inventory_sha,
        github_published=False, warm_payload_gameplay_confirmed=True,
        exact_executable_gameplay_validated=False, native_hook_count=82,
        runtime_dependencies=['Windows x64', '.NET Framework4.x'],
        excluded=['game executable/assets', 'saves', 'raw memory snapshots', 'credentials', 'local Python dependencies'])
    verification = dict(version=VERSION, builds=builds, checks=checks, growth=growth,
        regressions=regressions, ct=ct_proof, gameplay=game)
    info = {
        'source-manifest.json': raw_json(dict(schema=1, version=VERSION,
            source_inventory_sha256=inventory_sha, source_commit=None, source_tree=None, files=inventory)),
        'verification.json': raw_json(verification),
        'build-provenance.json': raw_json(provenance),
    }
    destination.mkdir(parents=True, exist_ok=True)
    published = destination / EXE
    shutil.copyfile(ROOT / 'artifacts/Release' / EXE, published)
    shutil.copyfile(ct, destination / ct.name)
    if sha(published) != checks['Release']['executable_sha256'] or sha(destination / ct.name) != ct_proof['ct_sha256']:
        raise ValueError('Copied executable or CT differs')
    archive = destination / (STEM + '-source.zip')
    write_zip(archive, [(e['path'], e['raw']) for e in selected]
        + [('build-info/' + name, raw) for name, raw in info.items()], STEM + '-source/')
    (destination / '使用说明.txt').write_bytes((ROOT / 'docs/使用说明.txt').read_bytes())
    (destination / '键位说明.md').write_bytes((ROOT / 'docs/键位说明.md').read_bytes())
    (destination / 'release-notes.md').write_bytes((ROOT / 'docs/releases' / (VERSION + '.md')).read_bytes())
    (destination / '修复与验证记录.json').write_bytes(raw_json(verification))
    assets = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p))
        for p in (published, archive, destination / ct.name)]
    complete = destination / '飞缘魔_Beta5.6.3_完整包.zip'
    names = [a['name'] for a in assets] + ['使用说明.txt', '键位说明.md', 'release-notes.md', '修复与验证记录.json']
    write_zip(complete, [(name, (destination / name).read_bytes()) for name in names])
    assets.append(dict(name=complete.name, bytes=complete.stat().st_size, sha256=sha(complete)))
    (destination / 'SHA256SUMS.txt').write_text(''.join(a['sha256'] + '  ' + a['name'] + '\n' for a in assets), 'utf-8')
    manifest = dict(**provenance, assets=assets, source_files=len(selected),
        source_archive_every_member_verified=True, complete_archive_every_member_verified=True,
        regressions=248, ct_direct_activation_gameplay_tested=False)
    (destination / 'release-manifest.json').write_bytes(raw_json(manifest))
    print(raw_json(manifest).decode('utf-8'))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    package(parser.parse_args().destination.resolve())
