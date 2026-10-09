"""Package the reviewed EXE and complete Git-tracked source as two assets."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD_INFO_NAMES = ("source-manifest.json", "components.json", "verification.json",
                    "build-provenance.md", "SHA256SUMS.txt")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_bytes(*arguments: str) -> bytes:
    return subprocess.check_output(
        ["git", "-c", "safe.directory=" + ROOT.as_posix(), *arguments], cwd=ROOT)


def git(*arguments: str) -> str:
    return git_bytes(*arguments).decode("utf-8").strip()


def source_entries(commit: str) -> list[dict]:
    """Export exact committed files, refusing private data or binary artifacts."""
    entries = []
    forbidden = {".git", ".devdeps", ".venv", "artifacts", "research", "release",
                 "references", "旧ct文件", "__pycache__", "build-info"}
    for item in git_bytes("ls-tree", "-r", "-z", commit).split(b"\0"):
        if not item:
            continue
        metadata, encoded_name = item.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        name = encoded_name.decode("utf-8")
        path = PurePosixPath(name)
        if (mode not in ("100644", "100755") or kind != "blob" or path.is_absolute()
                or ".." in path.parts or "\\" in name
                or any(part.casefold() in forbidden for part in path.parts)
                or path.name.startswith(".env")
                or path.suffix.lower() in (".exe", ".zip", ".pdb", ".log", ".dmp", ".bin",
                                           ".pyc", ".pyo", ".dll", ".user")):
            raise ValueError("Unselected source-tree entry: " + name)
        raw = git_bytes("cat-file", "blob", blob)
        raw.decode("utf-8")
        entries.append(dict(path=name, mode=mode, git_blob=blob,
                            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), raw=raw))
    if not entries:
        raise ValueError("Empty public source tree")
    return entries


def inventory(entries: list[dict]) -> list[dict]:
    return [{key: value for key, value in entry.items() if key != "raw"} for entry in entries]


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def verify_source_archive(archive: Path, commit: str, executable: Path) -> None:
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    entries = source_entries(commit)
    prefix = "Nioh-HinoEnma-" + version["version"] + "-source/"
    expected = {prefix + entry["path"] for entry in entries}
    expected.update(prefix + "build-info/" + name for name in BUILD_INFO_NAMES)
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(expected) or set(names) != expected or zipped.testzip() is not None:
            raise ValueError("Source archive contains missing, duplicate, unselected or corrupt files")
        for entry in entries:
            metadata = zipped.getinfo(prefix + entry["path"])
            if metadata.create_system != 3 or metadata.external_attr >> 16 != int(entry["mode"], 8):
                raise ValueError("Source archive file type/mode differs: " + entry["path"])
            if zipped.read(prefix + entry["path"]) != entry["raw"]:
                raise ValueError("Source archive differs from reviewed Git blob: " + entry["path"])
        for name in BUILD_INFO_NAMES:
            metadata = zipped.getinfo(prefix + "build-info/" + name)
            if metadata.create_system != 3 or metadata.external_attr >> 16 != 0o100644:
                raise ValueError("Embedded evidence is not a regular source file: " + name)
        source = json.loads(zipped.read(prefix + "build-info/source-manifest.json"))
        if (source["source_commit"] != commit or source["source_tree"] != git("rev-parse", commit + "^{tree}")
                or source["version"] != version["version"] or source["files"] != inventory(entries)):
            raise ValueError("Source archive manifest does not match the reviewed commit/tree")
        verification = json.loads(zipped.read(prefix + "build-info/verification.json"))
        components = json.loads(zipped.read(prefix + "build-info/components.json"))
        if (verification["source_commit"] != commit or verification["game_access"]
                or components["source_commit"] != commit or components["version"] != version["version"]
                or components["runtime_embedded_components"][0]["native_hook_count"] != 60):
            raise ValueError("Embedded build evidence differs from release source")
        for config in ("Debug", "Release"):
            check = verification["checks"][config]
            if (not check["success"] or check["game_access"] or check["version"] != version["version"]
                    or (check["self_checks"], check["hook_count"], check["payload_comparisons"],
                        check["layout_count"]) != (26, 60, 720, 12)):
                raise ValueError("Embedded portable validation differs: " + config)
        executable_hash = sha256(executable)
        if verification["checks"]["Release"]["executable_sha256"] != executable_hash:
            raise ValueError("Source archive evidence does not identify the distributed EXE")
        checksum = executable_hash + "  " + executable.name + "\n"
        if zipped.read(prefix + "build-info/SHA256SUMS.txt").decode("utf-8") != checksum:
            raise ValueError("Embedded EXE checksum differs")
        provenance = zipped.read(prefix + "build-info/build-provenance.md").decode("utf-8")
        for required in (commit, source["source_tree"], executable_hash):
            if required not in provenance:
                raise ValueError("Embedded provenance does not identify exact source and EXE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--build-origin", choices=("local", "github-actions"), default="local")
    parser.add_argument("--publisher", default="OIRANGEISHA")
    parser.add_argument("--workflow-url", default="Not applicable (local validation)")
    parser.add_argument("--verify-source-zip", type=Path)
    parser.add_argument("--exe", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        raise ValueError("A full reviewed source commit is required")
    if git("rev-parse", "HEAD") != args.source_commit or git("status", "--porcelain"):
        raise ValueError("Packaging requires the exact source commit and a clean tree")
    if args.verify_source_zip:
        if args.exe is None:
            raise ValueError("--exe is required when verifying a source archive")
        verify_source_archive(args.verify_source_zip, args.source_commit, args.exe)
        print(json.dumps(dict(source_archive_verified=True, source_commit=args.source_commit,
                              executable_sha256=sha256(args.exe))))
        return
    if args.exe is not None:
        raise ValueError("--exe is only used with --verify-source-zip")
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    match = re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-beta\.([1-9][0-9]*(?:\.[1-9][0-9]*)?)(?:\.hotfix\.([1-9][0-9]*))?", version["version"])
    if (not match or version["tag"] != "v" + version["version"] or version["channel"] != "beta"
            or version["repository"] != "OIRANGEISHA/Nioh-HinoEnma" or version["release_owner"] != "OIRANGEISHA"):
        raise ValueError("Expected consistent owner, repository and Semantic Versioning Beta metadata")
    plan = json.loads((ROOT / "profiles/steam-1.24.8.json").read_text("utf-8"))
    if plan["tool_version"] != version["version"] or len(plan["hooks"]) != 60:
        raise ValueError("Release metadata differs from the reviewed 60-hook profile")
    ct_name = version["ct_file"]
    if Path(ct_name).name != ct_name or not ct_name.endswith(".CT"):
        raise ValueError("Expected a CT source filename within the public ct directory")
    notes = ROOT / "docs/releases" / (version["version"] + ".md")
    validation = ROOT / ("docs/validation-beta" + match.group(4) + ("-hotfix" + match.group(5) if match.group(5) else "") + ".json")
    for required in (ROOT / "ct" / ct_name, notes, validation, ROOT / "docs/使用说明.txt"):
        if not required.is_file():
            raise ValueError("Missing reviewed publication source: " + required.name)
    stem = "Nioh-HinoEnma-" + version["version"]
    executable = ROOT / "artifacts/Release" / (stem + "-windows-x64.exe")
    reports, builds = {}, {}
    for config in ("Debug", "Release"):
        directory = ROOT / "artifacts" / config
        report = json.loads((directory / "verification.json").read_text("utf-8"))
        build = json.loads((directory / "build.json").read_text("utf-8"))
        config_exe = directory / executable.name
        if (not report["success"] or report["game_access"] or report["self_checks"] != 26
                or report["payload_comparisons"] != 720 or report["hook_count"] != 60
                or report["layout_count"] != 12 or not report["generated_source_matches"]
                or report["version"] != version["version"] or report["executable_sha256"] != sha256(config_exe)
                or build["product_version"] != version["version"] or build["file_version"] != version["file_version"]
                or build["configuration"] != config or build["offline_self_checks"] != 26
                or report["pe_machine"] != "x64" or build["pe_machine"] != "x64"):
            raise ValueError("Build or verification metadata does not match: " + config)
        reports[config], builds[config] = report, build
    entries = source_entries(args.source_commit)
    source_tree = git("rev-parse", "HEAD^{tree}")
    destination = ROOT / "artifacts/dist"
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Release output is not empty; do not overwrite prepared assets")
    published_exe = destination / executable.name
    shutil.copyfile(executable, published_exe)
    components = dict(schema=1, version=version["version"], source_commit=args.source_commit,
        runtime_embedded_components=[dict(name="Nioh Hino-Enma launcher", origin="this repository", native_hook_count=60)],
        platform_dependencies_not_embedded=["Windows x64", "Windows .NET Framework", "Win32 APIs"],
        development_dependencies_not_embedded=[
            dict(name="keystone-engine", version="0.9.2", purpose="independent x64 assembly verification", license="GPL-2.0 or commercial (development only)"),
            dict(name="capstone", version="5.0.9", purpose="instruction decoding and relocation analysis", license="BSD (development only)"),
            dict(name="unicorn", version="2.1.4", purpose="CPU regression checks with explicit Win64 native-call stubs", license="GPL-2.0 (development only)")],
        upstream_mechanism="Bryanyora's Nioh CT character change; see NOTICE.md",
        not_included=["Nioh executable or assets", "original third-party CT", "private memory dumps", "Python runtime", "development packages"],
        authenticode=builds["Release"]["authenticode_status"])
    provenance = ["# " + version["display_version"] + " build provenance", "",
        "- Repository: https://github.com/" + version["repository"],
        "- Source commit: " + args.source_commit, "- Source tree: " + source_tree,
        "- Release tag: " + version["tag"] + " (annotated; never moved after publication)",
        "- Release Owner: " + version["release_owner"], "- Build origin: " + args.build_origin,
        "- Prepared asset uploader: " + args.publisher, "- Workflow: " + args.workflow_url,
        "- Recorded UTC: " + datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "- Clean checkout checked before packaging: yes", "",
        "Debug and Release each passed 26 offline C# checks and 720 payload comparisons across 12 layouts. No game access.",
        "Local gameplay evidence and limitations are recorded in the reviewed release notes and sanitized validation record.",
        "Windows Authenticode: " + builds["Release"]["authenticode_status"] + ".",
        "CI attestation, when generated, covers the exact CI-built EXE and source ZIP; it does not certify gameplay or replace code signing.", "",
        "| Asset | Bytes | SHA-256 |", "| --- | ---: | --- |",
        "| " + executable.name + " | " + str(executable.stat().st_size) + " | " + sha256(executable) + " |", ""]
    info = {
        "source-manifest.json": json_bytes(dict(schema=1, version=version["version"], source_commit=args.source_commit,
                                                source_tree=source_tree, files=inventory(entries))),
        "components.json": json_bytes(components),
        "verification.json": json_bytes(dict(source_commit=args.source_commit, game_access=False, checks=reports)),
        "build-provenance.md": "\n".join(provenance).encode("utf-8"),
        "SHA256SUMS.txt": (sha256(executable) + "  " + executable.name + "\n").encode("utf-8"),
    }
    archive = destination / (stem + "-source.zip")
    prefix = stem + "-source/"
    timestamp = datetime.fromisoformat(version["release_date"] + "T00:00:00+00:00")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        contents = [(entry["path"], entry["raw"], int(entry["mode"], 8)) for entry in entries]
        contents += [("build-info/" + name, raw, 0o100644) for name, raw in info.items()]
        for name, raw, mode in contents:
            entry = zipfile.ZipInfo(prefix + name, timestamp.timetuple()[:6])
            entry.create_system = 3
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = mode << 16
            zipped.writestr(entry, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    verify_source_archive(archive, args.source_commit, published_exe)
    assets = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in (published_exe, archive)]
    manifest = dict(version=version["version"], source_commit=args.source_commit, source_tree=source_tree, assets=assets)
    (ROOT / "artifacts/release-manifest.json").write_bytes(json_bytes(manifest))
    release_notes = notes.read_text("utf-8") + "\n\n## Exact release assets\n\n"
    release_notes += "Source commit: " + args.source_commit + "; source tree: " + source_tree + ".\n\n"
    release_notes += "| Asset | Bytes | SHA-256 |\n| --- | ---: | --- |\n"
    for asset in assets:
        release_notes += "| " + asset["name"] + " | " + str(asset["bytes"]) + " | " + asset["sha256"] + " |\n"
    release_notes += "\nThe source ZIP contains the complete reviewed Git-tracked source and build-info evidence. Build dependencies and private research/game resources are excluded.\n"
    (ROOT / "artifacts/release-notes.md").write_text(release_notes, encoding="utf-8", newline="\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
