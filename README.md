# Nioh Hino-Enma

[简体中文](README.zh-CN.md)

**Current version: 1.0.0 Beta 2 / Pre-release.**

A standalone Windows tool that replaces the playable character in **Nioh: Complete Edition** with Hino-Enma while preserving her model and moveset. Beta 2 includes the local 0.35 fixes, native ladder movement and Living Weapon support. Player growth, armor and selected melee-weapon bonuses are added to the Boss baseline.

## Download and use

Get the Windows x64 EXE or ZIP from [Beta 2](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.2). The ZIP includes the EXE and Chinese instructions. You do not need Cheat Engine or Python to use the EXE.

1. Start the Steam game normally and stop at **NEW GAME / CONTINUE**.
2. Run the tool. After it reports that the next character will be Hino-Enma, load a mission.
3. The newly created player becomes Hino-Enma. You can close the tool.
4. To switch to William or Hino-Enma, select that character in the tool, return to the main menu and load the mission again. Run the tool again after restarting the game.

Repeated runs recognize the existing installation and retain the character choice for that game process. A new game process defaults to Hino-Enma after enabling. The tool checks the exact executable and instruction signatures; an unsupported build is refused. If access fails, try running the tool as administrator. To return to an older public version, exit Nioh first and use the unchanged [Beta 1 release](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1).

## Compatibility

- Windows x64 with .NET Framework 4.x and the **Steam Complete Edition 1.24.8** build, shown as **1.24.08** in the game window.
- Exact supported executable SHA-256: `0c3508c6b4d0696d84423949df9faccb3f9c6d93833854e1e17a78d66defc389`.
- Epic and other executable builds have not been adapted. Matching a version label alone is insufficient.
- The EXE changes the current process; game installation files do not need replacement. Game saves continue through the game's normal behavior; complete save/load and mission-transition coverage remains unverified.

## Implemented and tested

- Visible Hino-Enma replacement and basic movement, kick, umbrella attack and evasion.
- Locally tested boxes, key doors, prison doors, a door opened from one side and corpse loot.
- Flight camera correction; Himorogi Fragment from the bag; Kodama guide-home; Sacred Water from the bag; the reported blood tomb now summons a revenant.
- Native growth and armor recalculation added to Boss HP, ki and defense. User confirmed changes after re-equipping armor.
- Selected melee-weapon attack increment is added to Boss attacks. A sole equipped weapon is selected even if the other slot is empty. Weapon HUD refresh compatibility is included.
- Complete life-drain grab animations are confirmed on the reported Yoki, Dwellers and Onryoki. Target/resource checks remain; this is not a claim of support for every enemy or Boss.
- Native ladder interaction, climbing up and down, and leaving the ladder are confirmed. Hino-Enma movement, J/I and digit 5 work after leaving; ladder movement no longer invokes her roar.
- F6 purifies nearby Yokai Realm pools. Digit 5 directly invokes the roar on the ground or in the air; Alt retains the flight/dive move.
- Bag item compatibility includes the reported Ninja's Locks, Small Spirit Stone and self-recovery/buff paths. Dojo compatibility covers the reported locks, ki pulse, purification, weapon-switch and Living Weapon steps; shooting practice continues after defeating its target.
- Digit 9 starts native Living Weapon at full charge while retaining Hino-Enma's moves. Native attribute reinforcement is confirmed. Guardian attacks and repeated summons, including use with the tester's infinite-Living-Weapon trainer, are confirmed; measured hit damage remains untested.
- Fix the reported digit 9 full-charge startup refusal by reading the native resource ID as a 32-bit value. The earlier 64-bit read included unrelated padding. Offline regression passed, and the user confirmed startup, guardian attack and repeat summons after retirement in the corrected version.

The recorded keyboard bindings are the tester's current settings: **J** kick, **I** umbrella, **K** evade, **Shift** restore ki, **Q + Space** flight, **1** life drain, **5** roar, **F6** purification, **9** native Living Weapon/guardian summon. Space handles the compatible dojo ki-pulse/purification steps. Dojo weapon-switch combinations are Space + 2/3 for melee and Space + 1/4 for ranged; T handles the reported Living Weapon teaching step while preserving its Boss attack. Other bindings may differ.

## Known limitations

- Use items from the bag: digits 1–4 conflict with Boss skills. Sacred Water, the reported locks and Small Spirit Stone are confirmed; not every recovery/buff effect or ninjutsu item has been individually verified.
- Weapon HUD data and isolated rendering paths were checked, but the final on-screen icon still awaits explicit confirmation.
- Individual armor/weapon affixes, elemental effects and measured hit-damage differences have not all been tested.
- Ladder and dojo results cover the reported locations; other ladders, dialogue, shrines, scripted events, all mission transitions and interactable variants have not all been verified. Weapon-switch teaching support does not implement actual Boss weapon switching; native shooting is not implemented.
- Living Weapon retains Hino-Enma's body and moves without William's full startup animation or weapon appearance. Guardian summoning does not reproduce William's additional ki cost. Other guardians, controllers and full combat/transition coverage remain unverified.
- The included [CT](ct/Nioh_HinoEnma_1.24.8_Beta2.CT) uses the same scoped hooks; enabling it directly inside Cheat Engine has not been tested. Use either the CT or EXE for a game session. Mixing different versions in one process is not supported.
- The final public Beta 2 EXE's first injection into a fresh game process has not been separately tested. Public version/UI metadata changes are checked against the current local native payloads; the public EXE's read-only diagnosis recognizes the installed local 0.35 code without modifying the game.
- This Beta is unsigned with Authenticode. Build provenance and file checksums describe origin and integrity; they are separate from Windows code signing.

## Validation and development

See [Beta 2 release record](docs/releases/1.0.0-beta.2.md), [build instructions](docs/BUILD.md), [development/release standard](DEVELOPMENT_RELEASE_STANDARD.md) and [credits/components](NOTICE.md). [Beta 1's release record](docs/releases/1.0.0-beta.1.md) remains historical.

The local 0.35 adaptation passed **413 Python research checks**. Portable verification covers **19 C# checks** and **480 relocation comparisons** (40 hooks across 12 layouts). The Python research checks use private verified game-code snapshots and are not portable CI tests or included game resources. The public source can regenerate the profile and run the 19 C# checks and all 480 relocation comparisons without game resources. Public Beta packaging changes version labels and release metadata; its native payloads are compared with the current local adaptation. Final build results, hashes and source commit are recorded with the release assets.

Report an issue with the game build, mission, interaction object, expected result and actual response. Do not attach saves or process dumps unless you intentionally want to share them.
