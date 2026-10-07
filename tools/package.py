"""Package only reviewed Beta assets and record exact build provenance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--build-origin", choices=("local", "github-actions"), default="local")
    parser.add_argument("--publisher", default="OIRANGEISHA")
    parser.add_argument("--workflow-url", default="Not applicable (local validation)")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        raise ValueError("A full reviewed source commit is required")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    if head != args.source_commit or dirty:
        raise ValueError("Packaging requires the exact source commit and a clean tree")
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    stem = "Nioh-HinoEnma-" + version["version"]
    release = ROOT / "artifacts/Release"
    executable = release / (stem + "-windows-x64.exe")
    reports, builds = {}, {}
    for configuration in ("Debug", "Release"):
        directory = ROOT / "artifacts" / configuration
        report = json.loads((directory / "verification.json").read_text("utf-8"))
        build = json.loads((directory / "build.json").read_text("utf-8"))
        config_exe = directory / executable.name
        if (not report["success"] or report["game_access"] or report["self_checks"] != 12
                or report["payload_comparisons"] != 252 or report["hook_count"] != 21
                or report["version"] != version["version"]
                or report["executable_sha256"] != sha256(config_exe)
                or build["product_version"] != version["version"]
                or build["file_version"] != version["file_version"]):
            raise ValueError("Build or verification metadata does not match: " + configuration)
        reports[configuration], builds[configuration] = report, build
    destination = ROOT / "artifacts/dist"
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Release output is not empty; do not overwrite a prepared asset set")
    published_exe = destination / executable.name
    shutil.copyfile(executable, published_exe)
    archive = destination / (stem + "-windows-x64.zip")
    timestamp = datetime.fromisoformat(version["release_date"] + "T00:00:00+00:00")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path, name in ((executable, "飞缘魔启动工具.exe"), (ROOT / "docs/使用说明.txt", "使用说明.txt")):
            entry = zipfile.ZipInfo(name, timestamp.timetuple()[:6])
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            zipped.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    ct_source = ROOT / "ct/Nioh_HinoEnma_1.24.8_Beta1.CT"
    ct = destination / (stem + ".CT")
    shutil.copyfile(ct_source, ct)
    assets = (published_exe, archive, ct)
    for asset in assets:
        asset.with_name(asset.name + ".sha256").write_text(sha256(asset) + "  " + asset.name + "\n", encoding="utf-8", newline="\n")
    inventory = {
        "schema": 1, "version": version["version"], "source_commit": args.source_commit,
        "runtime_embedded_components": [
            {"name": "Nioh Hino-Enma launcher", "origin": "this repository", "native_hook_count": 21},
        ],
        "platform_dependencies_not_embedded": ["Windows x64", "Windows .NET Framework", "Win32 APIs"],
        "development_dependencies_not_embedded": [
            {"name": "keystone-engine", "version": "0.9.2", "purpose": "independent x64 assembly verification", "license": "GPL-2.0 or commercial (development only)"},
            {"name": "capstone", "version": "5.0.9", "purpose": "instruction decoding and relocation analysis", "license": "BSD (development only)"},
        ],
        "upstream_mechanism": "Bryanyora's Nioh CT character change; see NOTICE.md",
        "not_included": ["Nioh executable or assets", "original third-party CT", "private memory dumps", "Python runtime", "development packages"],
        "authenticode": builds["Release"]["authenticode_status"],
    }
    (destination / (stem + "-components.json")).write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8", newline="\n")
    verification = {"source_commit": args.source_commit, "game_access": False, "checks": reports}
    (destination / (stem + "-verification.json")).write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8", newline="\n")
    provenance = [
        "# " + version["display_version"] + " build provenance", "",
        "- Repository: https://github.com/" + version["repository"],
        "- Source commit: `" + args.source_commit + "`",
        "- Source tree: `" + subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip() + "`",
        "- Release tag: `" + version["tag"] + "` (annotated; never moved after publication)",
        "- Release Owner: " + version["release_owner"],
        "- Build origin: " + args.build_origin,
        "- Prepared asset uploader: " + args.publisher,
        "- Workflow: " + args.workflow_url,
        "- Recorded UTC: " + datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "- Python verification runtime: " + platform.python_version(),
        "- Clean checkout checked before packaging: yes", "",
        "## Build and portable validation", "",
    ]
    for config in ("Debug", "Release"):
        build = builds[config]
        provenance.append("- " + config + ": compiler " + build["compiler_file_version"]
                          + "; Windows " + build["windows_version"] + "; PowerShell " + build["powershell_version"]
                          + "; 12 offline C# checks and 252 payload comparisons passed.")
    provenance += [
        "- All 21 native hooks/signatures match the locally gameplay-tested adaptation; see docs/validation-beta1.json.",
        "- These portable tests do not attach to Nioh and do not replace gameplay verification.",
        "- Windows Authenticode: " + builds["Release"]["authenticode_status"] + ". No protected signing setup is configured.",
        "- CI attestation, when attached, applies to the CI-built EXE, ZIP and CT only; it is not an Authenticode signature or gameplay certification.", "",
        "## Exact prepared bytes", "", "| Asset | Bytes | SHA-256 |", "| --- | ---: | --- |",
    ]
    for asset in assets:
        provenance.append("| `" + asset.name + "` | " + str(asset.stat().st_size) + " | `" + sha256(asset) + "` |")
    provenance += ["", "## Gameplay evidence boundary", "",
        "Known Steam 1.24.08 local play, reported interactions and current revenant summon were tested before this public packaging. See the release notes for item/affix/interaction, CT-direct-enable, weapon-icon and cold first-enable limits. Beta 1 does not claim complete fresh-install or multi-PC coverage.", ""]
    (destination / (stem + "-build-provenance.md")).write_text("\n".join(provenance), encoding="utf-8", newline="\n")
    shutil.copyfile(ROOT / "docs/releases/1.0.0-beta.1.md", ROOT / "artifacts/release-notes.md")
    print(json.dumps({"version": version["version"], "source_commit": args.source_commit,
                      "assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in assets]}))


if __name__ == "__main__":
    main()
