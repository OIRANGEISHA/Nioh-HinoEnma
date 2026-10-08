# Nioh Hino-Enma development and release standard

Adapted for this Windows game tool from [RapidBench DEVELOPMENT_RELEASE_STANDARD.md](https://github.com/OIRANGEISHA/Rapidbench/blob/main/DEVELOPMENT_RELEASE_STANDARD.md), document 1.1. Android packaging, ABI splits, APK signing and benchmark scoring requirements do not apply to this project.

## Required publication controls

- Use Semantic Versioning with increasing Beta numbers and immutable public versions. Beta 4 is 1.0.0-beta.4, tag v1.0.0-beta.4, incorporating local 0.50. Beta releases are GitHub Pre-releases with latest=false. Retain all prior public tags, assets and historical records unchanged.
- Release Owner: **OIRANGEISHA**. Record the actual source author/tagger and upload identity. The owner-authorized Actions publisher may prepare tag, draft and assets; its uploads must be identified as github-actions[bot].
- Use Conventional Commits and record the exact source commit/tree with a clean reviewed checkout. An API transport fallback must compare local/remote tree hashes and record its use.
- Keep requirements, compatibility, bilingual README, changelog, source metadata, generated source, CT source and release notes consistent with the shipped public version and its local adaptation.
- Preserve relevant regression coverage. Build Debug and optimized x64 Release. Beta 4 requires 19 portable C# checks and 588 payload/patch comparisons for each build, spanning 49 hooks and 12 layouts. Distinguish actual gameplay reports, new regression checks, frozen earlier checks and public portable verification.
- Publish only selected tool/source/documentation files. Do not publish credentials, personal paths, raw private logs, game resources, historical third-party CT archives, dependency binaries or memory/code dumps.
- Export the complete source ZIP from exact Git-tracked blobs. Refuse private directories and binary artifacts, verify every source file against the reviewed commit, and include build instructions and pinned development requirements.
- The current owner-requested Release attachment inventory is exactly **the Windows x64 EXE and the source ZIP**. Store source-linked checksums, verification, component inventory and build provenance inside source ZIP build-info/ and/or the Release body. Retain CI attestations with GitHub and link them in the body; do not upload extra Release attachments.
- Check the exact game image and native signatures at runtime, decline unrecognized modifications and keep repeated enable idempotent.
- Prepare a Draft and immutable annotated tag, inspect exact source/tag/assets before publishing as Pre-release, then download and verify again. Never replace an existing tag or asset.
- Verify actual owner/authorized publisher identities, remote source commit/tree, annotated tag, notes, exact two-asset names/counts/sizes/SHA-256 and complete source ZIP contents. The published release and asset IDs must match the inspected draft.
- Before tag creation and immediately before publication, require the same clean source commit and unchanged remote main. Only the first owner-authorized Beta 4 / local 0.50 push may publish automatically. Future versions and manual dispatch are Draft-only; manual dispatch must supply the exact expected commit SHA.

## Beta-specific scope and deferred items

- This is a portable Windows Beta, not an APK or installer. Android installation/certificate gates are inapplicable.
- No Windows Authenticode signer is configured. Do not describe a Beta as signed; protected signing is a future Stable requirement.
- Local game tests apply only to the recorded Steam build and tested flows. Public packaging does not establish new cold-injection, full mission-transition, save/load or multi-PC coverage.
- Immutable-release enforcement depends on repository configuration. If unavailable, retain tagged source, recorded hashes/provenance and the prohibition on replacing published assets.
- CI attestation covers the exact CI-built EXE and source ZIP only. It does not attest a separately built local EXE, certify gameplay correctness or replace code signing.
- Checks of an attestation statement, source and subjects are distinct from independent cryptographic verification.

## Change control

Keep fixes scoped, record known defects, preserve Boss base-plus-bonus calculation, and do not add undocumented dependency upgrades or silently broaden compatibility. RC/Stable requires renewed gameplay and broader compatibility review before release. User instructions govern the selected release scope; this two-attachment policy supersedes the historical Beta 1–3 attachment inventory.
