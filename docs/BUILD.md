# Build and verification

Beta 3 corresponds to local 0.44 with 45 hooks. Public metadata is separate from the local version. Builds require Windows x64 and the .NET Framework C# compiler, not Nioh files or Cheat Engine.

## Build and portable checks

```powershell
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.3-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.3-windows-x64.exe --report artifacts/Release/verification.json
```

Edit assembly in `src/`, then regenerate the C# profile and matching CT with `python tools/build_profile.py`. Compare every payload/patch/signature/slot/target with local 0.44; do not substitute arbitrary game hashes or signatures. Outputs are ignored under `artifacts/<configuration>/`; prepared assets use separate `artifacts/dist/`. Release is optimized x64 GUI with `asInvoker`.

Public Debug/Release each passed 19 C# refusal/recognition/transaction checks and 540 payload/patch comparisons (45 hooks across 12 layouts), generated source exact, without game access. Pure-source/CT validation passed, including 275 unique labels and three rejection cases. `tools/verify.py --preview` creates an offscreen UI image; this version’s preview was reviewed without clipping. New public/CI builds receive their own hashes.

## Evidence boundaries

Local 0.43’s 499 Python research checks are frozen; local 0.44 passed 8 new hot-spring checks, not 507 rerun checks. Private game-code inputs/raw reports are excluded and are not portable CI. See [sanitized validation](validation-beta3.json) and [release notes](releases/1.0.0-beta.3.md).

Current-pool animation/Buff/exit and same-version William’s short wait are confirmed, without precise timing or older Hino exit-branch equality claims. Reported elements, Kato recovery and normal four-stat refresh have user confirmation. Public cold first-enable, direct CT enable, actual level spending, new growth save/load and damage measurements remain pending.

## Release process

Follow [the release standard](../DEVELOPMENT_RELEASE_STANDARD.md): Conventional Commits, exact clean reviewed source commit/tree, selected files, immutable prior versions, source-linked hashes/provenance and actual publisher identity.

The owner explicitly authorized this Beta 3 upload. A one-time push gate restricted to its exact version/commit/unused tag may prepare the annotated tag/Draft, verify all selected assets/source/identities, publish as Pre-release with `latest=false`, then verify again. Existing versions cannot be overwritten. The Beta 2 scope remains restricted; future versions and manual dispatch remain Draft-only with exact expected commit.

Read back downloaded asset names/sizes/SHA-256, tag/source, publisher/uploader identities, manifests and any attestation source/subjects/workflow. Record API transport fallback, compare local/remote trees and synchronize the checkout. Attestation semantics are not independent cryptographic signature verification; a CI attestation covers CI-built artifacts only. Authenticode is not configured; neither checksums nor attestation certify gameplay.
