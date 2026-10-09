# Nioh Hino-Enma development and release standard

Adapted for this Windows game tool from [RapidBench DEVELOPMENT_RELEASE_STANDARD.md](https://github.com/OIRANGEISHA/Rapidbench/blob/main/DEVELOPMENT_RELEASE_STANDARD.md), document 1.1. Android packaging, ABI splits, APK signing and benchmark scoring requirements do not apply to this project.

## Required publication controls

- Use Semantic Versioning with increasing Beta numbers and immutable public versions. Current Beta 5.1 is 1.0.0-beta.5.1, tag v1.0.0-beta.5.1, incorporating local 0.59. Beta releases are GitHub Pre-releases with latest=false. Retain all prior public tags, assets and historical records unchanged.
- Release Owner: **OIRANGEISHA**. Record the actual source author/tagger and upload identity. The owner-authorized Actions publisher may prepare tag, draft and assets; its uploads must be identified as github-actions[bot].
- Use Conventional Commits and record the exact source commit/tree with a clean reviewed checkout. An API transport fallback must compare local/remote tree hashes and record its use.
- Keep requirements, compatibility, bilingual README, changelog, source metadata, generated source, CT source and release notes consistent with the shipped public version and its local adaptation.
- Preserve relevant regression coverage. Build Debug and optimized x64 Release. Beta 5.1 requires 22 portable C# checks and 660 payload/patch comparisons for each build, spanning 55 hooks and 12 layouts. Keep the previous 50 hooks unchanged; the five additions implement the scoped post-defeat pairing, restoration and damage/healing guards. Distinguish public portable checks with explicit native-call stubs, local regressions using private verified native-code inputs, and user gameplay. Historical frozen checks are not newly rerun checks.
- Publish only selected tool/source/documentation files. Do not publish credentials, personal paths, raw private logs, game resources, historical third-party CT archives, dependency binaries or memory/code dumps.
- Export the complete source ZIP from exact Git-tracked blobs. Refuse private directories and binary artifacts, verify every source file against the reviewed commit, and include build instructions and pinned development requirements.
- The current owner-requested Release attachment inventory is exactly **the Windows x64 EXE and the source ZIP**. Store source-linked checksums, verification, component inventory and build provenance inside source ZIP build-info/ and/or the Release body. Retain CI attestations with GitHub and link them in the body; do not upload extra Release attachments.
- Check the exact game image and native signatures at runtime, decline unrecognized modifications and keep repeated enable idempotent.
- Prepare a Draft and immutable annotated tag, inspect exact source/tag/assets before publishing as Pre-release, then download and verify again. Never replace an existing tag or asset.
- Verify actual owner/authorized publisher identities, remote source commit/tree, annotated tag, notes, exact two-asset names/counts/sizes/SHA-256 and complete source ZIP contents. The published release and asset IDs must match the inspected draft.
- Before tag creation and immediately before publication, require the same clean source commit and unchanged remote main. The owner explicitly authorized this Beta 5.1 publication; only the first push of exact 1.0.0-beta.5.1 / local 0.59 may publish automatically. Other versions and manual dispatch remain Draft-only unless separately authorized; manual dispatch must supply the exact expected commit SHA.

## Beta-specific scope and deferred items

- This is a portable Windows Beta, not an APK or installer. Android installation/certificate gates are inapplicable.
- No Windows Authenticode signer is configured. Do not describe a Beta as signed; protected signing is a future Stable requirement.
- Local game tests apply only to the recorded Steam build and tested flows. Public packaging does not establish new cold-injection, full mission-transition, save/load or multi-PC coverage.
- Beta 5.1's post-defeat visual grab is scoped to the reported Nouhime / Yuki-Onna with loaded compatible resources. The temporary revision's two consecutive user-confirmed grabs and defeated-pose restoration must be distinguished from the final production build and dynamic-binding/reload verification. A zero-HP target receives no additional damage or healing; no revival or direct mission/save-state write is added. Do not claim all defeated Bosses or corpses are supported.
- Beta 5's seven reported new special-item effects and current Salt use/interruption result are user-confirmed. Salt's additional Common 205/85 routes have local CPU coverage only and remain unobserved in gameplay. Do not claim complete Salt interruption/enemy coverage.
- Document compatible shortcut items at slot 2 on the **first** item shortcut bar. Other shortcut positions retain Boss moves. Some non-critical item use remains unfixed.
- Immutable-release enforcement depends on repository configuration. If unavailable, retain tagged source, recorded hashes/provenance and the prohibition on replacing published assets.
- CI attestation covers the exact CI-built EXE and source ZIP only. It does not attest a separately built local EXE, certify gameplay correctness or replace code signing.
- Checks of an attestation statement, source and subjects are distinct from independent cryptographic verification.

## Change control

Keep fixes scoped, record known defects, preserve Boss base-plus-bonus calculation, and do not add undocumented dependency upgrades or silently broaden compatibility. RC/Stable requires renewed gameplay and broader compatibility review before release. User instructions govern selected release scope; this two-attachment policy supersedes the historical Beta 1–3 attachment inventory.
