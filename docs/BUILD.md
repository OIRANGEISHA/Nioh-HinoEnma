# Build and verification

Beta 5.1 Hotfix 1 retains Beta 5.1 / local 0.59 and adds the four-hook ladder revision, for 59 hooks. Public metadata is separate from local test versions. Building requires Windows x64 and the .NET Framework C# compiler, not Nioh files or Cheat Engine. The source ZIP contains the reviewed Git-tracked source; its build-info directory records the exact source commit/tree, source inventory, EXE checksum, portable verification, component inventory and build provenance.

## Build and portable checks

Python 3.10+ is required only for payload regeneration, developer verification and packaging. Install the pinned optional development dependencies in the project directory. Unicorn 2.1.4 is used for developer CPU checks; the standalone EXE does not include or require Unicorn, Python or Cheat Engine.

~~~powershell
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python -m unittest discover -s tests -p "test_*.py"
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.1.hotfix.1-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.1.hotfix.1-windows-x64.exe --report artifacts/Release/verification.json
~~~

Edit assembly in src/, then regenerate the C# profile and matching CT with python tools/build_profile.py. The pure public source chain reconstructs all 59 hooks from public instruction signatures without importing private verifiers or reading research files. Compare every payload, patch, signature, slot and target with the frozen local adaptation. Do not substitute arbitrary game hashes or signatures.

Outputs are ignored under artifacts/Debug and artifacts/Release. Release is optimized x64 GUI with asInvoker. Each build must pass 23 C# refusal/recognition/transaction checks and 708 payload/patch comparisons across 59 hooks and 12 layouts, with generated source matching exactly and no game access. Portable source/CT checks additionally check label uniqueness, native branch entry boundaries and code/data layout. tools/verify.py --preview creates an offscreen UI image.

## Evidence boundaries

Keep three classes of evidence distinct:

- **Public portable checks:** source reconstruction, assembly, relocation, injector refusal/recognition and public CPU regressions with explicit Win64 native-call stubs. These checks do not read private game-code inputs or execute the complete native game engine, item damage or rendered animation.
- **Local native-code regressions:** the private integrated ladder checks passed 50 tests and 693 CPU comparisons, plus 660 comparisons confirming the prior 55 hooks remain unchanged across 12 layouts. Private verified native-code inputs and raw reports are not distributed. The earlier local test EXE passed 22 self-checks and 708 comparisons; it is distinct from this public build, which adds a transaction-guard self-check.
- **User gameplay:** the accepted second temporary ladder revision was user-confirmed for upward/downward climbing, per-step motion and exit height. Read-only observation recorded two distinct ladder objects and their transitions. Every ladder and enemy interruption has not been verified. Final public EXE cold first-enable remains untested.

Run the retained public door, special-item, Salt and post-defeat tests along with the new portable ladder tests. Public ladder checks use synthetic actor/action/motion/ladder records; they do not execute rendered gameplay. The exact test and comparison counts from this build are recorded in [Hotfix validation](validation-beta5.1-hotfix1.json), separately from private native-input and historical gameplay evidence. Portable native-call stubs do not execute the complete native damage/event engine or inventory commit.

Private code snapshots, raw process-state reports, memory addresses, crash dumps and game resources are excluded. The eight retained public door-instance CPU checks use explicit stubs for native action lookup, motion indexing and action setting; they do not execute the native queue, door scripts or rendered animation.

See [Hotfix release notes](releases/1.0.0-beta.5.1.hotfix.1.md), [Hotfix validation](validation-beta5.1-hotfix1.json) and historical [Beta 5.1 validation](validation-beta5.1.json). Source and EXE verification do not imply renewed cold first-enable, all-mission, save/load, direct CT enable or multi-PC validation.

## Packaging and release

Use a clean reviewed source commit. From the Git checkout, package both verified builds with:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha>
~~~

Packaging requires the exact HEAD commit and a clean tree. It produces exactly two files under artifacts/dist/:

- Nioh-HinoEnma-1.0.0-beta.5.1.hotfix.1-windows-x64.exe
- Nioh-HinoEnma-1.0.0-beta.5.1.hotfix.1-source.zip

The source ZIP exports exact committed Git blobs rather than copying the working directory. It refuses game resources, private data directories, dependency installations, binary build artifacts, logs and symlinks. It includes the guarded CT as source in ct/, alongside the complete launcher, pure native source, frozen profile, build tools, pinned dependency requirements and documentation. The source manifest records every committed path, Git blob, size and SHA-256.

build-info/ contains the source manifest, component inventory, portable verification reports, EXE checksum and build provenance. The Release body contains the exact source commit/tree and both attachment hashes. CI stores provenance attestations with GitHub and links the attestation in the Release body. No extra checksum, CT, runtime ZIP, manifest or attestation file is uploaded as a Release attachment.

The owner explicitly authorized the one-time Actions replacement in `.github/workflows/hotfix.yml`, restricted to version 1.0.0-beta.5.1.hotfix.1 and Release ID 407938999. It binds the new annotated Hotfix tag to the exact reviewed source commit and reuses that release record with the Hotfix title/body and exactly two new attachments. Download and verify the new assets before removing only the two superseded Beta 5.1 attachments. Keep the original Beta 5.1 annotated-tag object 4590de9c41d5954541b5f34e6a05476a9eb6a4d2 and historical committed source/release/validation records; other releases remain unchanged. Finish as Pre-release with latest=false and record Actions identities, source/tag/asset checks and final readback. The general release workflow and other versions remain Draft-only without separate authorization.

Before tag creation and immediately before publication, the workflow requires a clean checkout, the same source HEAD and unchanged remote main. Readback checks exact tag/source/tree, notes, publisher and uploader identities, asset names/counts/sizes/hashes, complete source contents and attestation source/workflow/subjects. An API transport fallback must compare local/remote Git trees and record its use.

For local or downloaded assets, verify the source ZIP against the exact public Git checkout:

~~~powershell
python tools/package.py --source-commit <full-reviewed-commit-sha> --verify-source-zip <source.zip> --exe <release.exe>
~~~

Attestation statement and subject checks do not by themselves claim independent cryptographic verification. A CI attestation identifies CI-built bytes; it does not attest a separate local EXE, certify gameplay or replace Windows Authenticode signing.
