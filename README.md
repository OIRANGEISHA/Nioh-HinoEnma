# Nioh Hino-Enma Beta 5.6.1

[简体中文](README.zh-CN.md)

For Steam Nioh: Complete Edition 1.24.08. Beta 5.6.1 restores Living Weapon startup on main-row **9**, including the startup animation, shockwave, native gauge consumption and natural completion. Pressing 9 again during active Living Weapon retains Guardian Spirit summoning after the guardian retires and the character returns to ground idle.

Restart the game completely, stop at NEW GAME / CONTINUE, and enable Hino-Enma with the Beta 5.6.1 EXE. Enable again after each game restart. Windows x64/.NET Framework 4.x; the standalone EXE needs no CE or Python.

The exact standalone EXE passed a fresh-process test with automatic resource discovery and no temporary patch or manually seeded binding. Read-only observation recorded 82 matching hooks, an initially empty binding, one successful native startup, and charge 1400 → 0. The user confirmed the animation, shockwave, gauge display, natural ending, movement and menus. See [gameplay evidence](docs/living-weapon-beta561-gameplay.json). This test used the same weapon and Guardian Spirit, item type 11/family 2; other equipment and stages have not been comprehensively tested.

**Known unresolved bug: Ninjutsu items currently cannot be used.**

Includes the earlier Orochi/Nine Tails execution, Abyss next-floor interaction/loading/cancellation, per-player resource lifetime and Kodama “guide to shore” fixes. Their historical gameplay records retain their original version identities; these scenarios were not replayed in this Living Weapon test. Multiplayer appearance is not comprehensively verified. CT payloads match offline; direct CE activation has not been gameplay-tested. Lifetime hooks end on a full game exit.

The GitHub Beta 5.6.1 release preserves the exact cold-tested EXE. Its source ZIP is generated from the final committed UTF-8 source, and its manifest records the commit, tree and downloaded asset checks. The package includes the exact tested Windows EXE, matching CT, UTF-8 source and repair/validation records. A rebuild may have a different EXE hash and does not inherit the exact-file gameplay result.

See [release notes](docs/releases/1.0.0-beta.5.6.1.md), [build instructions](docs/BUILD.md), [keys](docs/键位说明.md), and [historical features](README-beta5.4.2.md). [NOTICE](NOTICE.md) retains original attribution; game files, saves, credentials and raw private dumps are excluded.
