# Build and verification

Beta 4 corresponds to local 0.50 with 49 hooks. Public metadata is separate from the local version. Building requires Windows x64 and the .NET Framework C# compiler, not Nioh files or Cheat Engine. The source ZIP contains all reviewed Git-tracked files; its build-info directory records the exact source commit/tree, source inventory, EXE checksum, portable verification, component inventory and build provenance.

## Build and portable checks

Python 3.10+ is required only for payload regeneration, developer verification and packaging. Install the pinned optional development dependencies in the project directory:

~~~powershell
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.4-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.4-windows-x64.exe --report artifacts/Release/verification.json
~~~

Edit assembly in src/, then regenerate the C# profile and matching CT with python tools/build_profile.py. The pure source chain reconstructs local 0.50 from the public instruction signatures without importing private verifiers or reading research files. Compare every payload, patch, signature, slot and target with the tested local adaptation. Do not substitute arbitrary game hashes or signatures.

Outputs are ignored under artifacts/Debug and artifacts/Release. Release is optimized x64 GUI with asInvoker. Each build must pass 19 C# refusal/recognition/transaction checks and 588 payload/patch comparisons across 49 hooks and 12 layouts, with the generated source matching exactly and no game access. Portable source/CT checks additionally check label uniqueness, native branch entry boundaries and code/data layout. tools/verify.py --preview creates an offscreen UI image.

## Evidence boundaries

Public portable checks validate source, assembly, relocation and injector refusal/recognition behavior. They do not reproduce private native-CPU checks or gameplay tests. Private code snapshots, raw process-state reports, memory addresses, crash dumps and game resources are excluded. The release notes and sanitized validation record distinguish frozen earlier checks, new regression checks, user confirmation and remaining coverage limits.

See [Beta 4 validation](validation-beta4.json) and [Beta 4 release notes](releases/1.0.0-beta.4.md). Source and EXE verification do not imply renewed cold first-enable, all-mission, save/load, direct CT enable or multi-PC validation.

## Packaging and release

Use a clean reviewed source commit. From the Git checkout, package both verified builds with:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha>
~~~

Packaging requires the exact HEAD commit and a clean tree. It produces exactly two files under artifacts/dist/:

- Nioh-HinoEnma-1.0.0-beta.4-windows-x64.exe
- Nioh-HinoEnma-1.0.0-beta.4-source.zip

The source ZIP exports exact committed Git blobs rather than copying the working directory. It refuses game resources, private data directories, dependency installations, binary build artifacts, logs and symlinks. It includes the guarded CT as source in ct/, alongside the complete launcher, pure native source, frozen profile, build tools, pinned dependency requirements and documentation. The source manifest records every committed path, Git blob, size and SHA-256.

build-info/ contains the source manifest, component inventory, portable verification reports, EXE checksum and build provenance. The Release body contains the exact source commit/tree and both attachment hashes. CI stores provenance attestations with GitHub and links the attestation in the Release body. No extra checksum, CT, runtime ZIP, manifest or attestation file is uploaded as a Release attachment.

The owner authorized this Beta 4 upload. Only the first push of 1.0.0-beta.4 / local 0.50 may automatically prepare an immutable annotated tag, create a Draft, inspect both downloaded assets and the complete source ZIP, then publish as Pre-release with latest=false and verify again. Existing tags and assets are never replaced. Future versions and workflow_dispatch remain Draft-only; manual dispatch requires the full expected commit SHA.

Before creating the tag and immediately before publication, the workflow requires a clean checkout, the same source HEAD and an unchanged remote main. Readback checks exact tag/source/tree, notes, publisher and uploader identities, asset names/counts/sizes/hashes, complete source contents and attestation source/workflow/subjects. An API transport fallback must compare local/remote Git trees and record its use.

For local or downloaded assets, verify the source ZIP against the exact public Git checkout:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha> --verify-source-zip <source.zip> --exe <release.exe>
~~~

Attestation statement and subject checks do not by themselves claim independent cryptographic verification. A CI attestation identifies CI-built bytes; it does not attest a separate local EXE, certify gameplay or replace Windows Authenticode signing.
