# Nioh Hino-Enma development and release standard

Adapted for this Windows game tool from [RapidBench DEVELOPMENT_RELEASE_STANDARD.md](https://github.com/OIRANGEISHA/Rapidbench/blob/main/DEVELOPMENT_RELEASE_STANDARD.md), document 1.1. Android packaging, ABI splits, APK signing and benchmark scoring requirements do not apply to this project.

## Required publication controls

- Use Semantic Versioning, increasing Beta numbers and immutable public versions. Beta 1 is `1.0.0-beta.1`, tag `v1.0.0-beta.1`, GitHub Pre-release.
- Release Owner: **OIRANGEISHA**. Source author/tagger are the owner. The owner-authorized repository Actions publisher can prepare tag/draft/assets; record its actual identity instead of presenting the upload as a human upload.
- Use Conventional Commits; record the exact source commit and a clean, reviewed file tree. This is a new repository's initial public release; no prior public Nioh tag exists.
- Keep source, requirements, compatibility, bilingual README, changelog and release notes consistent with the shipped version.
- Preserve relevant regression coverage. Build Debug and optimized x64 Release, run portable checks, and distinguish actual gameplay reports from offline simulation and prior-version checks.
- Publish only explicitly selected tool/source/documentation files. Do not publish credentials, private logs, game resources, old CT archives or memory/code dumps.
- Check the exact game image and code at runtime; decline unrecognized modifications and keep repeated enable idempotent.
- Attach SHA-256, source-linked build provenance and a scoped component inventory. New published versions never overwrite existing tags or assets.
- Prepare all assets in a Draft release and verify source/tag/assets before publishing as Pre-release. Do not mark a Beta as latest stable.
- Verify owner/authorized publisher identities, remote commit/tag, asset hashes and working-tree synchronization after publication. An API transport fallback must compare the local and remote tree hashes and record its use.

## Beta-specific scope and deferred items

- This is a portable Windows Beta, not an APK or installer; Android installation/certificate gates are inapplicable.
- No Windows Authenticode signer is configured. Do not describe the Beta as signed; protected signing is a future Stable requirement.
- Local game tests are valid only for the recorded Steam build and flows. Public-release metadata changes do not imply new cold-injection, full mission-transition or save/load coverage.
- Immutable-release enforcement depends on repository configuration. If unavailable, retain the tagged source, attached hashes and provenance, and do not replace published assets.
- Any CI attestation applies to the CI-built binary only. It does not attest a separately built local EXE, certify gameplay correctness or replace code signing.

## Change control

Keep fixes scoped, record known defects, preserve Boss base-plus-bonus calculation, and do not add undocumented dependency upgrades or silently broaden compatibility. RC/Stable requires renewed gameplay and broader compatibility review before release.
