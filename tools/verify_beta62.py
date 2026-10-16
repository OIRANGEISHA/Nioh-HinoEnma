"""Compare the compiled portable payloads against independent assembly."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import ctypes
from ctypes import wintypes

from build_profile import ROOT, assemble, generate, legacy_plans, load_plan


VERSION = '1.0.0-beta.6.2'


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
    expected = dict(product_version=VERSION, file_version='1.0.0.85')
    if not results or any(identity != expected for identity in results):
        raise ValueError('Exact Beta 6.2 EXE product/file version required')
    return expected


def verify(executable: Path, report: Path, preview: bool = False) -> dict:
    plan = load_plan()
    from hinoenma_beta62_release import validate_release
    validate_release(plan)
    if len(plan["hooks"]) != 86 or plan.get("living_weapon_start_bootstrap_revision") != 1 or plan["allocation_size"] != 0x69000 or plan["tool_version"] != "1.0.0-beta.6.2":
        raise ValueError("Expected the complete Beta 6.2 profile")
    if (ROOT / "launcher/Profile.generated.cs").read_text("utf-8") != generate(plan):
        raise ValueError("Generated source differs")
    report.parent.mkdir(parents=True, exist_ok=True)
    targets = {"--self-test": report.with_name("self-tests.json"),
               "--export-payloads": report.with_name("payloads.json"),
               "--export-legacy-payloads": report.with_name("legacy-payloads.json")}
    if preview:
        targets["--preview"] = report.with_name("launcher-preview.png")
    for mode, target in targets.items():
        if target.exists():
            target.unlink()
        completed = subprocess.run([str(executable.resolve()), mode, str(target.resolve())],
                                   capture_output=True, encoding="utf-8", errors="replace", timeout=30,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        if completed.returncode or not target.is_file():
            raise ValueError("Offline executable check failed: " + mode + ": " + completed.stderr)
    self_test = json.loads(targets["--self-test"].read_text("utf-8"))
    if (not self_test["success"] or self_test.get("game_access") is not False
            or self_test["count"] != 30 or len(self_test["checks"]) != 30
            or len(set(self_test["checks"])) != 30):
        raise ValueError("Offline refusal/transaction checks failed")
    exported = json.loads(targets["--export-payloads"].read_text("utf-8"))
    cache, names = {}, set()
    for item in exported:
        key = (item["module"], item["allocation"])
        if key not in cache:
            cache[key] = {h["name"]: h for h in assemble(plan, *key)}
        hook = cache[key][item["name"]]
        if base64.b64decode(item["payload"]) != hook["payload"] or base64.b64decode(item["patch"]) != hook["patched"]:
            raise ValueError("Compiled relocation differs: " + item["name"])
        unique = (*key, item["name"])
        if unique in names:
            raise ValueError("Duplicate relocation comparison")
        names.add(unique)
    if len(cache) != 12 or len(exported) != len(plan["hooks"]) * 12:
        raise ValueError("Incomplete relocation export")
    expected_layouts = {
        (module, ((module + plan["image_size"] + 0xFFFF) & ~0xFFFF) + slot * 0x10000)
        for module in (0x140000000, 0x7FF83AA00000, 0x7FFA01000000)
        for slot in (0, 1, 37, 511)
    }
    if set(cache) != expected_layouts:
        raise ValueError("Relocation layout set differs from the reviewed export")
    previous = {item['tool_version']: item for item in legacy_plans(plan)}
    legacy_exported = json.loads(targets['--export-legacy-payloads'].read_text('utf-8'))
    legacy_cache, legacy_names = {}, set()
    for item in legacy_exported:
        key = (item['version'], item['module'], item['allocation'])
        if key[0] not in previous or key[1:] not in expected_layouts:
            raise ValueError('Unexpected legacy release or relocation layout')
        if key not in legacy_cache:
            legacy_cache[key] = {hook['name']: hook for hook in assemble(previous[key[0]], *key[1:])}
        hook = legacy_cache[key][item['name']]
        if (base64.b64decode(item['payload']) != hook['payload']
                or base64.b64decode(item['patch']) != hook['patched']):
            raise ValueError('Compiled historical relocation differs: ' + item['name'])
        unique = (*key, item['name'])
        if unique in legacy_names:
            raise ValueError('Duplicate historical relocation comparison')
        legacy_names.add(unique)
    if (len(legacy_cache) != len(previous) * 12
            or len(legacy_names) != sum(len(item['hooks']) for item in previous.values()) * 12):
        raise ValueError('Incomplete historical relocation export')
    raw = executable.read_bytes()
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if raw[:2] != b"MZ" or raw[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", raw, pe+4)[0] != 0x8664:
        raise ValueError("Expected Windows x64 PE")
    version_identity = executable_version(executable)
    result = {
        "version": plan["tool_version"], "success": True, "game_access": False, "executable_versions": version_identity,
        "generated_source_matches": True,
        "generated_source_sha256": hashlib.sha256((ROOT/"launcher/Profile.generated.cs").read_bytes()).hexdigest(),
        "profile_sha256": hashlib.sha256((ROOT/"profiles/steam-1.24.8.json").read_bytes()).hexdigest(),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "build_script_sha256": hashlib.sha256((ROOT/'tools/build.ps1').read_bytes()).hexdigest(),
        "launcher_source_files": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT/'launcher').glob('*')) if path.suffix in ('.cs', '.manifest')},
        "self_checks": self_test["count"],
        "payload_comparisons": len(exported), "layout_count": len(cache), "hook_count": len(plan["hooks"]),
        "legacy_hook_counts": [len(item['hooks']) for item in previous.values()],
        "legacy_payload_comparisons": len(legacy_names), "legacy_layout_count": len(legacy_cache),
        "pe_machine": "x64", "executable_bytes": len(raw), "executable_sha256": hashlib.sha256(raw).hexdigest(),
    }
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    verify(args.exe, args.report, args.preview)
