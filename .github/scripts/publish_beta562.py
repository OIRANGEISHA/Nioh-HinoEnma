"""Publish only the payload-verified Beta5.6.2 executable and committed source.

Preparation uses no network. Publication uses the workflow's GH_TOKEN through gh,
never prints it, preserves existing releases, and verifies downloaded asset bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
REPO = "OIRANGEISHA/Nioh-HinoEnma"
VERSION = "1.0.0-beta.5.6.2"
TAG = "v" + VERSION
STEM = "Nioh-HinoEnma-" + VERSION
EXE = STEM + "-windows-x64.exe"
SOURCE = STEM + "-source.zip"
COMPLETE = STEM + "-complete.zip"
CT = "Nioh_HinoEnma_1.24.8_Beta5_6_2.CT"
EXE_SHA = "c636fd81d3b1aeffaad8b3a0f9d514c9ce133e151d740393b68565c314dea444"
PROFILE_SHA = "25a113a885867f922308eb75c8b87cf3b5088274496121318197ab69225e3f7b"
CT_SHA = "34c426c8402229c5a09cfa08326d849f628a6f4577873deb73cd1258bdc01d53"
ASSETS = (EXE, SOURCE, CT, COMPLETE, "SHA256SUMS.txt", "release-manifest.json")
OUT = ROOT / "artifacts" / "publish-beta562"
BOT = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
TITLE = "Nioh Hino-Enma 1.0.0 Beta 5.6.2"
PRIVATE_PARTS = {".git", ".agents", ".codex", ".aws", ".devdeps", ".venv",
                 "__pycache__", "artifacts", "research", "references", "release",
                 "dist", "build-info", "node_modules"}
BINARY_SUFFIXES = {".exe", ".dll", ".zip", ".pdb", ".dmp", ".bin", ".pyc",
                   ".pyo", ".jpg", ".jpeg", ".png", ".mp4", ".pdf", ".pfx",
                   ".pem", ".key", ".user", ".log"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(path.read_text("utf-8"))


def command(args, *, cwd=ROOT, input_bytes=None, acceptable=(0,)):
    completed = subprocess.run(args, cwd=cwd, input=input_bytes,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Avoid dumping environment or authentication diagnostics into build logs.
    require(completed.returncode in acceptable,
            "Command failed (exit %d): %s" % (completed.returncode, args[0]))
    return completed


def git(*args, cwd=ROOT):
    return command(["git", *args], cwd=cwd).stdout.decode("utf-8").strip()


def clean_source():
    require(Path(git("rev-parse", "--show-toplevel")).resolve() == ROOT.resolve(),
            "Source root must be its own Git checkout")
    commit = git("rev-parse", "HEAD")
    require(re.fullmatch("[0-9a-f]{40}", commit), "Exact source commit required")
    require(not git("status", "--porcelain", "--untracked-files=no"),
            "Tracked source changed; refusing publication")
    tree = git("rev-parse", "HEAD^{tree}")
    require(re.fullmatch("[0-9a-f]{40}", tree), "Exact source tree required")
    return commit, tree


def safe_source_path(path):
    parts = PurePosixPath(path).parts
    require(parts and not path.startswith("/") and "\\" not in path
            and all(part not in (".", "..") for part in parts), "Unsafe Git path")
    require(not any(part.casefold() in PRIVATE_PARTS for part in parts),
            "Private path in committed source: " + path)
    require(not any(part.casefold().startswith(".env") for part in parts),
            "Environment file in committed source")
    name = parts[-1].casefold()
    require(PurePosixPath(path).suffix.casefold() not in BINARY_SUFFIXES
            and name not in ("credentials", "credentials.json", "token.json",
                             "tokens.json", "id_rsa", "id_ed25519", "known_hosts"),
            "Binary or credential path in committed source: " + path)


def committed_source(commit):
    result = []
    listing = command(["git", "ls-tree", "-r", "-z", commit]).stdout
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, path_raw = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        path = path_raw.decode("utf-8")
        safe_source_path(path)
        require(kind == "blob" and mode in ("100644", "100755"),
                "Source links/submodules are forbidden: " + path)
        raw = command(["git", "cat-file", "blob", blob]).stdout
        raw.decode("utf-8")
        require(b"\0" not in raw, "Binary source content: " + path)
        require((ROOT / path).is_file() and not (ROOT / path).is_symlink()
                and (ROOT / path).read_bytes() == raw,
                "Working source bytes differ from Git blob: " + path)
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == blob,
                "Git blob identity differs: " + path)
        result.append(dict(path=path, mode=mode, blob=blob, bytes=len(raw),
                           sha256=sha(raw), raw=raw))
    require(result, "Empty committed source")
    return sorted(result, key=lambda entry: entry["path"])


def inventory(entries):
    return [{key: value for key, value in entry.items() if key != "raw"}
            for entry in entries]


def verify_zip_bytes(raw, contents, prefix=""):
    expected = {prefix + name: (data, mode) for name, data, mode in contents}
    require(len(expected) == len(contents), "Duplicate archive entry")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(archive.testzip() is None and len(archive.namelist()) == len(expected)
                and set(archive.namelist()) == set(expected), "Archive inventory/CRC differs")
        for name, (data, mode) in expected.items():
            item = archive.getinfo(name)
            require(archive.read(name) == data and item.create_system == 3
                    and item.external_attr >> 16 == int(mode, 8),
                    "Archive bytes/mode differ: " + name)


def zip_bytes(contents, prefix=""):
    require(len({prefix + name for name, _, _ in contents}) == len(contents),
            "Duplicate archive entry")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw, mode in contents:
            info = zipfile.ZipInfo(prefix + name, (2026, 10, 13, 0, 0, 0))
            info.create_system = 3
            info.external_attr = int(mode, 8) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    raw = output.getvalue()
    verify_zip_bytes(raw, contents, prefix)
    return raw


def verify_proof(proof, executable, profile_sha, generated_sha):
    expected = dict(version=VERSION, success=True, game_access=False,
        generated_source_matches=True, self_checks=30, payload_comparisons=984,
        layout_count=12, hook_count=82, legacy_payload_comparisons=7536,
        legacy_layout_count=108, pe_machine="x64", profile_sha256=profile_sha,
        generated_source_sha256=generated_sha, executable_sha256=file_sha(executable),
        executable_bytes=executable.stat().st_size,
        executable_versions=dict(product_version=VERSION, file_version="1.0.0.77"))
    require(all(proof.get(key) == value for key, value in expected.items()),
            "Exact offline executable verification required: " + str(executable))


def current_evidence(asset_dir, metadata):
    require(Path(git("rev-parse", "--show-toplevel", cwd=asset_dir)).resolve() == asset_dir.resolve(),
            "Asset directory must be its own immutable Git checkout")
    require(git("rev-parse", "HEAD", cwd=asset_dir) == metadata["asset_commit"],
            "Immutable asset checkout commit differs")
    require(not git("status", "--porcelain", "--untracked-files=no", cwd=asset_dir),
            "Tracked immutable assets changed")
    tracked = command(["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"], cwd=asset_dir).stdout
    require(set(tracked.decode("utf-8").split("\0")) - {""}
            == {EXE, "original-local-verification.json"},
            "Asset checkout contains unexpected files")
    exe = asset_dir / EXE
    original_path = asset_dir / "original-local-verification.json"
    require(file_sha(exe) == EXE_SHA and exe.stat().st_size == 814592,
            "Exact locally verified release EXE required")
    require(file_sha(original_path) == metadata["original_local_verification_sha256"],
            "Original local receipt identity differs")
    original = read_json(original_path)
    game = read_json(ROOT / "docs/living-weapon-beta562-gameplay.json")
    require(original.get("gameplay") == game and game.get("success") is True
            and game.get("exact_executable_gameplay_validated") is False
            and game.get("payload_equivalent_to_cold_tested") is True
            and game["basis"]["exact_standalone_gameplay_validated"] is True
            and game["basis"]["executable_sha256"] == "004f0000b0411218ee6dd94f39a5b69c189f6bd48fde875db135dea693dd5b7f"
            and game.get("temporary_runtime_patch") is False
            and game.get("manual_resource_binding") is False
            and game.get("executable_sha256") == EXE_SHA
            and game.get("profile_sha256") == PROFILE_SHA,
            "Cold gameplay receipt differs from original evidence")
    sys.path.insert(0, str(ROOT / "tools"))
    from verify_beta562_promotion import verify as verify_promotion
    promotion = verify_promotion()
    require(promotion == original.get("promotion")
            and promotion == read_json(ROOT / "docs/beta562-promotion-verification.json")
            and promotion["runtime_payloads_identical"] is True,
            "Independent cold-binary payload equivalence required")
    profile = ROOT / "profiles/steam-1.24.8.json"
    generated = ROOT / "launcher/Profile.generated.cs"
    ct = ROOT / "ct" / CT
    require(file_sha(profile) == PROFILE_SHA and file_sha(ct) == CT_SHA,
            "Versioned release profile or verified CT identity changed")
    generated_sha = file_sha(generated)
    cold_report = ROOT / "artifacts/PublishedExe/verification.json"
    command([sys.executable, str(ROOT / "tools/verify_beta562.py"),
             "--exe", str(exe), "--report", str(cold_report)])
    cold = read_json(cold_report)
    verify_proof(cold, exe, PROFILE_SHA, generated_sha)
    builds, checks = {}, {}
    for configuration in ("Debug", "Release"):
        folder = ROOT / "artifacts" / configuration
        checks[configuration] = read_json(folder / "verification.json")
        builds[configuration] = read_json(folder / "build.json")
        verify_proof(checks[configuration], folder / EXE, PROFILE_SHA, generated_sha)
        require(all(builds[configuration].get(key) == value for key, value in dict(
            configuration=configuration, product_version=VERSION, file_version="1.0.0.77",
            offline_self_checks=30, pe_machine="x64").items()), "CI build identity differs")
    regressions = read_json(ROOT / "artifacts/beta562-regression-tests.json")
    sys.path.insert(0, str(ROOT / "tools"))
    from run_beta562_regressions import source_files
    require(all(regressions.get(key) == value for key, value in dict(
        version=VERSION, success=True, game_access=False, tests_run=240, expected_tests=240,
        failures=0, errors=0, skipped=0, tested_source_unchanged=True,
        source_files=source_files()).items()), "Fresh exact-source 240 regressions required")
    ct_proof = read_json(ROOT / "artifacts/ct-verification.json")
    require(all(ct_proof.get(key) == value for key, value in dict(
        success=True, version=VERSION, game_access=False, hook_count=82, layout_count=12,
        three_way_payload_comparisons=984, native_patch_comparisons=984,
        source_input_unchanged=True, private_dependencies_imported=False,
        ct_direct_gameplay_tested=False, profile_sha256=PROFILE_SHA,
        generated_source_sha256=generated_sha, ct_sha256=CT_SHA,
        verifier_sha256=file_sha(ROOT / "tools/verify_beta562_ct.py"),
        converter_sha256=file_sha(ROOT / "src/living_weapon_start_ct.py")).items()),
        "Exact current CT proof required")
    source_check = read_json(ROOT / "artifacts/source-checks.json")
    require(source_check.get("success") is True and source_check.get("game_access") is False
            and source_check.get("hook_count") == 82
            and source_check.get("private_dependencies_imported") is False,
            "Current portable source check required")
    return dict(version=VERSION, game_access=False, gameplay=game, promotion=promotion,
        published_executable=dict(origin="local-source-build", sha256=EXE_SHA,
            exact_executable_gameplay_validated=False, payload_equivalent_to_cold_tested=True, checks=cold),
        ci_builds=dict(builds=builds, checks=checks,
            exact_executable_gameplay_validated=False,
            scope="CI rebuilt files have offline verification only; they are not Release assets."),
        regressions=regressions, ct=ct_proof, source_check=source_check,
        original_local_verification_sha256=file_sha(original_path))


def publication_metadata():
    metadata = read_json(ROOT / "docs/beta562-publication.json")
    require(all(metadata.get(key) == value for key, value in dict(version=VERSION,
        tag=TAG, executable_sha256=EXE_SHA, profile_sha256=PROFILE_SHA,
        ct_sha256=CT_SHA, publication_authorized=True).items()),
        "Explicit exact-version publication scope required")
    require(re.fullmatch("[0-9a-f]{40}", metadata.get("asset_commit", ""))
            and re.fullmatch("[0-9a-f]{64}", metadata.get("original_local_verification_sha256", "")),
            "Exact immutable asset identities required")
    return metadata


def asset_record(name, raw):
    return dict(name=name, bytes=len(raw), sha256=sha(raw))


def source_notes(commit):
    text = (ROOT / "docs/releases" / (VERSION + ".md")).read_text("utf-8")
    text = text.replace("本地交付", "GitHub Pre-release")
    text = re.sub(r"本次按用户要求先打包为 Beta5\.6\.1 本地版本，没有新建 GitHub 提交、标签或 Release。", "", text)
    text = re.sub(r"\]\(\.\./([^)]*)\)",
                  lambda match: "](https://github.com/" + REPO + "/blob/" + commit
                  + "/docs/" + match.group(1) + ")", text)
    return text.rstrip()


def release_notes(commit, tree, metadata, records):
    notes = source_notes(commit) + "\n\n公开发布来源：本地构建的 Beta5.6.2 EXE；全部运行补丁与实测修正版一致，当前版本另经离线验证，新 EXE 未重复实机测试。\n\n"
    notes += "源码提交：[" + commit + "](https://github.com/" + REPO + "/commit/" + commit + ")\n\n"
    notes += "源码 tree：`" + tree + "`；不可变资产提交：`" + metadata["asset_commit"] + "`。\n\n"
    notes += "| Release 文件 | SHA-256 |\n| --- | --- |\n"
    notes += "".join("| " + name + " | `" + records[name]["sha256"] + "` |\n" for name in ASSETS)
    return notes.rstrip("\n")


def build_provenance(commit, tree, metadata):
    return dict(schema=1, version=VERSION, source_commit=commit, source_tree=tree,
        asset_commit=metadata["asset_commit"], asset_branch=metadata.get("asset_branch"),
        build_origin="local-source-build", publisher=BOT,
        exact_tested_executable_preserved=False, payload_equivalent_to_cold_tested=True, published_executable_sha256=EXE_SHA,
        ci_rebuilt_executables_gameplay_validated=False,
        ct_direct_activation_gameplay_tested=False,
        note="Published executable is a versioned rebuild, with runtime bytes equivalent to cold-tested FileVersion 76; exact new-file gameplay was not repeated.")


def prepare(asset_dir):
    metadata = publication_metadata()
    commit, tree = clean_source()
    entries = committed_source(commit)
    evidence = current_evidence(asset_dir, metadata)
    require(clean_source() == (commit, tree), "Source changed during verification")
    evidence.update(source_commit=commit, source_tree=tree)
    files = inventory(entries)
    source_manifest = dict(schema=1, version=VERSION, source_commit=commit,
        source_tree=tree, source_inventory_sha256=sha(encoded(files)), files=files)
    provenance = build_provenance(commit, tree, metadata)
    info = {
        "source-manifest.json": encoded(source_manifest),
        "verification.json": encoded(evidence),
        "build-provenance.json": encoded(provenance),
        "original-local-verification.json": (asset_dir / "original-local-verification.json").read_bytes(),
        "current-source-checks.json": encoded(evidence["source_check"]),
        "current-regressions.json": encoded(evidence["regressions"]),
        "current-ct-verification.json": encoded(evidence["ct"]),
        "published-executable-verification.json": encoded(evidence["published_executable"]["checks"]),
    }
    contents = [(entry["path"], entry["raw"], entry["mode"]) for entry in entries]
    contents += [("build-info/" + name, raw, "100644") for name, raw in info.items()]
    binaries = {
        EXE: (asset_dir / EXE).read_bytes(),
        SOURCE: zip_bytes(contents, STEM + "-source/"),
        CT: (ROOT / "ct" / CT).read_bytes(),
    }
    inner_assets = [asset_record(name, raw) for name, raw in binaries.items()]
    inner_manifest = dict(**provenance, assets=inner_assets, source_files=len(entries),
        known_remaining_bug="忍术道具目前无法使用", equipment_scope=evidence["gameplay"]["equipment_scope"])
    inside = dict(binaries)
    inside.update({
        "使用说明.txt": (ROOT / "docs/使用说明.txt").read_bytes(),
        "修复与验证记录.json": encoded(evidence),
        "original-local-verification.json": info["original-local-verification.json"],
        "release-manifest.json": encoded(inner_manifest),
        "SHA256SUMS.txt": "".join(row["sha256"] + "  " + row["name"] + "\n"
                                    for row in inner_assets).encode("utf-8"),
    })
    binaries[COMPLETE] = zip_bytes([(name, raw, "100644") for name, raw in inside.items()])
    main_records = [asset_record(name, raw) for name, raw in binaries.items()]
    binaries["SHA256SUMS.txt"] = "".join(row["sha256"] + "  " + row["name"] + "\n"
                                            for row in main_records).encode("utf-8")
    manifest = dict(**provenance, repository=REPO, tag=TAG,
        publication_authorized=True, source_files=len(entries),
        source_inventory_sha256=source_manifest["source_inventory_sha256"],
        original_local_verification_sha256=metadata["original_local_verification_sha256"],
        assets=[asset_record(name, raw) for name, raw in binaries.items()],
        source_archive_every_member_verified=True, complete_archive_every_member_verified=True,
        cold_gameplay_validated=False, basis_cold_gameplay_validated=True, regressions=240,
        known_remaining_bug="忍术道具目前无法使用",
        equipment_scope=evidence["gameplay"]["equipment_scope"],
        manifest_self_hash_in_release_body=True)
    binaries["release-manifest.json"] = encoded(manifest)
    notes = release_notes(commit, tree, metadata,
                          {name: asset_record(name, raw) for name, raw in binaries.items()})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, raw in binaries.items():
        path = OUT / name
        require(not path.exists() or path.read_bytes() == raw,
                "Preserve existing different prepared asset: " + name)
    for name, raw in binaries.items():
        (OUT / name).write_bytes(raw)
    (OUT / "release-notes.md").write_bytes(notes.encode("utf-8"))
    verify_source_zip(binaries[SOURCE], commit, tree, entries, metadata)
    require(clean_source() == (commit, tree), "Source changed during packaging")
    print(json.dumps(dict(prepared=True, source_commit=commit, source_tree=tree,
        source_files=len(entries), assets=6, output=str(OUT), executable_sha256=EXE_SHA)))
    return manifest


def verify_source_zip(raw, commit, tree, entries, metadata):
    prefix = STEM + "-source/"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(archive.testzip() is None and len(names) == len(set(names)), "Source archive CRC/duplicates")
        for name in names:
            relative = name[len(prefix):]
            require(name.startswith(prefix) and relative and not relative.startswith("/")
                    and ".." not in PurePosixPath(relative).parts and "\\" not in relative,
                    "Source archive path traversal")
        manifest = json.loads(archive.read(prefix + "build-info/source-manifest.json"))
        require(manifest.get("source_commit") == commit and manifest.get("source_tree") == tree
                and manifest.get("version") == VERSION and manifest.get("files") == inventory(entries)
                and manifest.get("source_inventory_sha256") == sha(encoded(inventory(entries))),
                "Source archive Git inventory differs")
        source_names = {prefix + entry["path"] for entry in entries}
        info_names = {prefix + "build-info/" + name for name in (
            "source-manifest.json", "verification.json", "build-provenance.json",
            "original-local-verification.json", "current-source-checks.json",
            "current-regressions.json", "current-ct-verification.json", "published-executable-verification.json")}
        require(set(names) == source_names | info_names, "Source archive contains missing/extra files")
        for entry in entries:
            item = archive.getinfo(prefix + entry["path"])
            require(archive.read(item) == entry["raw"] and item.create_system == 3
                    and item.external_attr >> 16 == int(entry["mode"], 8),
                    "Downloaded source bytes/mode differ: " + entry["path"])
        proof = json.loads(archive.read(prefix + "build-info/verification.json"))
        require(proof.get("source_commit") == commit and proof.get("source_tree") == tree
                and proof.get("game_access") is False,
                "Downloaded verification commit/tree differs")
        require(json.loads(archive.read(prefix + "build-info/build-provenance.json"))
                == build_provenance(commit, tree, metadata),
                "Downloaded embedded build provenance differs")
        regression = proof.get("regressions", {})
        require(all(regression.get(key) == value for key, value in dict(version=VERSION,
            success=True, game_access=False, tests_run=240, failures=0, errors=0, skipped=0,
            tested_source_unchanged=True).items()), "Downloaded regression evidence differs")
        expected_regression_files = {entry["path"]: entry["sha256"] for entry in entries
            if (PurePosixPath(entry["path"]).parts[0] in ("src", "tools", "tests", "launcher", "profiles")
                and PurePosixPath(entry["path"]).suffix.lower() in (".py", ".json", ".cs", ".ps1", ".manifest"))
            or entry["path"] == "version.json"}
        require(regression.get("source_files") == expected_regression_files,
                "Downloaded regressions do not identify exact committed source")
        original_raw = archive.read(prefix + "build-info/original-local-verification.json")
        require(sha(original_raw) == metadata["original_local_verification_sha256"],
                "Downloaded original cold receipt changed")
        original = json.loads(original_raw)
        require(proof.get("gameplay") == original.get("gameplay")
                and proof["gameplay"]["executable_sha256"] == EXE_SHA
                and proof["published_executable"].get("sha256") == EXE_SHA
                and proof["ci_builds"].get("exact_executable_gameplay_validated") is False,
                "Downloaded gameplay provenance differs")
        require(proof.get("promotion") == original.get("promotion")
                and proof["promotion"] == read_json(ROOT / "docs/beta562-promotion-verification.json")
                and proof["published_executable"].get("exact_executable_gameplay_validated") is False
                and proof["published_executable"].get("payload_equivalent_to_cold_tested") is True,
                "Downloaded version-promotion provenance differs")
        for configuration in ("Debug", "Release"):
            check = proof["ci_builds"]["checks"][configuration]
            require(all(check.get(key) == value for key, value in dict(version=VERSION,
                success=True, game_access=False, self_checks=30, payload_comparisons=984,
                legacy_payload_comparisons=7536, hook_count=82, profile_sha256=PROFILE_SHA,
                generated_source_sha256=file_sha(ROOT / "launcher/Profile.generated.cs")).items()),
                "Downloaded CI evidence differs")
        cold = proof["published_executable"]["checks"]
        require(cold.get("executable_sha256") == EXE_SHA and cold.get("success") is True
                and cold.get("self_checks") == 30 and cold.get("payload_comparisons") == 984
                and cold.get("legacy_payload_comparisons") == 7536
                and cold.get("game_access") is False and cold.get("hook_count") == 82
                and cold.get("version") == VERSION and cold.get("profile_sha256") == PROFILE_SHA
                and cold.get("generated_source_sha256") == file_sha(ROOT / "launcher/Profile.generated.cs"),
                "Downloaded exact EXE proof differs")
        require(all(proof["ct"].get(key) == value for key, value in dict(success=True,
            version=VERSION, game_access=False, ct_sha256=CT_SHA, profile_sha256=PROFILE_SHA,
            generated_source_sha256=file_sha(ROOT / "launcher/Profile.generated.cs"),
            three_way_payload_comparisons=984, native_patch_comparisons=984,
            ct_direct_gameplay_tested=False).items()), "Downloaded CT evidence differs")
        require(proof["source_check"].get("success") is True
                and proof["source_check"].get("game_access") is False
                and proof["source_check"].get("hook_count") == 82,
                "Downloaded source-check evidence differs")
        for filename, expected in (("verification.json", proof),
            ("current-regressions.json", regression),
            ("current-ct-verification.json", proof["ct"]),
            ("current-source-checks.json", proof["source_check"]),
            ("published-executable-verification.json", cold)):
            require(json.loads(archive.read(prefix + "build-info/" + filename)) == expected,
                    "Downloaded duplicate evidence differs: " + filename)
        for name in info_names:
            item = archive.getinfo(name)
            require(item.create_system == 3 and item.external_attr >> 16 == 0o100644,
                    "Source proof archive mode differs: " + name)


def gh_json(endpoint, *, method=None, value=None, missing_ok=False):
    args = ["gh", "api", endpoint]
    if method:
        args += ["--method", method]
    raw = None
    if value is not None:
        args += ["--input", "-"]
        raw = encoded(value)
    completed = subprocess.run(args, cwd=ROOT, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode and missing_ok and b"HTTP 404" in completed.stderr:
        return None
    require(completed.returncode == 0, "GitHub API operation failed: " + endpoint)
    return json.loads(completed.stdout)


def main_matches(commit):
    require(gh_json("repos/" + REPO + "/git/ref/heads/main")["object"]["sha"] == commit,
            "Remote main changed; refusing publication")
    require(clean_source()[0] == commit, "Local source changed; refusing publication")


def find_release():
    # The release-by-tag endpoint only finds published releases. Authenticated
    # listing is required for both fresh Draft readback and Draft recovery.
    matches = []
    for page in range(1, 101):
        releases = gh_json("repos/" + REPO + "/releases?per_page=100&page=" + str(page))
        require(isinstance(releases, list), "Unexpected Release listing response")
        matches.extend(release for release in releases if release.get("tag_name") == TAG)
        if len(releases) < 100:
            break
    else:
        raise ValueError("Release listing bound exceeded; refusing ambiguous lookup")
    require(len(matches) <= 1, "Multiple releases share the target tag; preserve them")
    if not matches:
        return None
    return gh_json("repos/" + REPO + "/releases/" + str(matches[0]["id"]))


def tag_message(commit):
    return "Beta5.6.2; source " + commit + "; payload-verified EXE " + EXE_SHA


def check_tag(commit, *, missing_ok=False):
    ref = gh_json("repos/" + REPO + "/git/ref/tags/" + TAG, missing_ok=missing_ok)
    if ref is None:
        return None
    require(ref["object"]["type"] == "tag", "Existing release tag is not annotated")
    tag = gh_json("repos/" + REPO + "/git/tags/" + ref["object"]["sha"])
    require(tag["object"]["type"] == "commit" and tag["object"]["sha"] == commit
            and tag["tag"] == TAG and tag["tagger"]["name"] == BOT
            and tag["tagger"]["email"] == BOT_EMAIL
            and tag["message"].rstrip("\n") == tag_message(commit),
            "Existing annotated tag identity differs; preserve it")
    return ref["object"]["sha"]


def download(asset, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        completed = subprocess.run(["gh", "api", "repos/" + REPO + "/releases/assets/" + str(asset["id"]),
            "--header", "Accept: application/octet-stream"], cwd=ROOT,
            stdout=output, stderr=subprocess.PIPE)
    require(completed.returncode == 0, "Release binary download failed: " + asset["name"])
    return destination.read_bytes()


def validate_manifest(manifest, commit, tree, entries, metadata):
    expected = dict(version=VERSION, repository=REPO, tag=TAG, source_commit=commit,
        source_tree=tree, asset_commit=metadata["asset_commit"], build_origin="local-source-build",
        publisher=BOT, exact_tested_executable_preserved=False, payload_equivalent_to_cold_tested=True,
        published_executable_sha256=EXE_SHA, ci_rebuilt_executables_gameplay_validated=False,
        publication_authorized=True, cold_gameplay_validated=False, basis_cold_gameplay_validated=True, regressions=240,
        source_inventory_sha256=sha(encoded(inventory(entries))), source_files=len(entries),
        original_local_verification_sha256=metadata["original_local_verification_sha256"])
    require(all(manifest.get(key) == value for key, value in expected.items()),
            "Release manifest does not identify authorized source and cold file")
    records = manifest.get("assets", [])
    require(len(records) == 5 and {row["name"] for row in records} == set(ASSETS) - {"release-manifest.json"},
            "Release manifest asset inventory differs")
    for record in records:
        require(re.fullmatch("[0-9a-f]{64}", record.get("sha256", ""))
                and isinstance(record.get("bytes"), int) and record["bytes"] > 0,
                "Invalid asset digest/size")
    records_by_name = {record["name"]: record for record in records}
    require(records_by_name[EXE]["sha256"] == EXE_SHA
            and records_by_name[EXE]["bytes"] == 814592
            and records_by_name[CT]["sha256"] == CT_SHA,
            "Release manifest exact EXE/CT identity differs")


def validate_release_identity(release, commit, *, body=None, expect_draft=None):
    require(release["tag_name"] == TAG and release["target_commitish"] == commit
            and release["author"]["login"] == BOT and release["name"] == TITLE
            and release["prerelease"] is True,
            "Existing Release identity differs; preserve it")
    if body is not None:
        require(release.get("body") == body, "Release body differs; preserve it")
    if expect_draft is not None:
        require(release["draft"] is expect_draft, "Release Draft state differs")
    if not release["draft"]:
        require(release.get("published_at"), "Published release has no publication date")
    names = [asset["name"] for asset in release["assets"]]
    require(len(names) == len(set(names)) and set(names) <= set(ASSETS),
            "Existing Release asset inventory differs; preserve it")


def readback(release, commit, tree, entries, metadata, phase, expected_body=None):
    validate_release_identity(release, commit, body=expected_body)
    require({asset["name"] for asset in release["assets"]} == set(ASSETS),
            "Complete six-asset Release required")
    folder = OUT / "readback" / phase
    downloaded = {asset["name"]: download(asset, folder / asset["name"])
                  for asset in release["assets"]}
    manifest = json.loads(downloaded["release-manifest.json"])
    validate_manifest(manifest, commit, tree, entries, metadata)
    records = {row["name"]: row for row in manifest["assets"]}
    records["release-manifest.json"] = asset_record("release-manifest.json", downloaded["release-manifest.json"])
    require(release.get("body") == release_notes(commit, tree, metadata, records),
            "Canonical Release body differs; preserve it")
    for asset in release["assets"]:
        row = records[asset["name"]]
        require(asset["state"] == "uploaded" and asset["size"] == row["bytes"]
                and len(downloaded[asset["name"]]) == row["bytes"]
                and sha(downloaded[asset["name"]]) == row["sha256"],
                "Downloaded asset bytes differ: " + asset["name"])
        if asset.get("digest"):
            require(asset["digest"] == "sha256:" + row["sha256"], "GitHub asset digest differs")
        require("`" + row["sha256"] + "`" in release["body"]
                and "| " + asset["name"] + " |" in release["body"],
                "Release body omitted exact asset identity")
    require("/commit/" + commit in release["body"] and tree in release["body"]
            and "忍术道具目前无法使用" in release["body"]
            and "CT" in release["body"] and "未实机验收" in release["body"],
            "Release body omitted source or testing limits")
    sums = "".join(records[name]["sha256"] + "  " + name + "\n"
                   for name in (EXE, SOURCE, CT, COMPLETE)).encode("utf-8")
    require(downloaded["SHA256SUMS.txt"] == sums, "Downloaded checksums differ")
    verify_source_zip(downloaded[SOURCE], commit, tree, entries, metadata)
    with zipfile.ZipFile(io.BytesIO(downloaded[COMPLETE])) as archive:
        require(archive.testzip() is None and len(archive.namelist()) == len(set(archive.namelist())),
                "Complete archive CRC/duplicates")
        expected_names = {EXE, SOURCE, CT, "使用说明.txt", "修复与验证记录.json",
                          "original-local-verification.json", "release-manifest.json", "SHA256SUMS.txt"}
        require(set(archive.namelist()) == expected_names, "Complete archive inventory differs")
        for name in expected_names:
            item = archive.getinfo(name)
            require(item.create_system == 3 and item.external_attr >> 16 == 0o100644,
                    "Complete archive member mode differs: " + name)
        for name in (EXE, SOURCE, CT):
            require(archive.read(name) == downloaded[name], "Complete nested asset differs: " + name)
        require(archive.read("使用说明.txt") == (ROOT / "docs/使用说明.txt").read_bytes()
                and sha(archive.read("original-local-verification.json")) == metadata["original_local_verification_sha256"],
                "Complete instructions/original receipt differ")
        inside_manifest = json.loads(archive.read("release-manifest.json"))
        expected_inside_manifest = dict(**build_provenance(commit, tree, metadata),
            assets=[records[name] for name in (EXE, SOURCE, CT)], source_files=len(entries),
            known_remaining_bug="忍术道具目前无法使用",
            equipment_scope=read_json(ROOT / "docs/living-weapon-beta562-gameplay.json")["equipment_scope"])
        require(inside_manifest == expected_inside_manifest,
                "Complete internal manifest differs")
        require(archive.read("SHA256SUMS.txt") == "".join(records[name]["sha256"] + "  " + name + "\n"
                for name in (EXE, SOURCE, CT)).encode("utf-8"), "Complete internal checksums differ")
        with zipfile.ZipFile(io.BytesIO(downloaded[SOURCE])) as source_archive:
            require(archive.read("修复与验证记录.json") == source_archive.read(STEM + "-source/build-info/verification.json"),
                    "Complete verification differs from source archive")
    main_matches(commit)
    tag_sha = check_tag(commit)
    return dict(release_id=release["id"], tag_object=tag_sha,
        asset_ids={asset["name"]: asset["id"] for asset in release["assets"]},
        asset_hashes={name: sha(raw) for name, raw in downloaded.items()},
        url=release["html_url"], source_commit=commit, source_tree=tree)


def publish(asset_dir):
    metadata = publication_metadata()
    commit, tree = clean_source()
    entries = committed_source(commit)
    require(git("rev-parse", "HEAD", cwd=asset_dir) == metadata["asset_commit"]
            and file_sha(asset_dir / EXE) == EXE_SHA
            and file_sha(asset_dir / "original-local-verification.json") == metadata["original_local_verification_sha256"],
            "Immutable source assets differ before publication")
    main_matches(commit)
    release = find_release()
    if release is not None and {asset["name"] for asset in release["assets"]} == set(ASSETS):
        # A later workflow rebuild may have new PE timestamps. Inspect the canonical
        # previously uploaded receipts instead of replacing assets with rebuilt ones.
        before = readback(release, commit, tree, entries, metadata,
                          "existing-draft" if release["draft"] else "existing-published")
        already_published = not release["draft"]
        if release["draft"]:
            main_matches(commit)
            gh_json("repos/" + REPO + "/releases/" + str(release["id"]), method="PATCH",
                    value=dict(draft=False, prerelease=True, make_latest="false"))
            public = find_release()
            require(public is not None, "Published release disappeared")
            validate_release_identity(public, commit, body=release["body"], expect_draft=False)
            verified = readback(public, commit, tree, entries, metadata, "resumed-published",
                                expected_body=release["body"])
            require(all(verified[key] == before[key] for key in
                        ("release_id", "tag_object", "asset_ids", "asset_hashes")),
                    "Release, tag or asset identity changed during Draft recovery")
        else:
            verified = before
        verified.update(published=True, already_published=already_published)
        (OUT / "publication-readback.json").write_bytes(encoded(verified))
        print(json.dumps(verified))
        return
    require(release is None or release["draft"],
            "Published Release is incomplete; preserve it")
    manifest = read_json(OUT / "release-manifest.json")
    validate_manifest(manifest, commit, tree, entries, metadata)
    body = (OUT / "release-notes.md").read_text("utf-8")
    local_records = {row["name"]: row for row in manifest["assets"]}
    local_records["release-manifest.json"] = asset_record("release-manifest.json", (OUT / "release-manifest.json").read_bytes())
    for name in ASSETS:
        require(file_sha(OUT / name) == local_records[name]["sha256"]
                and (OUT / name).stat().st_size == local_records[name]["bytes"],
                "Prepared asset changed: " + name)
    if release is not None:
        validate_release_identity(release, commit, body=body, expect_draft=True)
    existing_tag = check_tag(commit, missing_ok=True)
    if existing_tag is None:
        require(release is None, "Existing release has no expected tag; preserve it")
        command(["git", "config", "user.name", BOT])
        command(["git", "config", "user.email", BOT_EMAIL])
        local_tag = command(["git", "show-ref", "--verify", "--quiet", "refs/tags/" + TAG], acceptable=(0, 1))
        if local_tag.returncode == 0:
            require(git("rev-parse", TAG + "^{}") == commit
                    and git("for-each-ref", "--format=%(taggername)|%(taggeremail)|%(contents)", "refs/tags/" + TAG).strip()
                    == BOT + "|<" + BOT_EMAIL + ">|" + tag_message(commit),
                    "Different existing local tag; preserve it")
        else:
            command(["git", "tag", "-a", TAG, commit, "-m", tag_message(commit)])
        main_matches(commit)
        command(["git", "push", "--atomic", "origin", "refs/tags/" + TAG])
        existing_tag = check_tag(commit)
    if release is None:
        main_matches(commit)
        command(["gh", "release", "create", TAG, *[str(OUT / name) for name in ASSETS],
            "--repo", REPO, "--target", commit, "--verify-tag", "--draft", "--prerelease",
            "--latest=false", "--title", TITLE, "--notes-file", str(OUT / "release-notes.md")])
        release = find_release()
        require(release is not None, "Prepared Draft is absent")
    else:
        existing_names = {asset["name"] for asset in release["assets"]}
        # Matching Draft recovery may fill missing names; never replace a file.
        for asset in release["assets"]:
            raw = download(asset, OUT / "readback/draft-recovery" / asset["name"])
            require(sha(raw) == local_records[asset["name"]]["sha256"]
                    and len(raw) == local_records[asset["name"]]["bytes"],
                    "Existing Draft asset differs; preserve Draft")
        for name in ASSETS:
            if name not in existing_names:
                main_matches(commit)
                command(["gh", "release", "upload", TAG, str(OUT / name), "--repo", REPO])
        release = find_release()
        require(release is not None, "Recovered Draft is absent")
    validate_release_identity(release, commit, body=body, expect_draft=True)
    draft = readback(release, commit, tree, entries, metadata, "draft", expected_body=body)
    require(draft["tag_object"] == existing_tag, "Tag changed during Draft preparation")
    main_matches(commit)
    gh_json("repos/" + REPO + "/releases/" + str(release["id"]), method="PATCH",
            value=dict(draft=False, prerelease=True, make_latest="false"))
    public = find_release()
    require(public is not None, "Published Release is absent")
    validate_release_identity(public, commit, body=body, expect_draft=False)
    verified = readback(public, commit, tree, entries, metadata, "published", expected_body=body)
    require(all(verified[key] == draft[key] for key in ("release_id", "tag_object", "asset_ids", "asset_hashes")),
            "Release, tag or asset identity changed during publication")
    verified.update(published=True, already_published=False)
    (OUT / "publication-readback.json").write_bytes(encoded(verified))
    print(json.dumps(verified))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    require(shutil.which("git"), "Git required")
    asset_dir = args.asset_dir.resolve()
    require(asset_dir.is_dir(), "Immutable asset checkout required")
    if args.prepare_only:
        prepare(asset_dir)
    else:
        require(shutil.which("gh"), "Authenticated workflow gh required")
        publish(asset_dir)


if __name__ == "__main__":
    main()
