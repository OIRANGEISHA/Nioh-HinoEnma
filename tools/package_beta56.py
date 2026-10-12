"""Package and verify the exact committed public Beta5.6 EXE/source assets."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from package import git, source_entries, inventory, json_bytes
from verify_beta56 import ROOT, VERSION, metadata, portable_proof, read, sha, validate_report, validate_regressions

INFO_NAMES = {'source-manifest.json', 'components.json', 'verification.json',
              'build-provenance.md', 'SHA256SUMS.txt'}


def require_commit(commit):
    if (not re.fullmatch(r'[0-9a-f]{40}', commit) or git('rev-parse', 'HEAD') != commit
            or git('status', '--porcelain')):
        raise ValueError('Packaging requires the exact clean committed source')
    return git('rev-parse', 'HEAD^{tree}')


def validate_build(build, configuration):
    version = metadata()
    if (build.get('configuration') != configuration or build.get('product_version') != VERSION
            or build.get('file_version') != version['file_version']
            or build.get('offline_self_checks') != 30 or build.get('pe_machine') != 'x64'):
        raise ValueError('Exact compiled product/file identity and30 checks required')


def validate_verification(proof, commit, tree, executable, portable):
    if (proof.get('game_access') is not False or proof.get('version') != VERSION
            or proof.get('source_commit') != commit or proof.get('source_tree') != tree
            or proof.get('beta56_exact_executable_gameplay_repeated') is not False
            or set(proof.get('checks', {})) != {'Debug', 'Release'}
            or set(proof.get('builds', {})) != {'Debug', 'Release'}):
        raise ValueError('Exact source commit/tree/build scope required')
    for configuration in ('Debug', 'Release'):
        local_exe = executable if configuration == 'Release' else ROOT / 'artifacts/Debug' / executable.name
        validate_report(proof['checks'][configuration], local_exe, portable)
        validate_build(proof['builds'][configuration], configuration)
    validate_regressions(proof['regressions'])


def verify_source_archive(archive, commit, executable, portable=None):
    version = metadata()
    tree = require_commit(commit)
    entries = source_entries(commit)
    prefix = 'Nioh-HinoEnma-' + VERSION + '-source/'
    expected = {prefix + e['path'] for e in entries} | {prefix + 'build-info/' + n for n in INFO_NAMES}
    portable = portable or portable_proof()
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(expected) or set(names) != expected or z.testzip() is not None:
            raise ValueError('Source archive missing/duplicate/unselected/corrupt members')
        for entry in entries:
            raw = z.read(prefix + entry['path'])
            raw.decode('utf-8')
            if raw != entry['raw'] or len(raw) != entry['bytes']:
                raise ValueError('Source archive differs from reviewed commit: ' + entry['path'])
            member = z.getinfo(prefix + entry['path'])
            if member.create_system != 3 or member.external_attr >> 16 != int(entry['mode'], 8):
                raise ValueError('Source file mode differs: ' + entry['path'])
        for name in INFO_NAMES:
            member = z.getinfo(prefix + 'build-info/' + name)
            if member.create_system != 3 or member.external_attr >> 16 != 0o100644:
                raise ValueError('Build-info file mode differs: ' + name)
        manifest = json.loads(z.read(prefix + 'build-info/source-manifest.json'))
        if (manifest.get('version') != VERSION or manifest.get('source_commit') != commit
                or manifest.get('source_tree') != tree or manifest.get('files') != inventory(entries)):
            raise ValueError('Archive source manifest differs from exact commit/tree')
        components = json.loads(z.read(prefix + 'build-info/components.json'))
        if (components.get('version') != VERSION or components.get('source_commit') != commit
                or components.get('native_hook_count') != 82
                or components.get('standalone_exe') is not True):
            raise ValueError('Archive runtime/component identity differs')
        verification = json.loads(z.read(prefix + 'build-info/verification.json'))
        validate_verification(verification, commit, tree, executable, portable)
        checksum = sha(executable) + '  ' + executable.name + '\n'
        if z.read(prefix + 'build-info/SHA256SUMS.txt').decode('utf-8') != checksum:
            raise ValueError('Distributed EXE checksum differs')
        if json.loads(z.read(prefix + 'version.json')) != version:
            raise ValueError('Archive publication version differs')
        provenance = z.read(prefix + 'build-info/build-provenance.md').decode('utf-8')
        for value in (commit, tree, sha(executable), version['tag']):
            if value not in provenance:
                raise ValueError('Archive provenance identity incomplete')
    return dict(success=True, source_archive_verified=True, source_commit=commit,
        source_tree=tree, source_files=len(entries), executable_sha256=sha(executable),
        archive_sha256=sha(archive), source_archive_crc_and_every_member_verified=True)


def package(commit, build_origin, publisher, workflow_url):
    version = metadata()
    tree = require_commit(commit)
    if build_origin == 'github-actions':
        if (publisher != 'github-actions[bot]'
                or not re.fullmatch(r'https://github.com/OIRANGEISHA/Nioh-HinoEnma/actions/runs/[0-9]+', workflow_url)):
            raise ValueError('CI build provenance identity differs')
    elif build_origin != 'local-source-build':
        raise ValueError('Unselected build origin')
    notes = ROOT / 'docs/releases' / (VERSION + '.md')
    if not notes.is_file():
        raise ValueError('Reviewed Beta5.6 release notes required')
    stem = 'Nioh-HinoEnma-' + VERSION
    executable = ROOT / 'artifacts/Release' / (stem + '-windows-x64.exe')
    checks = {c: read(ROOT / 'artifacts' / c / 'verification.json') for c in ('Debug', 'Release')}
    builds = {c: read(ROOT / 'artifacts' / c / 'build.json') for c in ('Debug', 'Release')}
    regressions = read(ROOT / 'artifacts/regression-tests.json')
    portable = portable_proof()
    verification = dict(version=VERSION, source_commit=commit, source_tree=tree, game_access=False,
        checks=checks, builds=builds, regressions=regressions,
        beta56_exact_executable_gameplay_repeated=False,
        build_origin=build_origin, publisher=publisher, workflow_url=workflow_url)
    validate_verification(verification, commit, tree, executable, portable)
    entries = source_entries(commit)
    destination = ROOT / 'artifacts/dist'
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Do not overwrite prepared immutable release assets')
    destination.mkdir(parents=True, exist_ok=True)
    published = destination / executable.name
    shutil.copyfile(executable, published)
    provenance = '\n'.join([
        '# ' + version['display_version'] + ' build provenance', '',
        '- Repository: https://github.com/' + version['repository'],
        '- Source commit: ' + commit, '- Source tree: ' + tree,
        '- Release tag: ' + version['tag'] + ' (annotated; immutable after publication)',
        '- Release Owner: ' + version['release_owner'], '- Build origin: ' + build_origin,
        '- Publisher: ' + publisher, '- Workflow: ' + workflow_url,
        '- Prepared UTC: ' + datetime.now(timezone.utc).isoformat(timespec='seconds'),
        '- EXE SHA-256: ' + sha(executable), '',
        str(regressions['tests_run']) + ' exact-source regressions; Debug and Release each passed30 compiled checks.',
        'Each compiled EXE matched984 current payloads at12 layouts and7536 prior payloads at108 version/layout pairs.',
        'The immutable Beta5.2 historical basis and the source-scoped current changes were verified separately.',
        'All82 current payloads and native patches matched both the guide candidate and accepted Beta5.5.1 at9 ASLR layouts (738 comparisons for each basis).',
        'The original Beta5.5.1 EXE gameplay receipt is retained unchanged in docs/guide-restart-gameplay.json.',
        'This Beta5.6 EXE has version-only equivalent runtime payloads; a new exact-file gameplay test is not claimed.',
        'CI attestation, when generated, identifies the exact build/asset bytes and does not replace code signing or gameplay testing.',
        'All build and package verification is offline; no game access.', ''])
    info = {
        'source-manifest.json': json_bytes(dict(schema=1, version=VERSION, source_commit=commit,
            source_tree=tree, files=inventory(entries))),
        'verification.json': json_bytes(verification),
        'components.json': json_bytes(dict(version=VERSION, source_commit=commit,
            native_hook_count=82, standalone_exe=True,
            runtime_dependencies=['Windows x64', 'Windows .NET Framework', 'Win32 APIs'],
            development_dependencies_file='requirements-dev.txt', credits='NOTICE.md',
            excluded=['Nioh executable/assets', 'private memory dumps', 'credentials',
                      'Python runtime', 'development dependencies'],
            authenticode=builds['Release'].get('authenticode_status'))),
        'build-provenance.md': provenance.encode('utf-8'),
        'SHA256SUMS.txt': (sha(published) + '  ' + published.name + '\n').encode('utf-8'),
    }
    archive = destination / (stem + '-source.zip')
    prefix = stem + '-source/'
    timestamp = datetime.fromisoformat(version['release_date'] + 'T00:00:00+00:00')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        contents = [(e['path'], e['raw'], int(e['mode'], 8)) for e in entries]
        contents += [('build-info/' + name, raw, 0o100644) for name, raw in info.items()]
        for name, raw, mode in contents:
            item = zipfile.ZipInfo(prefix + name, timestamp.timetuple()[:6])
            item.create_system = 3
            item.external_attr = mode << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    checked = verify_source_archive(archive, commit, published, portable)
    assets = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in (published, archive)]
    manifest = dict(version=VERSION, source_commit=commit, source_tree=tree, assets=assets,
        verification=checked, build_origin=build_origin, publisher=publisher)
    (ROOT / 'artifacts/release-manifest.json').write_bytes(json_bytes(manifest))
    release_notes = notes.read_text('utf-8') + '\n\n## Exact release assets\n\n'
    release_notes += 'Source commit: ' + commit + '; source tree: ' + tree + '.\n\n'
    release_notes += str(regressions['tests_run']) + ' exact-source regressions passed. Complete source/build receipts are embedded in the source ZIP.\n\n'
    release_notes += 'Build origin: ' + build_origin + '. The original Beta5.5.1 exact EXE gameplay result remains separate; this Beta5.6 EXE was verified for identical runtime payloads and has not repeated exact-file gameplay.\n\n'
    release_notes += '| Asset | Bytes | SHA-256 |\n| --- | ---: | --- |\n'
    for asset in assets:
        release_notes += '| ' + asset['name'] + ' | ' + str(asset['bytes']) + ' | ' + asset['sha256'] + ' |\n'
    release_notes += '\nThe source ZIP contains every reviewed Git-tracked UTF-8 source file and five build-info records. Private research, game resources, credentials and build dependencies are excluded.\n'
    (ROOT / 'artifacts/release-notes.md').write_text(release_notes, encoding='utf-8', newline='\n')
    print(json.dumps(manifest))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--build-origin', default='local-source-build')
    parser.add_argument('--publisher', default='local')
    parser.add_argument('--workflow-url', default='not applicable: local build')
    parser.add_argument('--verify-source-zip', type=Path)
    parser.add_argument('--exe', type=Path)
    args = parser.parse_args()
    if args.verify_source_zip:
        if args.exe is None:
            parser.error('--exe required for source archive verification')
        print(json.dumps(verify_source_archive(args.verify_source_zip, args.source_commit, args.exe)))
    elif args.exe:
        parser.error('--exe is only for source archive verification')
    else:
        package(args.source_commit, args.build_origin, args.publisher, args.workflow_url)
