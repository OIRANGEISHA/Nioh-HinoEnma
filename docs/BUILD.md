# Build and verification

The repository contains the complete standalone launcher source and a generated, version-locked payload profile. Building the EXE does not require Nioh files or Cheat Engine.

## Windows build

On Windows x64 with the .NET Framework C# compiler:

```powershell
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
```

Output is under `artifacts/<configuration>/`. The optimized Release uses x64, Windows GUI subsystem and `asInvoker`; build outputs are ignored by Git.

Packaged release assets use the separate `artifacts/dist/` directory. Windows paths are case-insensitive, so `Release` and `release` cannot name separate directories.

## Regenerate and compare payloads

Python 3.10+ is optional for developer verification. Keep packages in the project directory:

```powershell
python -m pip install --target artifacts/python-deps -r requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path artifacts/python-deps).Path
python tools/build_profile.py --check
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.2-windows-x64.exe --report artifacts/Release/verification.json
```

Edit native assembly in `src/`, then regenerate `launcher/Profile.generated.cs` with `python tools/build_profile.py`. The frozen `profiles/steam-1.24.8.json` records verified instruction boundaries and signatures. A changed game build requires new research and validation, not an arbitrary version/hash replacement.

The Beta 2 verifier executes 19 C# refusal/recognition/transaction checks and compares all 40 payloads across 12 layouts (480 comparisons) against independently assembled Python output. It does not attach to or modify a running game. `--preview` additionally creates an offscreen UI image for visual review.

Beta 2 uses the native payloads of local 0.35. Public version, UI and release metadata are separate from that local version number. Compare payloads, hook sites and native targets with the current local profile before publication; do not substitute arbitrary signatures or game hashes. The latest resource-ID width correction passed offline checks, and the user reconfirmed digit 9 startup, guardian attack and repeat after retirement. The final public EXE recognized the enabled 40-hook session using read-only inspection. Its first injection into a fresh Nioh process remains a separate, unperformed gameplay check.

## Release process

Commit the reviewed source and keep a clean tree. For the authorized upload of **1.0.0-beta.2 only**, the first push changing `version.json` on `main` can run the release workflow. It skips all other versions and any existing Beta 2 tag or release without changing them. This is a one-time publication path, not automatic publication for future versions.

The workflow builds Debug and Release from that exact commit, verifies payloads, creates checksums/provenance and an annotated tag, then prepares a Draft Pre-release as `github-actions[bot]`. Before publication it downloads all 11 assets and compares their names, sizes and SHA-256, checks the source commit, tag, uploader identity, manifests, checksum sidecars and attestation statement's subjects/workflow/source. This readback checks consistency and attestation semantics; it is not independent cryptographic signature verification. Only that first Beta 2 push can publish the verified Draft as a Pre-release with `latest=false`, followed by another asset/source/identity readback. Existing tags or release assets are never overwritten.

Manual workflow dispatch still requires the exact expected commit SHA and retains the verified Draft for final inspection and publication. Future versions use that manual Draft-only path.

The latest local adaptation passed 413 Python research checks using private verified game-code snapshots. Those tests, snapshots and process-state reports are excluded from publication and are not claimed as portable CI. Their scope is documented in the [Beta 2 release record](releases/1.0.0-beta.2.md). Repository CI uses the portable C# and payload checks described above. Beta 1's original verification record remains unchanged.
