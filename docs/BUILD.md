# Beta 5.4.2 build and verification

The profile has 81 hooks and file version 1.0.0.69. Eight shared payloads route the independent Nine Tails chain and retain the full original Orochi bodies; 73 payloads remain identical to Beta 5.4.1. The current owned resources are discovered at runtime. Allocation size is 0x51000, including nine writable, non-executable data pages and a separate 512-byte Nine Tails binding at offset 0x44000. Saved scene addresses are excluded.

## Rebuild on Windows x64

Use Python 3.12 with the pinned requirements and the x64 .NET Framework C# compiler selected by tools/build.ps1. No game assets, private research files or running game are needed for these checks. The EXE itself does not require Python.

```powershell
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python tools/run_regressions.py
python tools/verify_beta52_baseline.py --report artifacts/baseline-verification.json
python tools/verify_menu_preview.py --report artifacts/menu-preview-verification.json
python tools/verify_orochi_execution.py --report artifacts/orochi-execution-verification.json
python tools/verify_ninetails_execution.py --report artifacts/ninetails-execution-verification.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.4.2-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.4.2-windows-x64.exe --report artifacts/Release/verification.json
```

The complete suite has 203 tests, including 34 frozen Orochi tests and 24 Nine Tails tests. The runner records exact source hashes and refuses a source change during the run. The independent execution proofs also verify source identities, original bodies and relocated payloads. CPU stubs and copied-resource replay do not certify gameplay.

## Local package

Complete all checks above, finalize the exact gameplay scope in docs/validation-beta5.4.2.json, then use an empty output directory:

```powershell
python tools/package_local.py --destination <empty-directory>
python tools/package_local.py --verify-source-zip <source.zip> --exe <exe>
```

The packager rejects stale source, build, proof and regression receipts. It verifies the full UTF-8 snapshot and manifest, four source proofs, both compiled EXEs and the distributed checksum. Outputs are 飞缘魔启动工具.exe, Nioh-HinoEnma-1.0.0-beta.5.4.2-source.zip and 使用说明.txt. The source ZIP includes the repair record and build-info receipts but excludes game resources, save files, private process dumps and development binaries.

The local packager does not create a commit, tag, GitHub Release or CI attestation. The original Beta 5.4.2 local snapshot remains unchanged. On 2026-10-11 (Asia/Shanghai), the user authorized the current source push and Release. The exact-version push workflow now permits this Beta 5.4.2 only, with local_package_only=false, four source proofs, all 203 regressions, both builds and downloaded-asset readback. It exports exact Git source via tools/package.py, creates an immutable annotated tag and inspected Draft, then publishes Pre-release with latest=false. CI assets have separate hashes and provenance; local gameplay evidence is not relabeled as a CI game test. Earlier tags and assets remain immutable.

## Completed offline coverage

Debug and Release each passed 29 self-checks, 972 current-profile comparisons over 12 layouts and 6564 complete historical-profile comparisons over 96 layouts. Eight historical identities contain 55/59/60/70/71/71/80/81 hooks. The launcher reads large payloads in bounded 0x1000 chunks and refuses partial or excessive reads; the relocated heavy payload requires the new 0x4000 ceiling.

The Nine Tails proof passed 24 tests and preserves 73 payloads and patches over 12 layouts (876 comparisons each), plus eight original Orochi bodies. It covers discovery, both resource layers, descriptor bounds, DWORD overflow rejection, fresh bindings, generation invalidation, pending pairing, stale Nine Tails routing to Orochi, native fallback and Win64 ABI. The unchanged Orochi proof passed 34 tests, 852 earlier71 payload/patch comparisons and ten complete native frame guards. The immutable Beta 5.2 basis passed 720 payload and 720 patch comparisons.

The retained menu proof passed 59 tests. Its frozen 41 menu tests retain 4280 byte comparisons and 15880 CPU comparisons; the 18 cold-start tests retain 19892 CPU frames, 852 payload comparisons and 840 unchanged other-hook comparisons. Those suites use their exact predecessor inputs and do not claim 81-hook coverage.

## Gameplay evidence

The scene-bound Nine Tails candidate completed the native paired action, HP 0, native death state 1 and cleanup. The user confirmed story continuation and restored control. The exact new Release EXE's full-restart result and SHA-256 are recorded separately in docs/validation-beta5.4.2.json. Offline proofs always keep final_exe_gameplay_validated=false; the separate gameplay receipt is authoritative for the tested encounter.

Beta 5.4.2 has not repeated the full Orochi fight. It retains the original code and eight CPU routes; Beta 5.4.1's historical full-restart gameplay stays in its original record. Other weapon packages, difficulty variants, multiplayer and direct CT activation have not been individually tested.
