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
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.1-windows-x64.exe --report artifacts/Release/verification.json
```

Edit native assembly in `src/`, then regenerate `launcher/Profile.generated.cs` with `python tools/build_profile.py`. The frozen `profiles/steam-1.24.8.json` records verified instruction boundaries and signatures. A changed game build requires new research and validation, not an arbitrary version/hash replacement.

The verifier executes 12 C# refusal/recognition/transaction checks and compares all 21 payloads across 12 layouts (252 comparisons) against independently assembled Python output. It does not attach to or modify a running game. `--preview` additionally creates an offscreen UI image for visual review.

## Release process

Commit the reviewed source, keep a clean tree and run the manual GitHub workflow with the exact expected commit SHA. The workflow builds Debug and Release from that commit, verifies payloads, creates checksums/provenance, prepares an annotated tag and Draft Pre-release, and leaves the draft for final inspection and publication. Existing tags or release assets are not overwritten.

The original 89 local research tests used private verified game-code snapshots; those snapshots and local process-state reports are excluded. Their scope is documented in the release record. The repository CI checks are the portable C# and payload checks described above.
