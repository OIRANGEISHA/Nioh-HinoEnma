# Nioh Hino-Enma Beta 5.6

[简体中文](README.zh-CN.md)

For Steam Nioh: Complete Edition 1.24.08. Includes the Abyss next-floor interaction/loading/cancellation repair, per-player resource lifetime, and Kodama “guide to shore” interaction repair. Original Beta5.5 outbound boating passed separately.

Restart the game completely, stop at NEW GAME / CONTINUE, and enable Hino-Enma with the Beta5.6 EXE. Enable again after each restart. Windows x64/.NET Framework4.x; the standalone EXE needs no CE or Python.

Known unresolved bugs: Living Weapon (99 Weapon) activation lacks its animation and shockwave; both are currently replaced incorrectly with Guardian Spirit summoning. Ninjutsu items currently cannot be used. These issues will be addressed later.

Beta5.6 changes public version/build metadata and uses the same82 native payloads as the guide fix tested with a full Beta5.5.1 game restart. Preserve that exact-file result in [gameplay evidence](docs/guide-restart-gameplay.json); it is not a new Beta5.6 EXE gameplay test. Current compiled verification and9 ASLR comparisons bind the new version separately. The inherited continuous-floor/cancel/normal-cleanup evidence remains unchanged.

See [release notes](docs/releases/1.0.0-beta.5.6.md), [build](docs/BUILD.md), [keys](docs/键位说明.md), and [historical features](README-beta5.4.2.md). All floors, difficulties, interaction variants and multiplayer appearance are not comprehensively tested. Direct CE use remains untested; lifetime hooks end on a full game exit.

Release assets are the Windows EXE and complete Git-tracked UTF-8 source ZIP. Actions-built assets have separate hashes/provenance from the local gameplay-tested file. [NOTICE](NOTICE.md) retains original attribution; game files, saves, credentials and raw private dumps are excluded.
