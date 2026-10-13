"""Publish only the payload-verified Beta 6.1 executable and committed source.

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
VERSION = "1.0.0-beta.6.1"
TAG = "v" + VERSION
STEM = "Nioh-HinoEnma-" + VERSION
EXE = STEM + "-windows-x64.exe"
SOURCE = STEM + "-source.zip"
CT = "Nioh_HinoEnma_1.24.8_Beta6_1.CT"
EXE_SHA = "66982e4b857797bd03eb13780e82e4f945b5531dd5f22f3e25015fd7927d2cb7"
PROFILE_SHA = "9726a12e900b91eda692cf9721c56c131b3933ed5512d5aa6e096c8a09f435dd"
CT_SHA = "2268cffa7b34cbe102e1242b05c78333a7b1044ed466cb92322966a629e71f0e"
ASSETS = (EXE, SOURCE)
OUT = ROOT / "artifacts" / "publish-beta61"
BOT = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
TITLE = "Nioh Hino-Enma 1.0.0 Beta 6.1"
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
        executable_versions=dict(product_version=VERSION, file_version="1.0.0.80"))
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
    require(file_sha(exe) == EXE_SHA and exe.stat().st_size == 891904,
            "Exact locally verified release EXE required")
    require(file_sha(original_path) == metadata["original_local_verification_sha256"],
            "Original local receipt identity differs")
    original = read_json(original_path)
    game = {name: read_json(ROOT / "docs" / name) for name in (
        "harakiri-gameplay.json", "dung-fan-gameplay.json",
        "four-throwables-gameplay.json", "arrow-sloth-gameplay.json",
        "wind-weakness-dragon-gameplay.json")}
    require(original.get("gameplay") == game
            and game["harakiri-gameplay.json"]["status"] == "warm_runtime_gameplay_confirmed"
            and all(not game[name]["user_gameplay_confirmation_pending"] for name in game
                    if name != "harakiri-gameplay.json")
            and original["checks"]["Release"]["executable_sha256"] == EXE_SHA,
            "Original confirmed gameplay and executable required")
    sys.path.insert(0, str(ROOT / "tools"))
    from verify_beta61_items import verify as verify_items
    equivalent = verify_items()
    require(equivalent == original.get("item_equivalence")
            and equivalent["warm_payload_equivalence"] is True
            and equivalent["live_payload_comparisons"] == 984
            and equivalent["unchanged_payload_comparisons"] == 948,
            "Independent warm item payload equivalence required")
    profile = ROOT / "profiles/steam-1.24.8.json"
    generated = ROOT / "launcher/Profile.generated.cs"
    ct = ROOT / "ct" / CT
    require(file_sha(profile) == PROFILE_SHA and file_sha(ct) == CT_SHA,
            "Versioned release profile or verified CT identity changed")
    generated_sha = file_sha(generated)
    cold_report = ROOT / "artifacts/PublishedExe/verification.json"
    command([sys.executable, str(ROOT / "tools/verify_beta61.py"),
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
            configuration=configuration, product_version=VERSION, file_version="1.0.0.80",
            offline_self_checks=30, pe_machine="x64").items()), "CI build identity differs")
    regressions = read_json(ROOT / "artifacts/beta61-regression-tests.json")
    sys.path.insert(0, str(ROOT / "tools"))
    from run_beta61_regressions import source_files
    require(all(regressions.get(key) == value for key, value in dict(
        version=VERSION, success=True, game_access=False, tests_run=318, expected_tests=318,
        failures=0, errors=0, skipped=0, tested_source_unchanged=True,
        source_files=source_files()).items()), "Fresh exact-source 318 regressions required")
    ct_proof = read_json(ROOT / "artifacts/beta61-ct-verification.json")
    require(all(ct_proof.get(key) == value for key, value in dict(
        success=True, version=VERSION, game_access=False, hook_count=82, layout_count=12,
        three_way_payload_comparisons=984, native_patch_comparisons=984,
        source_input_unchanged=True, private_dependencies_imported=False,
        ct_direct_gameplay_tested=False, profile_sha256=PROFILE_SHA,
        generated_source_sha256=generated_sha, ct_sha256=CT_SHA,
        verifier_sha256=file_sha(ROOT / "tools/verify_beta61_ct.py"),
        converter_sha256=file_sha(ROOT / "src/living_weapon_start_ct.py")).items()),
        "Exact current CT proof required")
    source_check = read_json(ROOT / "artifacts/source-checks.json")
    require(source_check.get("success") is True and source_check.get("game_access") is False
            and source_check.get("hook_count") == 82
            and source_check.get("private_dependencies_imported") is False,
            "Current portable source check required")
    return dict(version=VERSION, game_access=False, gameplay=game, item_equivalence=equivalent,
        published_executable=dict(origin="local-source-build", sha256=EXE_SHA,
            exact_executable_gameplay_validated=False, warm_payload_equivalence=True, checks=cold),
        ci_builds=dict(builds=builds, checks=checks,
            exact_executable_gameplay_validated=False,
            scope="CI rebuilt files have offline verification only; they are not Release assets."),
        regressions=regressions, ct=ct_proof, source_check=source_check,
        original_local_verification_sha256=file_sha(original_path))


def publication_metadata():
    metadata = read_json(ROOT / "docs/beta61-publication.json")
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
    text = re.sub(r"\]\(\.\./([^)]*)\)",
                  lambda match: "](https://github.com/" + REPO + "/blob/" + commit
                  + "/docs/" + match.group(1) + ")", text)
    return text.rstrip()


def release_notes(commit, tree, metadata, records):
    notes = source_notes(commit) + "\n\n公开发布来源：本地构建的 Beta 6.1 EXE；全部运行补丁与实测修正版一致，当前版本另经离线验证，新 EXE 未重复实机测试。\n\n"
    notes += "源码提交：[" + commit + "](https://github.com/" + REPO + "/commit/" + commit + ")\n\n"
    notes += "源码 tree：`" + tree + "`；不可变资产提交：`" + metadata["asset_commit"] + "`。\n\n"
    notes += "| Release 文件 | SHA-256 |\n| --- | --- |\n"
    notes += "".join("| " + name + " | `" + records[name]["sha256"] + "` |\n" for name in ASSETS)
    return notes.rstrip("\n")


def build_provenance(commit, tree, metadata):
    return dict(schema=1, version=VERSION, source_commit=commit, source_tree=tree,
        asset_commit=metadata["asset_commit"], asset_branch=metadata.get("asset_branch"),
        build_origin="local-source-build", publisher=BOT,
        exact_tested_executable_preserved=False, warm_payload_equivalence=True, published_executable_sha256=EXE_SHA,
        ci_rebuilt_executables_gameplay_validated=False,
        ct_direct_activation_gameplay_tested=False,
        note="Published executable is a versioned rebuild, with runtime bytes equivalent to the user-confirmed warm item repairs; exact new-file gameplay was not repeated.")


def prepare(asset_dir):
    metadata = publication_metadata()
    commit, tree = clean_source()
    entries = committed_source(commit)
    evidence = current_evidence(asset_dir, metadata)
    require(clean_source() == (commit, tree), "Source changed during verification")
    evidence.update(source_commit=commit, source_tree=tree)
    source_manifest = dict(schema=1, version=VERSION, source_commit=commit,
        source_tree=tree, source_inventory_sha256=sha(encoded(inventory(entries))), files=inventory(entries))
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
    contents = [(e["path"], e["raw"], e["mode"]) for e in entries]
    contents += [("build-info/" + name, raw, "100644") for name, raw in info.items()]
    binaries = {EXE: (asset_dir / EXE).read_bytes(), SOURCE: zip_bytes(contents, STEM + "-source/")}
    records = {name: asset_record(name, raw) for name, raw in binaries.items()}
    manifest = dict(**provenance, repository=REPO, tag=TAG,
        publication_authorized=True, source_files=len(entries),
        source_inventory_sha256=source_manifest["source_inventory_sha256"],
        original_local_verification_sha256=metadata["original_local_verification_sha256"],
        assets=list(records.values()), source_archive_every_member_verified=True,
        cold_gameplay_validated=False, warm_item_gameplay_confirmed=True, regressions=318)
    validate_manifest(manifest, commit, tree, entries, metadata)
    notes = release_notes(commit, tree, metadata, records)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, raw in binaries.items():
        path = OUT / name
        require(not path.exists() or path.read_bytes() == raw, "Preserve existing prepared asset: " + name)
    for name, raw in binaries.items(): (OUT / name).write_bytes(raw)
    (OUT / "release-manifest.json").write_bytes(encoded(manifest))
    (OUT / "release-notes.md").write_text(notes, encoding="utf-8", newline="\n")
    verify_source_zip(binaries[SOURCE], commit, tree, entries, metadata)
    require(clean_source() == (commit, tree), "Source changed during packaging")
    print(json.dumps(dict(prepared=True, source_commit=commit, source_tree=tree,
        source_files=len(entries), assets=2, output=str(OUT), executable_sha256=EXE_SHA)))
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
            success=True, game_access=False, tests_run=318, failures=0, errors=0, skipped=0,
            tested_source_unchanged=True).items()), "Downloaded regression evidence differs")
        expected_regression_files = {entry["path"]: entry["sha256"] for entry in entries
            if (PurePosixPath(entry["path"]).parts[0] in ("src", "tools", "tests", "launcher", "profiles")
                and PurePosixPath(entry["path"]).suffix.lower() in (".py", ".json", ".cs", ".ps1", ".manifest"))
            or entry["path"] == "version.json"}
        require(regression.get("source_files") == expected_regression_files,
                "Downloaded regressions do not identify exact committed source")
        original_raw = archive.read(prefix + "build-info/original-local-verification.json")
        require(sha(original_raw) == metadata["original_local_verification_sha256"],
                "Downloaded original local receipt changed")
        original = json.loads(original_raw)
        require(proof.get("gameplay") == original.get("gameplay")
                and original["checks"]["Release"]["executable_sha256"] == EXE_SHA
                and proof["published_executable"].get("sha256") == EXE_SHA
                and proof["ci_builds"].get("exact_executable_gameplay_validated") is False,
                "Downloaded gameplay provenance differs")
        require(proof.get("item_equivalence") == original.get("item_equivalence")
                and proof["item_equivalence"].get("warm_payload_equivalence") is True
                and proof["item_equivalence"].get("live_payload_comparisons") == 984
                and proof["item_equivalence"].get("unchanged_payload_comparisons") == 948
                and proof["item_equivalence"].get("profile_sha256") == PROFILE_SHA
                and proof["published_executable"].get("exact_executable_gameplay_validated") is False
                and proof["published_executable"].get("warm_payload_equivalence") is True,
                "Downloaded item provenance differs")
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
    return "Beta 6.1; source " + commit + "; payload-verified EXE " + EXE_SHA


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
        publisher=BOT, exact_tested_executable_preserved=False, warm_payload_equivalence=True,
        published_executable_sha256=EXE_SHA, ci_rebuilt_executables_gameplay_validated=False,
        publication_authorized=True, cold_gameplay_validated=False,
        warm_item_gameplay_confirmed=True, regressions=318,
        source_inventory_sha256=sha(encoded(inventory(entries))), source_files=len(entries),
        original_local_verification_sha256=metadata["original_local_verification_sha256"])
    require(all(manifest.get(k) == v for k, v in expected.items()), "Publication manifest differs")
    rows = manifest.get("assets", [])
    require(len(rows) == 2 and {r["name"] for r in rows} == set(ASSETS), "Exactly EXE and source required")
    require(all(re.fullmatch("[0-9a-f]{64}", r["sha256"]) and r["bytes"] > 0 for r in rows), "Asset digest/size")
    row = next(r for r in rows if r["name"] == EXE)
    require(row["sha256"] == EXE_SHA and row["bytes"] == 891904, "Exact original EXE required")


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
    require({a["name"] for a in release["assets"]} == set(ASSETS), "Exactly two Release assets required")
    folder = OUT / "readback" / phase
    downloaded = {a["name"]: download(a, folder / a["name"]) for a in release["assets"]}
    records = {name: asset_record(name, raw) for name, raw in downloaded.items()}
    require(records[EXE]["sha256"] == EXE_SHA and records[EXE]["bytes"] == 891904, "Downloaded EXE differs")
    require(release["body"] == release_notes(commit, tree, metadata, records), "Canonical body/digests differ")
    for a in release["assets"]:
        row = records[a["name"]]
        require(a["state"] == "uploaded" and a["size"] == row["bytes"], "Asset state/size differs")
        if a.get("digest"): require(a["digest"] == "sha256:" + row["sha256"], "GitHub asset digest differs")
    verify_source_zip(downloaded[SOURCE], commit, tree, entries, metadata)
    main_matches(commit)
    return dict(release_id=release["id"], tag_object=check_tag(commit),
        asset_ids={a["name"]: a["id"] for a in release["assets"]},
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
