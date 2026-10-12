# Nioh Hino-Enma Beta 5.6.2

[简体中文](README.zh-CN.md)

For Steam Nioh: Complete Edition 1.24.08. Beta 5.6.2 fixes main-row **9** failing to start Living Weapon after switching saves or returning to the title screen and reloading. It also supports the different native startup event schemas and independent main/auxiliary animation schedules used by melee weapon families. Startup animation, shockwave, native gauge flow and natural completion are retained.

Restart the game completely, stop at NEW GAME / CONTINUE, and enable Hino-Enma with this version's EXE. Enable again after each game restart. Windows x64/.NET Framework 4.x; no CE or Python needed for the standalone EXE. Exit the game before upgrading.

The corrected FileVersion 1.0.0.76 executable passed a fresh-process, second-load test with Taro Tachi (odachi), all 82 hooks verified, and no temporary patch or manual binding. The user confirmed all startup effects, gauge display/drain and end-state controls. Seven resource families passed offline checks; these are not seven live gameplay tests. Beta 5.6.2 is a versioned rebuild: all runtime payloads and native patches match that tested binary across 12 relocation layouts. The new exact EXE has not been gameplay-tested again. See [evidence](docs/living-weapon-beta562-gameplay.json).

**Known unresolved bug: Ninjutsu items currently cannot be used.** Nonstandard equipment records in downloaded saves remain outside the verified scope; weapon rarity itself is not restricted. Multiplayer appearance is not comprehensively verified.

Includes previous Orochi/Nine Tails executions, Abyss next-floor/loading/cancellation/resource-lifetime and Kodama guide-to-shore fixes. Historical gameplay records keep their original version identities; these scenarios were not replayed for this fix. CT payloads match offline, but direct CE activation has not been gameplay-tested.

[Download Beta 5.6.2](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.6.2): Windows EXE, matching CT, committed UTF-8 source ZIP, complete ZIP, checksums and validation records. Game files, saves, credentials and raw memory dumps are excluded.

See [release notes](docs/releases/1.0.0-beta.5.6.2.md), [build instructions](docs/BUILD.md), [keys](docs/键位说明.md), [historical features](README-beta5.4.2.md), and [NOTICE](NOTICE.md).
