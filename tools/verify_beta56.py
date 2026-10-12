"""Verify the exact public Beta5.6 source and compiled offline payloads.

No game process or proprietary resource is opened. The historical gameplay
receipt applies to its original Beta5.5.1 EXE, not to a rebuilt Beta5.6 EXE.
"""
from __future__ import annotations
import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / name) for name in ('src', 'tools')]
from build_profile import assemble, ct_source, generate, legacy_plans, load_plan
from run_regressions import EXPECTED_TESTS, source_files
from verify_beta52_baseline import verify as verify_baseline

VERSION = '1.0.0-beta.5.6'
CHECKS = (30, 82, 984, 12)
LEGACY = ([55, 59, 60, 70, 71, 71, 80, 81, 81], 7536, 108)
BASES = {
    'profiles/gameplay-tested-kodama-guide.json':
        '280a83ad7e7e1bf2b13ba7f73a8f236336665921b311a1a27fc4304f7b530ab1',
    'profiles/gameplay-tested-beta5.5.1.json':
        '34324ce6558db94f419dd5342a1362889a08f7796b81782532a1bccc13126c2b',
}
GAMEPLAY_EXE_SHA256 = 'f6b3b9543a5c6426a86d3740754daa178a011573988993a0483a77c3938328b4'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text('utf-8'))


