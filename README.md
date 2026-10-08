# Nioh Hino-Enma

[简体中文](README.zh-CN.md)

**Current version: 1.0.0 Beta 3 / Pre-release.**

A standalone Windows tool that replaces the playable character in **Nioh: Complete Edition** with Hino-Enma while preserving her model and moveset. Beta 3 incorporates local 0.44 and the fixes after Beta 2’s local 0.35 baseline: bag talismans, elemental skills, guardian recovery, level-based Boss stats and native hot-spring animation. Player growth, armor and the selected melee weapon’s native bonuses remain additive.

## Download and use

When its assets are available, get the Windows x64 EXE or ZIP from [Beta 3](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.3). The ZIP includes the EXE and Chinese instructions. You do not need Cheat Engine or Python to use the EXE.

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

## New in Beta 3

- Restore native hot-spring sit/wait/stand/exit. Current-pool animation, Buff and restored movement/J/I are confirmed. Same-version William also automatically stands after a short wait there; exact durations and all pools are not claimed.
- Reported bag Lightning/Fire Talismans and Travel Amulet, including repeated elemental-talisman use. The user confirmed Living Weapon elements on needles, body charge and life drain. Original roar status and auxiliary effects are preserved; a second added element for the roar is excluded.
- Native Kato guardian recovery through shrine recall and death-grave pickup, followed by digit-9 startup and attacks. Other guardians remain pending.
- Native Boss HP/ki/attack/defense curves use a linear mapping from level 1/index 1 to level 400/index 1410, rounding down. Valid saved levels 1–750 are read, mapped levels above 400 are capped, and higher native scene indices are retained. Native growth/equipment/selected-weapon bonuses remain additive. Re-equip armor and close the menu, or reload the character, for normal refresh; no saved levels/points/scene indices or current HP are directly edited. Repeated refresh recomputes base plus bonuses.

## Retained features and tested scope

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

- Signpost Talisman marking is unresolved; roar plus an additional element is excluded. Needle paralysis strength, exact elemental damage/healing and all airborne variants remain unmeasured/unverified.
- Hot-spring wait samples were about 0.062/0.063 seconds for Hino-Enma and 0.079 seconds for William at the reported pool. These do not establish precise timing equality or the exit branch used in older Hino-Enma traces; other pools remain pending.
- Actual level-up spending, new growth save/load and combat-damage quantification remain pending. Attack scalars are not per-hit damage, and derived ki is not measured final ki-bar capacity. Trainers can independently override runtime values.
- Use items from the bag: digits 1–4 conflict with Boss skills. Sacred Water, the reported locks and Small Spirit Stone are confirmed; not every recovery/buff effect or ninjutsu item has been individually verified.
- Weapon HUD data and isolated rendering paths were checked, but the final on-screen icon still awaits explicit confirmation.
- Individual armor/weapon affixes, elemental effects and measured hit-damage differences have not all been tested.
- Ladder and dojo results cover the reported locations; other ladders, dialogue, shrines, scripted events, all mission transitions and interactable variants have not all been verified. Weapon-switch teaching support does not implement actual Boss weapon switching; native shooting is not implemented.
- Living Weapon retains Hino-Enma's body and moves without William's full startup animation or weapon appearance. Guardian summoning does not reproduce William's additional ki cost. Other guardians, controllers and full combat/transition coverage remain unverified.
- The included [CT](ct/Nioh_HinoEnma_1.24.8_Beta3.CT) uses the same scoped hooks; enabling it directly inside Cheat Engine has not been tested. Use either the CT or EXE for a game session. Mixing different versions in one process is not supported.
- The final public Beta 3 EXE’s first enable in a fresh game process remains pending. Offline checks and enabled-session recognition do not establish cold first-enable.
- This Beta is unsigned with Authenticode. Build provenance and file checksums describe origin and integrity; they are separate from Windows code signing.

## Validation and development

See [Beta 3 release record](docs/releases/1.0.0-beta.3.md), [build instructions](docs/BUILD.md), [development/release standard](DEVELOPMENT_RELEASE_STANDARD.md) and [credits/components](NOTICE.md). [Beta 1's release record](docs/releases/1.0.0-beta.1.md) remains historical.

The local 0.43 baseline’s **499 Python research checks are frozen**; local 0.44 passed **8 new hot-spring checks**, not 507 checks rerun. Private game-code inputs/raw reports are excluded and are not portable CI. New public Beta 3 Debug and optimized x64 Release each passed **19 C# checks and 540 payload/patch comparisons** (45 hooks across 12 layouts), with generated source exact and no game access. Pure-source/CT checks passed, including 275 unique labels and three rejection cases; the offscreen UI was reviewed without clipping. Final source commit, shipped hashes and actual publisher are recorded in provenance. Beta 1 and Beta 2 historical releases remain unchanged.

Report an issue with the game build, mission, interaction object, expected result and actual response. Do not attach saves or process dumps unless you intentionally want to share them.
