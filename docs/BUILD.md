# Build and verification

Beta 5.3 contains 70 hooks: the unchanged 60-hook Beta 5.2 basis plus ten scoped map-preview hooks. Public version `1.0.0-beta.5.3`, file version `1.0.0.64` and tag `v1.0.0-beta.5.3` are separate from the retained private profile version. The distributed source ZIP is exported from the exact reviewed Git commit, rather than copied from a local research folder.

## Rebuild on Windows x64

The standalone EXE requires Windows x64 and .NET Framework; users do not need Python or Cheat Engine. Python 3.10+ and pinned development dependencies are used only to regenerate or verify source. Offline rebuilding needs no Nioh executable, game assets or private research inputs.

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
python tools/verify.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.3-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.3-windows-x64.exe --report artifacts/Release/verification.json
```

Edit pure assembly in `src/` or the menu builders in `tools/`, regenerate the embedded C# profile and matching CT with `python tools/build_profile.py`, then repeat the checks. The menu verifier binds the reviewed source/test hashes; a deliberate source change requires renewed review and proof. Do not substitute arbitrary game hashes or native signatures.

The profile allocates `0x2D000` bytes. Six data pages remain writable and non-executable; code capacities receive executable, read-only protection. The camera values 740 and −45 are computed loads, with private zero-initialized instance stamps. No recorded live heap address is used. The CT emitter preserves the source's decimal operand meaning when rendering AutoAssembler hexadecimal values; compare actual relocated CT and EXE bytes.

Supported older 55/59/60-hook installations are read-only restart identities. The tool refuses damaged or unknown configurations and does not migrate older allocations. Current installation dependencies include complete menu native-function instruction-pointer and saved-return exclusions.

## Evidence boundaries

The final public source passed 133 regression tests (121 retained plus 12 release-evidence refusal checks) and 25 portable menu tests, including 2,490 byte comparisons and 10,005 synthetic CPU comparisons across 12 ASLR layouts. Public-source Debug and Release each passed 28 C# self-checks, 840 current-profile comparisons and 2,088 complete prior-profile comparisons. Source/CT verification passed for 70 hooks, 636 unique labels and 840 namespace comparisons. The immutable Beta 5.2 baseline verifier passed all 60 original template/fixup sets, 720 payload comparisons and 720 patch comparisons. Actual reports and local public-source EXE hashes are recorded in [Beta 5.3 validation](validation-beta5.3.json); record final CI-built and downloaded asset hashes separately.

Public CPU fixtures use synthetic records and explicit Win64 native-call stubs. They test source, ownership, ABI, scope lifetime, fallback and relocation; they do not prove real game object lifetime, resource execution, native damage or inventory commits. Private game-code inputs, raw memory reports and game resources are excluded from source and CI. Earlier validation files retain their historical scope.

Temporary in-game revisions were user-confirmed for the Hino-Enma map/base preview, native idle, removal of William overlays and accepted camera framing. A fresh-process first enable/reload of the final public EXE has not been gameplay-tested. Every in-mission menu, display ratio, mission transition and save/load flow is not claimed to be covered. See [Beta 5.3 notes](releases/1.0.0-beta.5.3.md) and [keyboard documentation](键位说明.md).

## Packaging and publication

From the exact clean, reviewed Git checkout:

```powershell
python tools/package.py --source-commit <full-reviewed-commit-sha>
```

The public package has exactly two Release attachments:

- `Nioh-HinoEnma-1.0.0-beta.5.3-windows-x64.exe`
- `Nioh-HinoEnma-1.0.0-beta.5.3-source.zip`

The source ZIP exports committed Git blobs and records every selected path, blob ID, size and SHA-256. It includes the complete launcher, pure source, generated profile, matching CT, pinned development requirements, bilingual instructions and verification tools. Packaging refuses private directories, game assets, dependency binaries, build artifacts and symlinks.

The ZIP's `build-info/` records the exact source commit/tree, source inventory, portable verification reports, EXE checksum, component inventory and build provenance. The Release body records both attachment hashes, sizes and actual publisher/uploader identities. Keep CI attestations with GitHub and link them in the body; do not add checksum, CT, runtime ZIP or attestation files as separate Release attachments.

The owner authorized publishing this Beta 5.3 through the existing version-scoped Actions flow. Verify the same clean source and unchanged remote main before tag creation and immediately before publication. Inspect the annotated tag and Draft assets, publish as Pre-release with `latest=false`, then download both attachments and verify their bytes, complete source inventory and final IDs. Never move earlier tags or replace earlier attachments. The historical Beta 5.1 Hotfix replacement remains a separate, narrowly authorized exception.

To verify downloaded files against the exact public Git checkout:

```powershell
python tools/package.py --source-commit <full-reviewed-commit-sha> --verify-source-zip <source.zip> --exe <release.exe>
```

An API transport fallback must record its use and compare local/remote Git trees. Attestation source/subject checks are separate from independent cryptographic verification. A CI attestation covers only the CI-built bytes and does not attest a separate local EXE, certify gameplay or replace Windows Authenticode signing. This Beta remains unsigned.