def executable_version(path):
    """Read the exact file's Win32 version resource, independently of build.json."""
    api = ctypes.WinDLL('version', use_last_error=True)
    size = api.GetFileVersionInfoSizeW
    size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    size.restype = wintypes.DWORD
    get = api.GetFileVersionInfoW
    get.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    get.restype = wintypes.BOOL
    query = api.VerQueryValueW
    query.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR,
                     ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    query.restype = wintypes.BOOL
    ignored = wintypes.DWORD()
    length = size(str(path.resolve()), ctypes.byref(ignored))
    if not length:
        raise ValueError('EXE has no Win32 version resource')
    data = ctypes.create_string_buffer(length)
    if not get(str(path.resolve()), 0, length, data):
        raise ValueError('Could not read EXE version resource')
    pointer, count = ctypes.c_void_p(), wintypes.UINT()
    if not query(data, '\\VarFileInfo\\Translation', ctypes.byref(pointer), ctypes.byref(count)) or count.value % 4:
        raise ValueError('EXE version translations are incomplete')
    translations = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_ushort))
    results = []
    for index in range(count.value // 4):
        prefix = '\\StringFileInfo\\%04x%04x\\' % (translations[index*2], translations[index*2+1])
        identity = {}
        for name, key in (('ProductVersion', 'product_version'), ('FileVersion', 'file_version')):
            value, chars = ctypes.c_void_p(), wintypes.UINT()
            if not query(data, prefix + name, ctypes.byref(value), ctypes.byref(chars)) or not value.value or not chars.value:
                raise ValueError('EXE product/file version string missing')
            identity[key] = ctypes.wstring_at(value.value, chars.value).rstrip('\0')
        results.append(identity)
    expected = dict(product_version=VERSION, file_version='1.0.0.73')
    if not results or any(identity != expected for identity in results):
        raise ValueError('Exact Beta5.6 EXE product/file version required')
    return expected


def metadata():
    version = read(ROOT / 'version.json')
    expected = dict(version=VERSION, tag='v' + VERSION, file_version='1.0.0.73',
        repository='OIRANGEISHA/Nioh-HinoEnma', release_owner='OIRANGEISHA',
        ct_file='Nioh_HinoEnma_1.24.8_Beta5_6.CT', channel='beta',
        local_package_only=False, abyss_actions_revision=3, abyss_cancel_revision=1,
        abyss_resource_lifetime_revision=1, abyss_guide_revision=1,
        gameplay_basis_version='1.0.0-beta.5.5.1', beta56_exact_executable_gameplay_repeated=False)
    if any(version.get(k) != v for k, v in expected.items()):
        raise ValueError('Exact authorized Beta5.6 publication metadata required')
    return version


def expected_layouts(plan):
    return {(module, ((module + plan['image_size'] + 0xFFFF) & ~0xFFFF) + slot * 0x10000)
        for module in (0x140000000, 0x7FF83AA00000, 0x7FFA01000000)
        for slot in (0, 1, 37, 511)}


def validate_exports(plan, current, historical):
    """Check every exported name/layout/byte, including immutable legacy profiles."""
    layouts = expected_layouts(plan)
    plans = {VERSION: plan, **{p['tool_version']: p for p in legacy_plans(plan)}}
    caches, seen = {}, set()
    for legacy, items in ((False, current), (True, historical)):
        allowed = set(plans) - {VERSION} if legacy else {VERSION}
        if not isinstance(items, list):
            raise ValueError('Payload export must be a list')
        for item in items:
            version = item['version'] if legacy else VERSION
            layout = (item['module'], item['allocation'])
            if version not in allowed or layout not in layouts:
                raise ValueError('Unselected export identity/layout')
            key = (version, *layout)
            if key not in caches:
                caches[key] = {h['name']: h for h in assemble(plans[version], *layout)}
            hook = caches[key].get(item['name'])
            identity = (*key, item['name'])
            if hook is None or identity in seen:
                raise ValueError('Missing, unknown or duplicate exported hook')
            if (base64.b64decode(item['payload'], validate=True) != hook['payload']
                    or base64.b64decode(item['patch'], validate=True) != hook['patched']):
                raise ValueError('Compiled payload or native patch differs: ' + item['name'])
            seen.add(identity)
        wanted = {(v, *layout, h['name']) for v in allowed for layout in layouts
                  for h in plans[v]['hooks']}
        got = {i for i in seen if i[0] in allowed}
        if got != wanted:
            raise ValueError('Incomplete compiled export coverage')
    counts = [len(p['hooks']) for p in legacy_plans(plan)]
    if counts != LEGACY[0] or len(current) != CHECKS[2] or len(historical) != LEGACY[1]:
        raise ValueError('Exact current and prior inventory required')
    return dict(payload_comparisons=len(current), layout_count=len(layouts),
        legacy_hook_counts=counts, legacy_payload_comparisons=len(historical),
        legacy_layout_count=len(counts) * len(layouts))


def portable_proof():
    version, plan = metadata(), load_plan()
    if (plan['tool_version'] != VERSION or len(plan['hooks']) != 82
            or plan['allocation_size'] != 0x55000 or plan['data_offset'] != 0xF000
            or plan.get('local_package_only') is not False):
        raise ValueError('Exact public82 profile and allocation required')
    if (ROOT / 'launcher/Profile.generated.cs').read_text('utf-8') != generate(plan):
        raise ValueError('Current generated launcher differs from the full source chain')
    if (ROOT / 'ct' / version['ct_file']).read_text('utf-8') != ct_source(plan, version['display_version']):
        raise ValueError('Current CT differs from the full source chain')
    receipt = read(ROOT / 'docs/guide-restart-gameplay.json')
    if (receipt.get('version') != '1.0.0-beta.5.5.1'
            or receipt.get('executable_sha256') != GAMEPLAY_EXE_SHA256
            or receipt.get('formal_restart_gameplay_validated') is not True
            or receipt.get('user_confirmed_return_to_shore_movement_and_menu') is not True
            or receipt.get('verified_hooks') != 82):
        raise ValueError('Original exact Beta5.5.1 restart receipt required')
    layouts = [(base, base + delta) for base in (0x140000000, 0x180000000, 0x7FF600000000)
               for delta in (-0x2000000, 0x100000, 0x4000000)]
    current = {layout: assemble(plan, *layout) for layout in layouts}
    basis_proofs = {}
    for name, digest in BASES.items():
        path = ROOT / name
        if sha(path) != digest:
            raise ValueError('Immutable gameplay basis profile changed: ' + name)
        basis = read(path)
        if len(basis['hooks']) != 82:
            raise ValueError('Incomplete gameplay basis')
        for key in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets'):
            if basis[key] != plan[key]:
                raise ValueError('Gameplay-tested layout changed: ' + key)
        comparisons = 0
        for layout in layouts:
            before = assemble(basis, *layout)
            for a, b in zip(before, current[layout]):
                if (a['name'] != b['name'] or a['payload'] != b['payload']
                        or a['patched'] != b['patched']):
                    raise ValueError('A gameplay-tested payload/native patch changed: ' + b['name'])
                comparisons += 1
        basis_proofs[name] = dict(profile_sha256=digest, layout_count=9,
            hook_count=82, payload_comparisons=comparisons, patch_comparisons=comparisons)
    return dict(success=True, game_access=False, current_version=VERSION,
        source_files=source_files(), baseline=verify_baseline(),
        gameplay_basis=basis_proofs, original_restart_receipt_sha256=sha(ROOT / 'docs/guide-restart-gameplay.json'),
        original_gameplay_executable_sha256=GAMEPLAY_EXE_SHA256,
        beta56_exact_executable_gameplay_repeated=False)


def validate_regressions(receipt):
    if (receipt.get('success') is not True or receipt.get('game_access') is not False
            or type(receipt.get('tests_run')) is not int or receipt['tests_run'] != EXPECTED_TESTS
            or receipt.get('failures') != 0 or receipt.get('errors') != 0
            or receipt.get('source_files') != source_files()):
        raise ValueError('Complete exact-source public regression receipt required')


def validate_report(report, executable, proof):
    if (report.get('success') is not True or report.get('game_access') is not False
            or report.get('version') != VERSION or report.get('generated_source_matches') is not True
            or tuple(report.get(k) for k in ('self_checks', 'hook_count', 'payload_comparisons', 'layout_count')) != CHECKS
            or tuple(report.get(k) for k in ('legacy_hook_counts', 'legacy_payload_comparisons', 'legacy_layout_count')) != LEGACY
            or report.get('pe_machine') != 'x64' or report.get('portable_proof') != proof
            or report.get('profile_sha256') != sha(ROOT / 'profiles/steam-1.24.8.json')
            or report.get('generated_source_sha256') != sha(ROOT / 'launcher/Profile.generated.cs')
            or report.get('executable_sha256') != sha(executable)
            or report.get('executable_bytes') != executable.stat().st_size
            or report.get('executable_version') != executable_version(executable)):
        raise ValueError('Exact current/legacy build and immutable gameplay basis proof required')


def verify(executable, report, preview=False):
    proof = portable_proof()
    plan = load_plan()
    report.parent.mkdir(parents=True, exist_ok=True)
    outputs = {'--self-test': report.with_name('self-tests.json'),
        '--export-payloads': report.with_name('payloads.json'),
        '--export-legacy-payloads': report.with_name('legacy-payloads.json')}
    if preview:
        outputs['--preview'] = report.with_name('launcher-preview.png')
    for mode, path in outputs.items():
        if path.exists():
            path.unlink()
        run = subprocess.run([str(executable.resolve()), mode, str(path.resolve())],
            capture_output=True, encoding='utf-8', errors='replace', timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if run.returncode or not path.is_file():
            raise ValueError('Compiled offline check failed: ' + mode + ': ' + run.stderr)
    checks = read(outputs['--self-test'])
    if (checks.get('success') is not True or checks.get('game_access') is not False
            or checks.get('count') != 30 or len(checks.get('checks', [])) != 30
            or len(set(checks['checks'])) != 30):
        raise ValueError('Complete30 compiled transaction/refusal checks required')
    export = validate_exports(plan, read(outputs['--export-payloads']), read(outputs['--export-legacy-payloads']))
    raw = executable.read_bytes()
    pe = struct.unpack_from('<I', raw, 0x3C)[0]
    if raw[:2] != b'MZ' or raw[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', raw, pe+4)[0] != 0x8664:
        raise ValueError('Expected x64 Windows PE')
    if proof['source_files'] != source_files():
        raise ValueError('Source changed during verification')
    result = dict(success=True, game_access=False, version=VERSION, generated_source_matches=True,
        self_checks=30, hook_count=82, pe_machine='x64', executable_bytes=len(raw),
        executable_version=executable_version(executable),
        executable_sha256=sha(executable), profile_sha256=sha(ROOT / 'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT / 'launcher/Profile.generated.cs'), portable_proof=proof, **export)
    validate_report(result, executable, proof)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'portable_proof'}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    verify(args.exe, args.report, args.preview)
