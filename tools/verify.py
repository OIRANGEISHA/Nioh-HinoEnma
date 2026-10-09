"""Compare the compiled portable payloads against independent assembly."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from build_profile import ROOT, assemble, generate, load_plan


def verify(executable: Path, report: Path, preview: bool = False) -> dict:
    plan = load_plan()
    if len(plan["hooks"]) != 55:
        raise ValueError("Expected the reviewed 55-hook profile")
    if (ROOT / "launcher/Profile.generated.cs").read_text("utf-8") != generate(plan):
        raise ValueError("Generated source differs")
    report.parent.mkdir(parents=True, exist_ok=True)
    targets = {"--self-test": report.with_name("self-tests.json"),
               "--export-payloads": report.with_name("payloads.json")}
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
            or self_test["count"] != 22 or len(self_test["checks"]) != 22
            or len(set(self_test["checks"])) != 22):
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
    raw = executable.read_bytes()
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if raw[:2] != b"MZ" or raw[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", raw, pe+4)[0] != 0x8664:
        raise ValueError("Expected Windows x64 PE")
    result = {
        "version": plan["tool_version"], "success": True, "game_access": False,
        "generated_source_matches": True, "self_checks": self_test["count"],
        "payload_comparisons": len(exported), "layout_count": len(cache), "hook_count": len(plan["hooks"]),
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
