# Build and verification

Beta 5 corresponds to local 0.58 with 50 hooks. Public metadata is separate from the local version. Building requires Windows x64 and the .NET Framework C# compiler, not Nioh files or Cheat Engine. The source ZIP contains the reviewed Git-tracked source; its build-info directory records the exact source commit/tree, source inventory, EXE checksum, portable verification, component inventory and build provenance.

## Build and portable checks

Python 3.10+ is required only for payload regeneration, developer verification and packaging. Install the pinned optional development dependencies in the project directory. Unicorn 2.1.4 is used for developer CPU checks; the standalone EXE does not include or require Unicorn, Python or Cheat Engine.

~~~powershell
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python tests/test_latched_door_instances.py
python tests/test_special_items_portable.py
python tests/test_salt_recovery_portable.py
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5-windows-x64.exe --report artifacts/Release/verification.json
~~~

Edit assembly in src/, then regenerate the C# profile and matching CT with python tools/build_profile.py. The pure public source chain reconstructs local 0.58 from public instruction signatures without importing private verifiers or reading research files. Compare every payload, patch, signature, slot and target with the frozen local adaptation. Do not substitute arbitrary game hashes or signatures.

Outputs are ignored under artifacts/Debug and artifacts/Release. Release is optimized x64 GUI with asInvoker. Each build must pass 21 C# refusal/recognition/transaction checks and 600 payload/patch comparisons across 50 hooks and 12 layouts, with generated source matching exactly and no game access. Portable source/CT checks additionally check label uniqueness, native branch entry boundaries and code/data layout. tools/verify.py --preview creates an offscreen UI image.

## Evidence boundaries

Keep three classes of evidence distinct:

- **Public portable checks:** source reconstruction, assembly, relocation, injector refusal/recognition and public CPU regressions with explicit Win64 native-call stubs. These checks do not read private game-code inputs or execute the complete native game engine, item damage or rendered animation.
- **Local native-code regressions:** the 23 new local 0.58 checks use private verified native-code inputs. Those inputs and raw reports are not distributed and are not public portable CI. Earlier local checks remain frozen; a new public build is not a rerun of every historical check.
- **User gameplay:** seven reported special-item effects and the current Salt consumption/effect/Yokai-ki-hit/interruption test are separately confirmed. Sampled recovery in Hino-Enma actions 91/92 does not establish gameplay coverage of the additional Common 205/85 paths or every Salt/enemy combination.

The public CPU suite has **23 passed checks**, separate from the 23 local native-code checks: 8 retained door-instance checks in tests/test_latched_door_instances.py, 5 new item checks in tests/test_special_items_portable.py and 10 new Salt checks in tests/test_salt_recovery_portable.py. The item checks cover owned dispatch, definitions/events/clips and branch/candle eligibility. The Salt checks cover bounded token ownership/cleanup, synthetic 205/85/96/rear route guards, two required clip slots, rejection cases and event catch-up. Native damage/event engines, inventory commit and rendered animations do not execute.

Private code snapshots, raw process-state reports, memory addresses, crash dumps and game resources are excluded. The eight retained public door-instance CPU checks use explicit stubs for native action lookup, motion indexing and action setting; they do not execute the native queue, door scripts or rendered animation.

See [Beta 5 release notes](releases/1.0.0-beta.5.md), [Beta 5 validation](validation-beta5.json) and historical [Beta 4.1 validation](validation-beta4.1.json). Source and EXE verification do not imply renewed cold first-enable, all-mission, save/load, direct CT enable or multi-PC validation.

## Packaging and release

Use a clean reviewed source commit. From the Git checkout, package both verified builds with:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha>
~~~

Packaging requires the exact HEAD commit and a clean tree. It produces exactly two files under artifacts/dist/:

- Nioh-HinoEnma-1.0.0-beta.5-windows-x64.exe
- Nioh-HinoEnma-1.0.0-beta.5-source.zip

The source ZIP exports exact committed Git blobs rather than copying the working directory. It refuses game resources, private data directories, dependency installations, binary build artifacts, logs and symlinks. It includes the guarded CT as source in ct/, alongside the complete launcher, pure native source, frozen profile, build tools, pinned dependency requirements and documentation. The source manifest records every committed path, Git blob, size and SHA-256.

build-info/ contains the source manifest, component inventory, portable verification reports, EXE checksum and build provenance. The Release body contains the exact source commit/tree and both attachment hashes. CI stores provenance attestations with GitHub and links the attestation in the Release body. No extra checksum, CT, runtime ZIP, manifest or attestation file is uploaded as a Release attachment.

The owner explicitly requested this Beta 5 publication. Only the first push of exact 1.0.0-beta.5 / local 0.58 may automatically prepare an immutable annotated tag, create a Draft, inspect both downloaded assets and the complete source ZIP, then publish as Pre-release with latest=false and verify again. Existing tags and assets are never replaced. Other versions and workflow_dispatch remain Draft-only unless separately authorized; manual dispatch requires the full expected commit SHA.

Before tag creation and immediately before publication, the workflow requires a clean checkout, the same source HEAD and unchanged remote main. Readback checks exact tag/source/tree, notes, publisher and uploader identities, asset names/counts/sizes/hashes, complete source contents and attestation source/workflow/subjects. An API transport fallback must compare local/remote Git trees and record its use.

For local or downloaded assets, verify the source ZIP against the exact public Git checkout:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha> --verify-source-zip <source.zip> --exe <release.exe>
~~~

Attestation statement and subject checks do not by themselves claim independent cryptographic verification. A CI attestation identifies CI-built bytes; it does not attest a separate local EXE, certify gameplay or replace Windows Authenticode signing.
