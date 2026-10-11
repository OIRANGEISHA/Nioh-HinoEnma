# Beta 5.4.1 build and verification

The local Beta 5.4.1 profile contains 81 hooks, file version 1.0.0.68. All 71 Beta 5.3.2 hook payloads remain identical. Ten new hooks supply native Orochi execution resource views and scoped numerical/Living Weapon query guards. Current actors and loaded resources are discovered at runtime. Hino idle and common idle are distinct records; private58 retains Hino idle, private1F0 retains owned common idle for native heavy-transition discovery. The allocation is 0x43000; eight private data pages are writable and non-executable. No recorded live heap address is embedded.

## Rebuild on Windows x64

Windows .NET Framework includes the x64 C# compiler used by `tools/build.ps1`. Use Python 3.12 and the pinned development requirements for source regeneration and independent verification. No game files or private research inputs are needed. The EXE itself does not require Python or those packages.

```powershell
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python tools/run_regressions.py
python tools/verify_menu_preview.py --report artifacts/menu-preview-verification.json
python tools/verify_beta52_baseline.py --report artifacts/baseline-verification.json
python tools/verify_orochi_execution.py --report artifacts/orochi-execution-verification.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.4.1-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.4.1-windows-x64.exe --report artifacts/Release/verification.json
```

The complete source suite contains 177 tests. The runner records the exact tested source hashes and refuses a changed source set during the run. The 34 execution tests are part of that total; their independent verifier additionally records frozen trial-source identities and previous71 payload preservation.

## Local snapshot package

The verified Beta 5.4.1 package was prepared locally; the subsequent user request authorizes committing and pushing its reviewed source and records to GitHub `main`. To create a local package after completing all checks above:

```powershell
python tools/package_local.py --destination <empty-directory>
python tools/package_local.py --verify-source-zip <source.zip> --exe <exe>
```

The packager refuses stale source/build/proof hashes and nonempty output directories. It exports a complete selected UTF-8 source snapshot and verifies every archived file against its current source and manifest, all three portable proofs, both EXE verification reports and the distributed EXE checksum. The source ZIP includes technical records, release notes and `build-info/` with source inventory, snapshot identity, component inventory, build evidence and checksums. It excludes game resources, private dumps and development binaries.

Outputs are `飞缘魔启动工具.exe`, `Nioh-HinoEnma-1.0.0-beta.5.4.1-source.zip` and `使用说明.txt`. The default destination is `artifacts/dist-local`. This local packager records a source snapshot and does not create a Git commit, tag, remote Release or CI attestation. The original verified local ZIP retains its original snapshot; subsequent documentation updates in Git are recorded by their commits.

## Publication scope

The user requested the Beta 5.4.1 GitHub Release on 2026-10-11 (Asia/Shanghai), after the source push and its complete CI passed. The version-scoped Actions publisher now permits this reviewed Beta 5.4.1 release. It runs all 177 regressions, all three source proofs, Debug/Release builds and verification, then calls `tools/package.py` from the exact clean reviewed commit. The source ZIP exports exact Git blobs and includes the complete regression receipt. The workflow prepares an immutable annotated tag and Draft, verifies both downloaded assets and source contents, and publishes a Pre-release with latest=false. Historical tags, assets and evidence remain unchanged.

The Release has exactly two attachments: `Nioh-HinoEnma-1.0.0-beta.5.4.1-windows-x64.exe` and `Nioh-HinoEnma-1.0.0-beta.5.4.1-source.zip`. Usage, checksums, CI provenance and the attestation link are in the Release body and source ZIP. GitHub Actions builds a separate EXE; its exact hash is recorded there. The local gameplay-tested EXE and original local ZIP retain their original identities and are not overwritten or relabeled as CI builds.

## Validation boundaries

The frozen 41 menu tests retain 4280 byte comparisons, 15880 synthetic CPU comparisons and 12 ASLR layouts. The 18 frozen cold-start tests retain 19892 CPU frames, 852 relocated payloads and 840 unchanged other-hook comparisons. The verifier supplies their exact Beta 5.3.2 predecessor input without changing frozen files or assertions. These counts describe those historical suites, not the new81 profile.

The 34 execution tests use synthetic owners, resources and explicit Win64 call stubs. They check dynamic discovery, native fallback, both motion/event layers, descriptor bounds, the paired chain, post-kill scope, numerical query exits and ABI preservation. All previous71 payloads and patches remain identical across 12 layouts (852 comparisons of each). The immutable Beta 5.2 basis retains 720 payload and 720 patch comparisons.

Debug and Release each passed 29 self-checks, 972 current-profile comparisons across 12 layouts and 5592 old-profile comparisons across 84 layouts. The prior 55/59/60/70/71/71/80 installations remain read-only restart identities. Installation excludes complete menu frames and ten execution/geometry/query frames, including the full query86 frame, saved returns and the late no-hit epilogue.

The scene-bound trials and final EXE gameplay retain separate evidence. The exact optimized Release EXE, SHA-256 `dff85284c3e2ade94d6c8d50255734e48544391546e92eae41489864b6f7c2be`, passed a complete game-process restart and main-menu enable, followed by final Orochi execution on `1DC1C / 19569 / 3203`. All 81 installed hooks matched the release payloads; no diagnostic hook or temporary patch was present. The user confirmed the kill, continued story and restored control. The 1412 read-only clock samples recorded native HP 0 and eight head deaths at target frame 251, then player idle and execution phase 0 at frame 411.

The eight exact head identities have native-table and regression evidence, but all eight full battles have not been tested individually. The earlier `8F795` animation-only failure lacks target-clock evidence establishing its cause. Nine Tails remains unverified. See [the debugging record](debugging/orochi-execution-2026-10-11.md), [local validation](validation-beta5.4.1.json) and [package notes](releases/1.0.0-beta.5.4.1.md). CT execution in CE remains untested; Authenticode signing is absent.
