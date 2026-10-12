"""Package the exact cold-tested Beta5.6.1 EXE and verified local UTF-8 source."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from build_profile import ROOT
from run_beta561_regressions import source_files

VERSION = '1.0.0-beta.5.6.1'
STEM = 'Nioh-HinoEnma-' + VERSION
EXE_NAME = STEM + '-windows-x64.exe'
EXCLUDED = {'.git', '.devdeps', '.venv', '__pycache__', 'artifacts', 'build-info',
            'research', 'references', 'release', 'dist'}
FORBIDDEN_SUFFIXES = {'.exe', '.zip', '.pdb', '.dmp', '.bin', '.pyc', '.pyo',
                      '.dll', '.user', '.log', '.jpg', '.png'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read(path):
    return json.loads(path.read_text('utf-8'))


def entries():
    result = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part.casefold() in EXCLUDED for part in rel.parts):
            continue
        if (path.is_symlink() or path.suffix.lower() in FORBIDDEN_SUFFIXES
                or path.name.startswith('.env')):
            raise ValueError('Unexpected private/binary source entry: ' + str(rel))
        raw = path.read_bytes()
        raw.decode('utf-8')
        result.append(dict(path=rel.as_posix(), bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(), mode='100644', raw=raw))
    if not result:
        raise ValueError('Empty source selection')
    return result


def write_zip(path, contents, prefix=''):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, raw in contents:
            item = zipfile.ZipInfo(prefix + name, (2026, 10, 12, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(path) as z:
        expected = {prefix + name: raw for name, raw in contents}
        if (z.testzip() is not None or len(z.namelist()) != len(expected)
                or set(z.namelist()) != set(expected)):
            raise ValueError('Archive inventory/CRC mismatch')
        for name, raw in expected.items():
            item = z.getinfo(name)
            if (z.read(name) != raw or item.create_system != 3
                    or item.external_attr >> 16 != 0o100644):
                raise ValueError('Archive byte/mode mismatch: ' + name)


def package(destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Preserve existing immutable package assets')
    version = read(ROOT/'version.json')
    if version['version'] != VERSION or version['file_version'] != '1.0.0.74':
        raise ValueError('Exact Beta5.6.1 metadata required')
    game = read(ROOT/'docs/living-weapon-beta561-gameplay.json')
    exe = ROOT/'artifacts/Release'/EXE_NAME
    if (not game['success'] or not game['exact_executable_gameplay_validated']
            or game['temporary_runtime_patch'] or game['manual_resource_binding']
            or game['executable_sha256'] != sha(exe)
            or game['profile_sha256'] != sha(ROOT/'profiles/steam-1.24.8.json')):
        raise ValueError('Exact standalone cold gameplay receipt required')
    regressions = read(ROOT/'artifacts/beta561-regression-tests.json')
    if (not regressions['success'] or regressions['version'] != VERSION
            or regressions['game_access'] or regressions['tests_run'] != 240
            or regressions['failures'] or regressions['errors'] or regressions['skipped']
            or not regressions['tested_source_unchanged']
            or regressions['source_files'] != source_files()):
        raise ValueError('Complete unchanged-source 240 regressions required')
    checks = {c: read(ROOT/'artifacts'/c/'verification.json') for c in ('Debug', 'Release')}
    builds = {c: read(ROOT/'artifacts'/c/'build.json') for c in ('Debug', 'Release')}
    for config, proof in checks.items():
        binary = ROOT/'artifacts'/config/EXE_NAME
        if (not proof['success'] or proof['game_access'] or proof['version'] != VERSION
                or proof['self_checks'] != 30 or proof['payload_comparisons'] != 984
                or proof['legacy_payload_comparisons'] != 7536 or proof['hook_count'] != 82
                or proof['layout_count'] != 12 or proof['legacy_layout_count'] != 108
                or proof['executable_sha256'] != sha(binary)
                or proof['profile_sha256'] != sha(ROOT/'profiles/steam-1.24.8.json')
                or proof['generated_source_sha256'] != sha(ROOT/'launcher/Profile.generated.cs')
                or builds[config]['configuration'] != config
                or builds[config]['product_version'] != VERSION
                or builds[config]['file_version'] != '1.0.0.74'):
            raise ValueError('Exact current compiled payload verification required: ' + config)
    ct = ROOT/'ct'/version['ct_file']
    ct_proof = read(ROOT/'artifacts/ct-verification.json')
    if (not ct_proof['success'] or ct_proof['game_access']
            or ct_proof['three_way_payload_comparisons'] != 984
            or ct_proof['native_patch_comparisons'] != 984
            or ct_proof['ct_sha256'] != sha(ct)
            or ct_proof['profile_sha256'] != game['profile_sha256']
            or ct_proof['generated_source_sha256'] != checks['Release']['generated_source_sha256']
            or ct_proof['converter_sha256'] != sha(ROOT/'src/living_weapon_start_ct.py')
            or ct_proof['verifier_sha256'] != sha(ROOT/'tools/verify_beta561_ct.py')):
        raise ValueError('Exact production CT verification required')
    selected = entries()
    inventory = [{k: v for k, v in entry.items() if k != 'raw'} for entry in selected]
    source_hash = hashlib.sha256(raw_json(inventory)).hexdigest()
    provenance = dict(schema=1, version=VERSION, build_origin='local-source-build',
        prepared_utc=datetime.now(timezone.utc).isoformat(), source_commit=None,
        source_tree=None, source_inventory_sha256=source_hash,
        github_published=False, tag_created=False, exact_tested_executable_preserved=True,
        note='Local reviewed source snapshot; no new Git commit or release claimed. Generated C# text matches cold build; newline normalization only.',
        excluded=['game executable/assets', 'raw memory snapshots', 'credentials', 'bundled Python/dependencies'],
        runtime_dependencies=['Windows x64', '.NET Framework 4.x'],
        native_hook_count=82, allocation_size='0x69000')
    verification = dict(version=VERSION, builds=builds, checks=checks,
        regressions=regressions, ct=ct_proof, gameplay=game,
        cpu_summary=read(ROOT/'docs/living-weapon-beta561-offline.json'))
    info = {
        'source-manifest.json': raw_json(dict(schema=1, version=VERSION, source_commit=None,
            source_tree=None, source_inventory_sha256=source_hash, files=inventory)),
        'verification.json': raw_json(verification),
        'build-provenance.json': raw_json(provenance),
        'SHA256SUMS.txt': (sha(exe) + '  ' + EXE_NAME + '\n' + sha(ct) + '  ' + ct.name + '\n').encode('utf-8'),
    }
    destination.mkdir(parents=True, exist_ok=True)
    published = destination/EXE_NAME
    shutil.copyfile(exe, published)
    shutil.copyfile(ct, destination/ct.name)
    source_archive = destination/(STEM+'-source.zip')
    write_zip(source_archive, [(e['path'], e['raw']) for e in selected]
        + [('build-info/'+name, raw) for name, raw in info.items()], STEM+'-source/')
    assets = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p))
              for p in (published, source_archive, destination/ct.name)]
    sums = ''.join(a['sha256']+'  '+a['name']+'\n' for a in assets).encode('utf-8')
    (destination/'SHA256SUMS.txt').write_bytes(sums)
    (destination/'修复与验证记录.json').write_bytes(raw_json(verification))
    (destination/'使用说明.txt').write_bytes((ROOT/'docs/使用说明.txt').read_bytes())
    (destination/'release-notes.md').write_bytes((ROOT/'docs/releases'/ (VERSION+'.md')).read_bytes())
    complete = destination/'飞缘魔_Beta5.6.1_完整包.zip'
    names = [a['name'] for a in assets] + ['SHA256SUMS.txt', '修复与验证记录.json', '使用说明.txt', 'release-notes.md']
    write_zip(complete, [(name, (destination/name).read_bytes()) for name in names])
    assets.append(dict(name=complete.name, bytes=complete.stat().st_size, sha256=sha(complete)))
    manifest = dict(**provenance, source_files=len(selected), assets=assets,
        source_archive_every_member_verified=True, complete_archive_every_member_verified=True,
        cold_gameplay_validated=True, regressions=240,
        ct_direct_activation_gameplay_tested=False, known_remaining_bug='忍术道具目前无法使用')
    (destination/'release-manifest.json').write_bytes(raw_json(manifest))
    print(json.dumps(manifest, ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    package(parser.parse_args().destination.resolve())
