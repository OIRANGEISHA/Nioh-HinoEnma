"""Package only the verified Beta5.5 local EXE and complete UTF-8 source."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile
from verify_beta55_local import ROOT, verify, sha, read

EXCLUDED = {'.git', '.devdeps', '.venv', '__pycache__', 'artifacts', 'research'}
FORBIDDEN = {'.exe', '.dll', '.pdb', '.zip', '.dmp', '.bin', '.pyc', '.pyo', '.log', '.user'}


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def source_inventory():
    result = []
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(part.casefold() in EXCLUDED for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError('No source symlinks: ' + str(rel))
        if path.is_dir():
            continue
        if path.suffix.lower() in FORBIDDEN or path.name.startswith('.env'):
            raise ValueError('Unselected binary/private file: ' + str(rel))
        raw = path.read_bytes()
        raw.decode('utf-8')
        result.append(dict(path=rel.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    return result


def verify_archive(archive, executable):
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if not names or len(names) != len(set(names)) or bundle.testzip() is not None:
            raise ValueError('Invalid or duplicate source ZIP members')
        prefix = 'Nioh-HinoEnma-1.0.0-beta.5.5-source/'
        manifest = json.loads(bundle.read(prefix + 'build-info/source-manifest.json'))
        inventory = manifest['files']
        info = ['source-manifest.json', 'verification.json', 'build-provenance.md']
        if set(names) != {prefix + row['path'] for row in inventory} | {prefix + 'build-info/' + name for name in info}:
            raise ValueError('Unexpected or missing ZIP member')
        hashes = {}
        for row in inventory:
            path = PurePosixPath(row['path'])
            if path.is_absolute() or '..' in path.parts or '\\' in row['path']:
                raise ValueError('Unsafe source member')
            raw = bundle.read(prefix + row['path'])
            raw.decode('utf-8')
            hashes[row['path']] = hashlib.sha256(raw).hexdigest()
            if len(raw) != row['bytes'] or hashes[row['path']] != row['sha256']:
                raise ValueError('Source hash/size mismatch: ' + row['path'])
        proof = json.loads(bundle.read(prefix + 'build-info/verification.json'))
        if not proof['success'] or proof['game_access'] or proof['hook_count'] != 82 or proof['regression']['tests_run'] != 218:
            raise ValueError('Incomplete package proof')
        if any(hashes.get(name) != expected for name, expected in proof['source_files'].items()):
            raise ValueError('Proof/source identity mismatch')
        if (manifest['source_commit'] is not None or manifest['source_tree'] is not None
                or manifest['version'] != '1.0.0-beta.5.5'
                or manifest['source_snapshot_sha256'] != hashlib.sha256(encode(dict(files=inventory))).hexdigest()
                or manifest['executable_sha256'] != sha(executable)
                or proof['builds']['Release']['executable_sha256'] != sha(executable)):
            raise ValueError('Invalid local source/EXE provenance')
    return dict(source_files=len(inventory), source_snapshot_sha256=manifest['source_snapshot_sha256'],
                executable_sha256=sha(executable), archive_sha256=sha(archive))


def package(destination):
    proof = verify()
    inventory = source_inventory()
    if destination.exists():
        raise ValueError('Keep existing deliveries; destination already exists')
    destination.mkdir(parents=True)
    executable = destination / '飞缘魔启动工具_Beta5.5.exe'
    shutil.copy2(ROOT / 'artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.5-windows-x64.exe', executable)
    manifest = dict(version='1.0.0-beta.5.5', source_commit=None, source_tree=None,
                    build_origin='local-source-snapshot', created_utc=datetime.now(timezone.utc).isoformat(),
                    files=inventory, executable_sha256=sha(executable),
                    source_snapshot_sha256=hashlib.sha256(encode(dict(files=inventory))).hexdigest())
    prefix = 'Nioh-HinoEnma-1.0.0-beta.5.5-source/'
    archive = destination / 'Nioh-HinoEnma-1.0.0-beta.5.5-source.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for row in inventory:
            raw = (ROOT / row['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('Source changed during packaging')
            bundle.writestr(prefix + row['path'], raw)
        bundle.writestr(prefix + 'build-info/source-manifest.json', encode(manifest))
        bundle.writestr(prefix + 'build-info/verification.json', encode(proof))
        bundle.writestr(prefix + 'build-info/build-provenance.md',
            '# Local Beta 5.5 provenance\n\nNo new source commit, public tag, GitHub Release or CI attestation is claimed. '
            'The gameplay-tested candidate and versioned Beta5.5 EXE have separate checksums. '
            'Their82 payloads and native jumps match at nine ASLR layouts. '
            'Abyss boat remains unverified and deferred.\n')
    checked = verify_archive(archive, executable)
    if inventory != source_inventory():
        raise ValueError('Source changed after packaging')
    usage = destination / '使用说明.txt'
    shutil.copy2(ROOT / 'docs/使用说明.txt', usage)
    checksum = '\n'.join(sha(path) + '  ' + path.name for path in (executable, archive, usage)) + '\n'
    (destination / 'SHA256SUMS.txt').write_text(checksum, encoding='utf-8')
    receipt = dict(success=True, game_access=False, version='1.0.0-beta.5.5',
                   destination=str(destination), **checked, current_source_matches_archive=True,
                   github_published=False, usage_sha256=sha(usage))
    (destination / 'package-verification.json').write_bytes(encode(receipt))
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--verify-source-zip', type=Path)
    parser.add_argument('--exe', type=Path)
    args = parser.parse_args()
    if args.verify_source_zip and args.exe:
        print(json.dumps(verify_archive(args.verify_source_zip, args.exe)))
    elif args.destination and not args.exe and not args.verify_source_zip:
        package(args.destination.resolve())
    else:
        parser.error('Choose destination or verify-source-zip with exe')
