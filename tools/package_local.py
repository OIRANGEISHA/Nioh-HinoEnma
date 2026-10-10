"""Package an exactly verified UTF-8 source snapshot and standalone EXE.

This creates local files only. A local snapshot has no new Git commit or tag;
it never claims that a GitHub Release or CI attestation exists.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
import shutil
import zipfile
from package import ROOT,sha256,json_bytes,source_hashes,validate_build_check,validate_source_proofs
from build_profile import load_plan,generate

EXCLUDED={'.git','.devdeps','.venv','artifacts','research','release','references','__pycache__','build-info'}
INFO_NAMES={'source-manifest.json','verification.json','build-provenance.md','SHA256SUMS.txt','components.json'}


def source_files():
    rows=[]
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if any(part.casefold() in EXCLUDED for part in rel.parts):continue
        if path.is_symlink():raise ValueError('No source symlinks: '+str(rel))
        if path.is_dir():continue
        if (path.name.startswith('.env') or path.suffix.lower() in
                ('.exe','.zip','.dll','.pdb','.log','.dmp','.bin','.pyc','.pyo','.user')):
            raise ValueError('Unselected binary/private file: '+str(rel))
        raw=path.read_bytes();raw.decode('utf-8')
        rows.append(dict(path=rel.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),raw=raw))
    return rows


def verify_archive(archive,executable):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if not names or len(names)!=len(set(names)) or z.testzip() is not None:raise ValueError('Corrupt source ZIP')
        prefix=names[0].split('/')[0]+'/'
        manifest=json.loads(z.read(prefix+'build-info/source-manifest.json'))
        expected={prefix+x['path'] for x in manifest['files']}|{prefix+'build-info/'+n for n in INFO_NAMES}
        if set(names)!=expected:raise ValueError('Unexpected or missing source ZIP files')
        for row in manifest['files']:
            p=PurePosixPath(row['path'])
            if p.is_absolute() or '..' in p.parts or '\\' in row['path']:raise ValueError('Unsafe source path')
            raw=z.read(prefix+row['path']);raw.decode('utf-8')
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                raise ValueError('Source manifest mismatch: '+row['path'])
        files=manifest['files']
        identity=hashlib.sha256(json_bytes(dict(files=files))).hexdigest()
        if identity!=manifest['source_snapshot_sha256'] or manifest['source_commit'] is not None:
            raise ValueError('Local snapshot identity mismatch')
        v=json.loads(z.read(prefix+'version.json'))
        proof=json.loads(z.read(prefix+'build-info/verification.json'))
        release=proof['checks']['Release']
        if v['version']!=manifest['version'] or release['executable_sha256']!=sha256(executable):
            raise ValueError('Distributed EXE/source identity mismatch')
        if z.read(prefix+'build-info/SHA256SUMS.txt').decode('utf-8')!=sha256(executable)+'  '+executable.name+'\n':
            raise ValueError('Distributed EXE checksum mismatch')
    return dict(source_files=len(files),source_snapshot_sha256=identity,executable_sha256=sha256(executable))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--verify-source-zip',type=Path)
    parser.add_argument('--exe',type=Path)
    args=parser.parse_args()
    if args.verify_source_zip:
        if args.exe is None:raise ValueError('--exe required')
        print(json.dumps(verify_archive(args.verify_source_zip,args.exe)));return
    if args.exe:raise ValueError('--exe is only for ZIP verification')
    version=json.loads((ROOT/'version.json').read_text('utf-8'));plan=load_plan()
    if plan['tool_version']!=version['version'] or len(plan['hooks'])!=71:
        raise ValueError('Exact Beta5.3.1 source profile required')
    if (ROOT/'launcher/Profile.generated.cs').read_text('utf-8')!=generate(plan):
        raise ValueError('Stale generated launcher')
    hashes=source_hashes();reports={};builds={}
    stem='Nioh-HinoEnma-'+version['version']
    for config in ('Debug','Release'):
        directory=ROOT/'artifacts'/config
        check=json.loads((directory/'verification.json').read_text('utf-8'))
        build=json.loads((directory/'build.json').read_text('utf-8'))
        executable=directory/(stem+'-windows-x64.exe')
        validate_build_check(check,version['version'],{k:hashes[k] for k in ('profile_sha256','generated_source_sha256')})
        if (check['executable_sha256']!=sha256(executable) or build['product_version']!=version['version']
                or build['file_version']!=version['file_version'] or build['offline_self_checks']!=28
                or build['configuration']!=config):raise ValueError('Stale build: '+config)
        reports[config]=check;builds[config]=build
    proofs={name:json.loads((ROOT/'artifacts'/file).read_text('utf-8')) for name,file in
        (('beta52_baseline','baseline-verification.json'),('menu_preview','menu-preview-verification.json'))}
    validate_source_proofs(proofs,hashes)
    regression=json.loads((ROOT/'artifacts/regression-tests.json').read_text('utf-8'))
    if not regression.get('success') or regression.get('game_access') is not False or regression['tests_run']!=134:
        raise ValueError('Complete source regressions required')
    rows=source_files();inventory=[{k:v for k,v in x.items() if k!='raw'} for x in rows]
    identity=hashlib.sha256(json_bytes(dict(files=inventory))).hexdigest()
    destination=(args.destination or ROOT/'artifacts/dist-local').resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('Do not overwrite prepared local release')
    destination.mkdir(parents=True,exist_ok=True)
    executable=destination/'飞缘魔启动工具.exe'
    shutil.copyfile(ROOT/'artifacts/Release'/(stem+'-windows-x64.exe'),executable)
    manifest=dict(version=version['version'],source_commit=None,source_tree=None,
        build_origin='local-source-snapshot',baseline=json.loads((ROOT/'baseline-source.json').read_text('utf-8')),
        source_snapshot_sha256=identity,files=inventory)
    info={
        'source-manifest.json':json_bytes(manifest),
        'verification.json':json_bytes(dict(game_access=False,checks=reports,source_proofs=proofs,regressions=regression)),
        'components.json':json_bytes(dict(version=version['version'],native_hook_count=71,
            runtime=['Windows x64','.NET Framework 4.x'],standalone_exe=True,
            excluded=['Nioh executable/assets','game dumps','Python runtime','development dependencies'],
            development_dependencies_file='requirements-dev.txt',credits='NOTICE.md',
            authenticode=builds['Release']['authenticode_status'])),
        'SHA256SUMS.txt':(sha256(executable)+'  '+executable.name+'\n').encode('utf-8'),
        'build-provenance.md':('\n'.join([
            '# '+version['display_version']+' local build','',
            'Source snapshot SHA-256: '+identity,
            'EXE SHA-256: '+sha256(executable),
            'Baseline Git commit: '+manifest['baseline']['baseline_commit'],
            'Prepared UTC: '+datetime.now(timezone.utc).isoformat(timespec='seconds'),'',
            'No new Git commit, tag, GitHub Release, or CI attestation is claimed.',
            'Debug and Release: 28 self-checks, 852 current and 2928 legacy payload comparisons each.',
            '41 portable menu tests; 134 source regressions; no game access during these checks.',
            'The private menu trial passed visible mist, framing, idle, status reopen and title reload.',
            'The packaged EXE has not yet been enabled in a fresh game process.',
            'Rebuild and verify using docs/BUILD.md.'])+'\n').encode('utf-8')}
    archive=destination/(stem+'-source.zip');prefix=stem+'-source/'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for row in rows:z.writestr(prefix+row['path'],row['raw'])
        for name,raw in info.items():z.writestr(prefix+'build-info/'+name,raw)
    result=verify_archive(archive,executable)
    shutil.copyfile(ROOT/'docs/使用说明.txt',destination/'使用说明.txt')
    result.update(version=version['version'],local_only=True,destination=str(destination),
        assets=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha256(p)) for p in (executable,archive)])
    (ROOT/'artifacts/local-release-manifest.json').write_bytes(json_bytes(result))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
