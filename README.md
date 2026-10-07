# Nioh Hino-Enma

[简体中文](README.zh-CN.md)

**Current version: 1.0.0 Beta 1 / Pre-release.**

A standalone Windows tool that replaces the playable character in **Nioh: Complete Edition** with Hino-Enma while preserving her model and moveset. This first public Beta includes the locally tested interaction fixes and adds player growth, armor and selected melee-weapon bonuses to the Boss baseline.

## Download and use

Get the Windows x64 EXE or ZIP from [Beta 1](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1). The ZIP includes the EXE and Chinese instructions. You do not need Cheat Engine or Python to use the EXE.

1. Start the Steam game normally and stop at **NEW GAME / CONTINUE**.
2. Run the tool. After it reports enabled, load a mission.
3. The newly created player becomes Hino-Enma. You can close the tool.
4. Run it again after restarting the game. If already playing as William, return to the main menu before enabling it.

Repeated runs recognize the existing installation. The tool checks the exact executable and instruction signatures; an unsupported build is refused. If access fails, try running the tool as administrator.

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

The recorded keyboard bindings are the tester's current settings: **J** kick, **I** umbrella, **K** evade, **Shift** restore ki, **Q + Space** flight, **1** life drain. Other bindings may differ.

## Known limitations

- Life drain cannot grab the reported non-humanoid first-mission Boss second phase.
- Use recovery/buff items from the bag; shortcut keys may conflict with Boss skills. Sacred Water is confirmed; Elixir healing and every other eligible item have not been individually verified.
- Weapon HUD data and isolated rendering paths were checked, but the final on-screen icon still awaits explicit confirmation.
- Individual armor/weapon affixes, elemental effects and measured hit-damage differences have not all been tested.
- Ladders, dialogue, shrines, scripted events, all mission transitions and all interactable variants remain unverified.
- The included [CT](ct/Nioh_HinoEnma_1.24.8_Beta1.CT) uses the same scoped hooks; enabling it directly inside Cheat Engine has not been tested. Use either the CT or EXE for a game session.
- This Beta is unsigned with Authenticode. Build provenance and file checksums describe origin and integrity; they are separate from Windows code signing.

## Validation and development

See [Beta 1 release record](docs/releases/1.0.0-beta.1.md), [build instructions](docs/BUILD.md), [development/release standard](DEVELOPMENT_RELEASE_STANDARD.md) and [credits/components](NOTICE.md).

The prior local adaptation passed **89 Python checks**, **12 C# checks**, and **252 relocation comparisons**. Those local research checks include verified game-code snapshots and are not claimed to be portable CI tests. The public source can regenerate the payload profile and run the C# checks and relocation comparison without game resources. Public Beta packaging changes version labels and release metadata; its native payloads are compared with the tested adaptation.

Report an issue with the game build, mission, interaction object, expected result and actual response. Do not attach saves or process dumps unless you intentionally want to share them.
