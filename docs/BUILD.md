# Beta 5.3.2 build and verification

The Beta 5.3.2 profile contains 71 hooks, file version 1.0.0.66. It preserves the original 60-hook basis and all ten other menu entries. Only the existing resource-readiness payload changes, with native loading-gate waits and transient-manager retries. The code allocation is 0x36000; seven private data pages are writable and non-executable. No recorded live heap address is embedded.

## Rebuild on Windows x64

Windows .NET Framework includes the x64 C# compiler used by `tools/build.ps1`. Python and pinned development packages are needed only for regenerating and independently verifying source. No game files or private research inputs are needed.

```powershell
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python -m unittest discover -s tests -p "test_*.py"
python tools/verify_menu_preview.py --report artifacts/menu-preview-verification.json
python tools/verify_beta52_baseline.py --report artifacts/baseline-verification.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.3.2-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.3.2-windows-x64.exe --report artifacts/Release/verification.json
```

The full regressions currently contain 134 tests. The owner-authorized GitHub publication uses `tools/package.py` from an exact clean reviewed Git checkout, after the checks above:

```powershell
$taskSourceCommit = (git rev-parse HEAD).Trim()
python tools/package.py --source-commit $taskSourceCommit --build-origin local --publisher OIRANGEISHA
python tools/package.py --source-commit $taskSourceCommit --verify-source-zip artifacts/dist/Nioh-HinoEnma-1.0.0-beta.5.3.2-source.zip --exe artifacts/dist/Nioh-HinoEnma-1.0.0-beta.5.3.2-windows-x64.exe
```

The release packager refuses a dirty/mismatched checkout, stale source/build proofs and a nonempty output directory. It exports exact tracked Git blobs and embeds the reviewed commit/tree, per-file manifest, component inventory, build reports and EXE checksum in `build-info/`. Release attachments are only the Windows x64 EXE and complete Git-source ZIP. GitHub Actions uses `--build-origin github-actions`, its actual bot uploader identity and workflow URL; do not use those values for a local build. The authorized flow verifies the exact annotated tag and downloads before publishing Pre-release with `latest=false`. Final attachment hashes and CI provenance are recorded in the release body/ZIP; generated attestations remain with GitHub and do not add attachments.

## Optional local snapshot package

`tools/package_local.py` remains available for rebuilding an uncommitted local snapshot, distinct from a Git-source publication. Prepare its required regression receipt:

```powershell
python -c "import json,unittest; from pathlib import Path; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); p=Path('artifacts/regression-tests.json'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(dict(success=r.wasSuccessful(),game_access=False,tests_run=r.testsRun)),encoding='utf-8'); raise SystemExit(not r.wasSuccessful())"
python tools/package_local.py
```

The local packager refuses stale build/source proofs and nonempty output directories. It records a complete UTF-8 snapshot with per-file hashes, exact EXE hash, build reports and component inventory. Its default output is `artifacts/dist-local`; `--destination <empty-directory>` can select another directory. Local outputs are the standalone EXE, source ZIP, and usage text. Verify downloaded/copied local artifacts with:

```powershell
python tools/package_local.py --verify-source-zip <source.zip> --exe <exe>
```

## Validation boundaries

The 41 frozen portable menu tests use synthetic records and explicit native-call stubs: 4280 byte comparisons, 15880 CPU comparisons, and 12 ASLR layouts. They verify copied timing hashes, current-generation camera checks, once-only aura queueing, owned resources, native fallback and machine restoration. Debug and Release each passed 28 self-checks, 852 current-profile and 3780 old-profile comparisons. Another 18 cold-start tests execute 19892 synthetic CPU frames, comparing 852 relocated payloads and 840 unchanged other-hook payloads. Old 55/59/60/70/71-hook installations are restart-only identities. Installation checks include the complete BaseMode aura frame, both native loading-gate dependencies, their readiness leaf and saved returns.

The cold-start test EXE was user-confirmed after a complete game-process restart: enable at NEW GAME/CONTINUE, continue directly to the mission map/base and open the status page before visiting a mission. Model, idle, camera and mist were normal, with one preload and no fallback. The final public EXE is a separate build; its 71 hook payloads and native targets are checked against that tested revision. These tests do not imply every scene, aspect ratio or resource-failure condition. CT execution inside CE remains untested.

The owner has authorized a new `v1.0.0-beta.5.3.2` Pre-release with only the EXE and Git-source ZIP. Local offline results remain local evidence in docs/validation-beta5.3.2.json; final CI-built and downloaded asset hashes belong in the source ZIP's build-info/ and release body. Publication completes after exact source, tag and downloaded-artifact verification. Earlier releases and evidence remain unchanged. Authenticode signing is absent.
